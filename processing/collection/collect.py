import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tokped_scraper import get_brand_listing, get_item_details, get_image
from datetime import datetime, timedelta
import glob
import json
from jsonpath_ng import parse
from processing.logger import logger
from concurrent.futures import ThreadPoolExecutor
from typing import List
from functools import partial
import time
from processing.utils.utils import save_json, sanitize_product_name, create_dir_if_not_exists
from dotenv import load_dotenv

load_dotenv()

# Configuration constants
IMAGE_MIN_BYTES = 5000
WRITE_DATE = datetime.today().date()
SOURCE_FILE = "brands.txt"
DETAILS_DIR = "details"
LISTING_DIR = "listing"
OVERWRITE = os.getenv("OVERWRITE") == "True"


def read_brands(source_file: str) -> List[str]:
    """Reads brand names from a file."""
    with open(os.path.join(os.path.dirname(__file__), source_file), "r") as read_file:
        return [brand.strip() for brand in read_file.readlines()]


def scrape_listing(source_file: str = SOURCE_FILE):
    """Scrapes all listings from brands."""
    brands = read_brands(source_file)

    for brand in brands:
        try:
            logger.info(f"Fetching brand list for {brand}")
            brand_listing = get_brand_listing(brand_uri=brand)

            file_path = f"{LISTING_DIR}/{brand}/listing_{WRITE_DATE}.json"
            save_json(brand_listing, file_path)
        except Exception as e:
            logger.error(f"Error scraping brand {brand}: {str(e)}")


def scrape_products():
    """Scrapes details for all products in the unified file."""
    scraped_products = []
    json_files = glob.glob(f"{LISTING_DIR}/**/listing_*.json")
    parser = parse("$..GetShopProduct.data")

    for json_file in json_files:
        try:
            with open(json_file, "r") as jf:
                data = json.load(jf)
            brand = json_file.split("/")[1]

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

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(scrape_product_details, products)


def scrape_product_details(product: dict):
    """Scrapes product details for a single product."""
    try:
        product_name = product["name"]
        product_brand = product["brand"]
        product_url = product["product_url"]

        sanitized_product_name = sanitize_product_name(product_name)

        file_path = (
            f"{DETAILS_DIR}/{product_brand}/{sanitized_product_name}/details_{WRITE_DATE}.json"
        )
        file_exists = os.path.isfile(file_path)
        if not file_exists or OVERWRITE:
            product_details = get_item_details(product_url)
            save_json(product_details, file_path)
        else:
            logger.info(f"File exists. Skipping {file_path}")
    except Exception as e:
        logger.error(f"Error scraping product {product['name']}: {str(e)}")


def scrape_images():
    """Scrapes images from product details."""
    json_files = glob.glob(f"{DETAILS_DIR}/**/**/details_*.json")
    parser = parse("$..urlMaxRes")

    for json_file in json_files:
        try:
            with open(json_file, "r") as jf:
                data = json.load(jf)
            links = [link.value for link in parser.find(data)]

            dir_parts = json_file.split("/")
            with ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(partial(fetch_image, dir_parts=dir_parts), links)

        except Exception as e:
            logger.error(f"Error processing images for {json_file}: {str(e)}")


def fetch_image(link, dir_parts):
    """Fetch and write image file"""
    image_name = link.split("/")[-1]
    product_brand = dir_parts[1]
    product_name = dir_parts[2]

    if image_name[-4:] not in (".png", ".jpg"):
        image_name += ".jpg"

    file_dir = f"{DETAILS_DIR}/{product_brand}/{product_name}/images"
    file_path = f"{file_dir}/{image_name}"
    file_exists = os.path.isfile(file_path)
    if not file_exists or OVERWRITE:
        image_file = get_image(link, brand_uri=product_brand)
        if len(image_file) >= IMAGE_MIN_BYTES:
            create_dir_if_not_exists(file_dir)
            with open(file_path, "wb+") as f:
                f.write(image_file)
            logger.info(f"Image saved at {file_path}")
        else:
            logger.info(f"Skipped saving image: {link} (too small/broken image)")


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
