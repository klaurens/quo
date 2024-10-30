import glob
import os
import json
import logging
from jsonpath_ng.ext import parse
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        # logging.StreamHandler(),  # This sends log output to the console
        # You can also add FileHandler() if you want to log to a file
        logging.FileHandler(f"scraper-{datetime.today().date()}.log")
    ],
)

# Define JSONPath parsers
BASIC_PARSER = parse("$..basicInfo")
PARENT_ID_PARSER = parse("$..parentID")
DESC_PARSER = parse("$..content[?(@.title=='Deskripsi')].subtitle")
CHILD_PARSER = parse("$..pdpGetLayout..children[*]")
OUT_FILE_NAME = "details.json"
CATEGORY_BREADCRUMB_URI = "https://www.tokopedia.com/p/"


def extract_details(json_file):
    try:
        # Determine parent directory path
        parent_dir = os.path.dirname(json_file)
        output_file = os.path.join(parent_dir, OUT_FILE_NAME)

        logging.info(f"Processing file: {json_file}")

        # Open and parse JSON file
        with open(json_file, "r") as f:
            j = json.load(f)

        # Extract relevant information using JSONPath parsers
        basic_info = BASIC_PARSER.find(j)
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

        parsed_parent_id = PARENT_ID_PARSER.find(j)
        parsed_desc = DESC_PARSER.find(j)
        parsed_children = CHILD_PARSER.find(j)

        # Get values if they exist
        parent_id = parsed_parent_id[0].value if parsed_parent_id else None
        description = parsed_desc[0].value if parsed_desc else None

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
            "parent_id": parent_id,
            "description": description,
            "category": category,
            "category_tree": category_tree,
            "children": flattened_children,
        }

        # Log extracted information
        logging.info(f"Extracted details for {parent_dir}")

        # Write data to details.json in the same directory as the JSON file
        with open(output_file, "w") as f:
            json.dump(out_json, f, indent=4)

        logging.info(f"Successfully wrote to {output_file}")

    except Exception as e:
        logging.error(f"Failed to process {json_file}: {e}")


def extract_all():
    # Get list of JSON files
    files = glob.glob("../collection/details/**/**/*-*-*.json")

    # Track execution time
    start = time.time()

    logging.info("Starting JSON extraction process")

    # Execute in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(extract_details, files)

    logging.info(
        f"Completed JSON extraction process. Execution time: {time.time() - start}"
    )

if __name__ == "__main__":
    extract_all()