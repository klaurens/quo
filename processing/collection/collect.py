import os
import sys
from datetime import datetime, timedelta
import glob
import json
from jsonpath_ng.ext import parse
from concurrent.futures import ThreadPoolExecutor
from typing import List
from functools import partial
import time

# Set ROOT_DIR to the root directory of the project, assuming this script is inside `quo/processing/collection`
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add the root directory to the sys.path to allow imports from quo
sys.path.append(ROOT_DIR)

from processing.logger import logger
from processing.utils.utils import (
    save_json,
    sanitize_product_name,
    create_dir_if_not_exists,
)
from dotenv import load_dotenv
from tokped_scraper import get_brand_listing, get_item_details, get_image

load_dotenv()

# Configuration constants
IMAGE_MIN_BYTES = 5000
WRITE_DATE = datetime.today().date()
SOURCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brands.txt")
DETAILS_DIR = os.path.join(ROOT_DIR, "details")
LISTING_DIR = os.path.join(ROOT_DIR, "listing")
SCRAPE_OVERWRITE = os.getenv("SCRAPE_OVERWRITE") == "True"
DETAILS_FILENAME = os.getenv("DETAILS_FILENAME")

BASIC_PARSER = parse("$..basicInfo")
PARENT_ID_PARSER = parse("$..parentID")
DESC_PARSER = parse("$..content[?(@.title=='Deskripsi')].subtitle")
CHILD_PARSER = parse("$..pdpGetLayout..children[*]")
PRICE_PARSER = parse("$..price.value")
EXTRACT_FILENAME = os.getenv("EXTRACT_FILENAME")
CATEGORY_BREADCRUMB_URI = "https://www.tokopedia.com/p/"


def read_brands(source_file: str) -> List[str]:
    """Reads brand names from a file."""
    with open(source_file, "r") as read_file:
        return [brand.strip() for brand in read_file.readlines()]


def scrape_listing(source_file: str = SOURCE_FILE):
    """Scrapes all listings from brands."""
    brands = read_brands(source_file)

    for brand in brands:
        try:
            logger.info(f"Fetching brand list for {brand}")
            brand_listing = get_brand_listing(brand_uri=brand)

            file_path = os.path.join(LISTING_DIR, brand, f"listing_{WRITE_DATE}.json")
            save_json(brand_listing, file_path)
        except Exception as e:
            logger.error(f"Error scraping brand {brand}: {str(e)}")


def scrape_products():
    """Scrapes details for all products in the unified file."""
    scraped_products = []
    json_files = glob.glob(os.path.join(LISTING_DIR, "**", "listing_*.json"))
    parser = parse("$..GetShopProduct.data")

    for json_file in json_files:
        try:
            with open(json_file, "r") as jf:
                data = json.load(jf)
            brand = os.path.basename(os.path.dirname(json_file))

            # Insert brand into the JSON object
            brand_parser = parse("$..GetShopProduct.data[*].brand")
            brand_parser.update_or_create(data, brand)

            values = parser.find(data)
            scraped_products.extend([v.value for v in values])

        except Exception as e:
            logger.error(f"Error processing file {json_file}: {str(e)}")

    products = [
        product for product_list in scraped_products for product in product_list
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(scrape_product_details, products)


def scrape_product_details(product: dict):
    """Scrapes product details for a single product."""
    try:
        product_name = product["name"]
        product_brand = product["brand"]
        product_url = product["product_url"]

        sanitized_product_name = sanitize_product_name(product_name)

        # Save product detail
        product_dir = os.path.join(DETAILS_DIR, product_brand, sanitized_product_name)
        details_path = os.path.join(product_dir, DETAILS_FILENAME)
        details_exists = os.path.isfile(details_path)
        if not details_exists or SCRAPE_OVERWRITE:
            product_details = get_item_details(product_url)
            save_json(product_details, details_path)
        else:
            logger.info(f"File exists, skipping details save: {product_dir}")

        # Extract and simplify details to product_info
        extract_path = os.path.join(product_dir, EXTRACT_FILENAME)
        extract_exists = os.path.isfile(extract_path)
        if not extract_exists or SCRAPE_OVERWRITE:
            logger.info(f"Extracting file: {sanitized_product_name}")
            product_info = extract_details(product_details)
            save_json(product_info, extract_path)
        else:
            logger.info(f"File exists, skipping extraction: {product_dir}")
    except Exception as e:
        logger.error(f"Error scraping product {product['name']}: {str(e)}")


def scrape_images():
    """Scrapes images from product details."""
    logger.info("Globbing Image URIs to Collect.")
    json_files = glob.glob(os.path.join(DETAILS_DIR, "**", "**", DETAILS_FILENAME))
    parser = parse("$..urlMaxRes")

    for json_file in json_files:
        try:
            with open(json_file, "r") as jf:
                data = json.load(jf)
            links = [link.value for link in parser.find(data)]

            dir_parts = json_file.split("/")
            with ThreadPoolExecutor(max_workers=8) as executor:
                executor.map(partial(fetch_image, dir_parts=dir_parts), links)

        except Exception as e:
            logger.error(f"Error processing images for {json_file}: {str(e)}")


def fetch_image(link, dir_parts):
    """Fetch and write image file"""
    image_name = link.split("/")[-1]
    product_brand = dir_parts[-3]  # Adjusted to use the correct index for brand
    product_name = dir_parts[-2]  # Adjusted to use the correct index for product name

    if image_name[-4:] not in (".png", ".jpg"):
        image_name += ".jpg"

    file_dir = os.path.join(DETAILS_DIR, product_brand, product_name, "images")
    file_path = os.path.join(file_dir, image_name)
    file_exists = os.path.isfile(file_path)
    if not file_exists or SCRAPE_OVERWRITE:
        image_file = get_image(link, brand_uri=product_brand)
        if len(image_file) >= IMAGE_MIN_BYTES:
            create_dir_if_not_exists(file_dir)
            with open(file_path, "wb+") as f:
                f.write(image_file)
            logger.info(f"Image saved at {file_path}")
        else:
            logger.info(f"Skipped saving image: {link} (too small/broken image)")
    else:
        logger.info(f"Image Exists: {link}, skipping download")


def extract_details(product_json):
    try:
        # Extract relevant information using JSONPath parsers
        basic_info = BASIC_PARSER.find(product_json)
        if basic_info:
            basic_info = basic_info[0].value
            product_id = basic_info.get("id")
            shop_id = basic_info.get("shopID")
            shop_name = basic_info.get("shopName")
            url = basic_info.get("url")
            category_breadcrumb = basic_info.get("category").get("breadcrumbURL")
            category_tree = category_breadcrumb.replace(
                CATEGORY_BREADCRUMB_URI, ""
            ).split("/")
            category = category_tree[-1]
        else:
            product_id = shop_id = shop_name = url = category = category_tree = None

        parsed_parent_id = PARENT_ID_PARSER.find(product_json)
        parsed_desc = DESC_PARSER.find(product_json)
        parsed_children = CHILD_PARSER.find(product_json)
        parsed_price = PRICE_PARSER.find(product_json)

        # Get values if they exist
        parent_id = parsed_parent_id[0].value if parsed_parent_id else None
        description = parsed_desc[0].value if parsed_desc else None
        price = parsed_price[0].value if parsed_price else None

        flattened_children = (
            [
                {
                    "productID": child.value["productID"],
                    "optionName": ", ".join(child.value["optionName"]),
                }
                for child in parsed_children
            ]
            if parsed_children
            else None
        )

        # Create dictionary to store extracted details
        out_json = {
            "product_id": product_id,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "url": url,
            "price": price,
            "parent_id": parent_id,
            "description": description,
            "category": category,
            "category_tree": category_tree,
            "children": flattened_children,
        }

        return out_json

    except Exception as e:
        logger.error(f"Failed to process {product_json}: {e}")


def main():
    try:
        start_time = time.time()
        logger.info("Start Scraping Run")

        scrape_listing()
        scrape_products()
        scrape_images()

        end_time = time.time()
        logger.info("Finished Scraping Run")
        logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")


if __name__ == "__main__":
    main()
