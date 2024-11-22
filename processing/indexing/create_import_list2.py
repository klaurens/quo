import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(ROOT_DIR)
import glob
import json
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Lock
from functools import partial
from processing.logger import logger
from dotenv import load_dotenv

load_dotenv()

# Configuration and Constants
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "indices")

# PRODUCT_SET_NAME = os.getenv("PRODUCT_SET_A_NAME", "default_set")
PRODUCT_SET_NAME = "test-set"
BUCKET_DIR = os.getenv("BUCKET_NAME")
BATCH_SIZE = int(os.getenv("BATCH_SIZE"))
DATETIME_FORMAT = os.getenv("DATETIME_FORMAT")
EXTRACT_FILENAME = os.getenv("EXTRACT_FILENAME")

try:
    with open(
        os.path.join(ROOT_DIR, "processing/indexing/taxonomy.json"), "r"
    ) as mapping_file:
        CATEGORY_MAPPING = json.load(mapping_file)
    logger.info("Category mapping loaded successfully.")
except FileNotFoundError:
    logger.error("Category mapping file not found.")


# Utility Functions
def get_product_images(product_path):
    """Retrieve image file paths from the product directory."""
    return glob.glob(os.path.join(product_path, "images", "*.[jp][pn]g"))


def get_product_details(product_path):
    """Load product details from the product_info.json file."""
    try:
        detail_path = glob.glob(os.path.join(product_path, EXTRACT_FILENAME))
        if detail_path:
            with open(detail_path[0], "r") as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.info(f"Error loading product details: {e}")
    return {}


def sanitize_image_path(image_path):
    """Convert local image path to a GCS-friendly format."""
    # image_path.replace("/home/root/quo/", "")
    start_dir = "details"
    normalized_path = os.path.normpath(image_path)
    relative_path = normalized_path.split(start_dir, 1)[-1]
    clean_path = os.path.join(start_dir, relative_path.lstrip(os.sep))
    return clean_path


def get_category_code(product_info):
    mapped_code = CATEGORY_MAPPING.get(product_info["category"], None)
    code = mapped_code.split(": ")[0]

    return code


def get_bounding_box(image, category_code):
    head, tail = os.path.split(image)

    processed_path = os.path.join(head, "processed", f"{tail}.npy")
    if os.path.exists(processed_path) and category_code:
        detection_data = np.load(processed_path, allow_pickle=True).item()
        bounding_boxes = [
            (x1, y1, x2, y2)
            for i, class_id in enumerate(detection_data["classes"])
            if class_id == int(category_code)
            for y1, x1, y2, x2 in [detection_data["boxes"][i].astype(int)]
        ]

        if bounding_boxes:
            largest_box = max(
                bounding_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])
            )

            logger.info(f"Selected largest bounding box for {image}: {largest_box}")
            box_string = ",".join(map(str, largest_box))
            return f'"{box_string}"'
    logger.warning(f"No bounding box found for {image}")
    return ""  # Don't return None


def compile_product_data(product_path, lines, lines_lock):
    """Compile data for a single product and append to the shared lines list."""
    images = get_product_images(product_path)
    product_info = get_product_details(product_path)

    if not images or not product_info:
        logger.info(f"Missing images or details file for {product_path}")
        return

    product_display_name = os.path.basename(product_path)
    product_id = product_info.get("product_id", "Unknown")
    product_category = "apparel-v2"
    product_labels = (
        f'category={product_info.get("category", "no-cat")},'
        f'brand={product_info.get("shop_name", "Unknown")},'
        f'price={product_info.get("price", 0)}'
    )

    for image in images:
        image_loc = sanitize_image_path(image)
        category_code = get_category_code(product_info)
        bbox = get_bounding_box(image, category_code)
        csv_line = (
            f'"gs://quo-trial/{image_loc}",,"{PRODUCT_SET_NAME}","{product_id}",'
            f'"{product_category}","{product_display_name}","{product_labels}",'
            f'{bbox if bbox else ""}\n'
        )
        with lines_lock:
            lines.append(csv_line)
            logger.info(f"Appended {product_display_name}")


def write_batch_to_file(lines, batch_index, write_date):
    """Write a batch of lines to a file."""
    filename = os.path.join(
        OUTPUT_DIR, f"index_{PRODUCT_SET_NAME}_{write_date}_{batch_index}.csv"
    )
    try:
        with open(filename, "w") as f:
            f.writelines(lines)
        logger.info(
            f"Batch {batch_index} written to {filename} with {len(lines)} lines."
        )
    except IOError as e:
        logger.info(f"Error writing to file {filename}: {e}")


# Main Logic
def main():
    product_paths = glob.glob(os.path.join(ROOT_DIR, "details", "**", "**"))
    lines = []
    lines_lock = Lock()

    # Compile product data concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(
            partial(compile_product_data, lines=lines, lines_lock=lines_lock),
            product_paths,
        )

    # Write lines to files in batches
    write_date = datetime.now(timezone.utc).strftime(DATETIME_FORMAT)
    for i in range(0, len(lines), BATCH_SIZE):
        batch = lines[i : i + BATCH_SIZE]
        write_batch_to_file(
            batch, batch_index=(i // BATCH_SIZE) + 1, write_date=write_date
        )


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting import list creation")
    main()

    end_time = time.time()
    logger.info("Finished import list creation")
    logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
