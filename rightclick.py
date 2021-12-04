#!/usr/bin/env python3
#
# rightclick.py
# Automatically acquire whole NFT collections from OpenSea.
#
# k0rnh0li0 2021

import os
import sys
import signal
import requests

# Constants
# Root OpenSea API URL
API_URL = "https://api.opensea.io"
# Number of assets per page
PAGE_SIZE = 50

# Configuration
# If True, do not print info about individual assets
QUIET = False
# Directory to save downloaded collections to
OUTPUT_DIR = "collections"

# Total value of all downloaded NFTs
usd_total = 0

def download_collection(collection):
    assets = None
    page = 0

    #\TODO create collection directory
    while True:
        if page * PAGE_SIZE > 10000:
            # API restriction - can only use offsets up to 10000
            break

        req_url = API_URL + "/assets"
        req_params = {
            "collection": collection,
            "offset": page * PAGE_SIZE,
            "limit": PAGE_SIZE,
            "order_direction": "asc"
        }

        # Get assets in collection
        resp = requests.get(req_url, params=req_params)
        if resp.status_code != 200:
            print(f"Error {resp.status_code} on page {page} of collection '{collection}'")
            break

        # Convert API response to JSON
        try:
            resp = resp.json()
        except Exception as e:
            print(e)
            break

        assets = resp["assets"]
        if assets == []:
            if page == 0:
                print(f"Collection '{collection}' does not exist")
            break

        # Verify that the output directory exists
        if not os.path.isdir(OUTPUT_DIR + "/" + collection):
            os.mkdir(OUTPUT_DIR + "/" + collection)

        # Download all assets on this page
        for asset in assets:
            download_asset(collection, asset)

        page += 1

def download_asset(collection, asset):
    global usd_total

    # Name of this asset
    asset_name = asset["name"]

    if asset_name is None:
        asset_name = asset["token_id"]

    # URL of asset content
    asset_url = ""

    if asset["animation_url"] is not None:
        asset_url = asset["animation_url"]
    elif asset["image_url"] is not None:
        asset_url = asset["image_url"]

    if asset_url == "":
        return

    # USD value of the asset
    # Will be zero if no one was dumb enough to buy it yet
    last_price = 0

    if asset["last_sale"] is not None:
        token_price_usd = float(asset["last_sale"]["payment_token"]["usd_price"])
        token_decimals = asset["last_sale"]["payment_token"]["decimals"]
        total_price = int(asset["last_sale"]["total_price"]) / 10**(token_decimals)
        last_price = int(total_price * token_price_usd)

    # Download asset content
    req = requests.get(asset_url, stream=True)

    # Output file extension
    asset_ext = ""
    ctype = req.headers["Content-Type"]
    if "image" in ctype or "video" or "audio" in ctype:
        asset_ext = ctype.split("/")[1]
    else:
        print(f"Unrecognized Content-Type: {ctype}")
        asset_ext = "bin"

    # Output file path
    output_file = f"{OUTPUT_DIR}/{collection}/{asset_name}.{asset_ext}"

    if os.path.exists(output_file):
        # File already exists - don't re-download it
        return

    with open(output_file, "wb") as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    if not QUIET:
        print(f"{asset_name} - ${last_price}")

    usd_total += last_price

def parse_flag(flag):
    flag = flag.split("=")
    prop = flag[0].lower()

    if prop == "quiet":
        global QUIET
        QUIET = True
    elif prop == "output-dir":
        global OUTPUT_DIR
        OUTPUT_DIR = flag[1]
    else:
        print(f"Unrecognized flag '{prop}'")
        exit()

def finish():
    print(f"\nYou acquired ${usd_total} worth of NFTs!\n")
    exit()

def sig_handler(num, frame):
    finish()

if __name__ == "__main__":
    print("nft-rightclicker")
    print("All your NFTs are mine now!")
    print("k0rnh0li0 2021")
    print("https://twitter.com/gr8_k0rnh0li0\n")

    if len(sys.argv) < 2:
        print("At least one NFT collection must be specified.")
        exit()

    # First handle flags
    for v in sys.argv[1:]:
        if v[0:2] == "--":
            parse_flag(v[2:])

    # Create root NFT collections directory if necessary
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    # Set handler for CTRL+C
    signal.signal(signal.SIGINT, sig_handler)

    # Download all specified NFT collections
    for v in sys.argv[1:]:
        if v[0:2] == "--":
            continue
        download_collection(v)

    finish()
