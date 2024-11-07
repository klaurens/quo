import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import glob
import json
import numpy as np
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from processing.logger import logger

CATEGORY_MAPPING = {}

# Initialize the category mapping once
try:
    with open("processing/indexing/taxonomy.json", "r") as mapping_file:
        CATEGORY_MAPPING = json.load(mapping_file)
    logger.info("Category mapping loaded successfully.")
except FileNotFoundError:
    logger.error("Category mapping file not found.")
except json.JSONDecodeError as e:
    logger.error(f"Error decoding category mapping: {e}")

def load_info_file(info_path):
    """Load product info from a JSON file."""
    try:
        with open(info_path, "r") as info_file:
            return json.load(info_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading info file {info_path}: {e}")
        return None

def get_image_pairs(product_path):
    """Find images and corresponding processed files if they exist."""
    images_dict = {}
    image_files = glob.glob(os.path.join(product_path, "images", "*.[jp][pn]g"))
    for image_path in image_files:
        processed_path = image_path.replace("/images/", "/images/processed/") + ".npy"
        if os.path.exists(processed_path):
            images_dict[image_path] = processed_path
        else:
            logger.warning(f"Processed file missing for image: {image_path}")
    return images_dict

def get_bounding_boxes(image_pairs, category_code):
    """Retrieve bounding boxes for a given category code."""
    boxes_dict = {}
    for image_path, detect_path in image_pairs.items():
        try:
            detection_data = np.load(detect_path, allow_pickle=True).item()
        except Exception as e:
            logger.error(f"Error loading detection file {detect_path}: {e}")
            continue
        
        bounding_boxes = [
            (x1, y1, x2, y2)
            for i, class_id in enumerate(detection_data["classes"])
            if class_id == int(category_code)
            for y1, x1, y2, x2 in [detection_data["boxes"][i].astype(int)]
        ]
        
        if bounding_boxes:
            largest_box = max(bounding_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            boxes_dict[image_path] = largest_box
            logger.debug(f"Selected largest bounding box for {image_path}: {largest_box}")
    return boxes_dict

def categorize_product(meta_dict):
    """Categorize a product and prepare import lines based on metadata."""
    product_display_name = meta_dict["product_name"].split("/")[1]
    info_path = meta_dict["info"]
    image_pairs = meta_dict["images_detect_pairs"]

    info = load_info_file(info_path)
    if not info:
        return []

    category = info.get("category", "Unknown")
    if category not in CATEGORY_MAPPING:
        logger.warning(f"Category '{category}' not in mapping for {product_display_name}")
        return []

    mapped_category = CATEGORY_MAPPING[category]
    category_code, _ = mapped_category.split(": ")
    bounding_boxes = get_bounding_boxes(image_pairs, category_code)

    product_id = info.get("product_id", "Unknown")
    product_category = "apparel-v2"
    product_labels = f'category={category},brand={info.get("shop_name", "Unknown")},price={info.get("price", 0)}'

    import_lines = [
        f'gs://quo-trial/{image},,set_A,{product_id},{product_category},{product_display_name},{product_labels},{",".join(map(str, box))}\n'
        for image, box in bounding_boxes.items()
    ]
    logger.info(f"Categorized product {product_display_name} with {len(import_lines)} entries.")
    return import_lines

def main():
    product_paths = glob.glob("details/**/**/")
    all_import_lines = []

    logger.info("Starting product categorization.")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(categorize_product, {
                "product_name": os.path.relpath(product_path, "details"),
                "info": os.path.join(product_path, "product_info.json"),
                "images_detect_pairs": get_image_pairs(product_path)
            })
            for product_path in product_paths
            if os.path.exists(os.path.join(product_path, "product_info.json"))
        ]

        for future in as_completed(futures):
            try:
                all_import_lines.extend(future.result())
            except Exception as e:
                logger.error(f"Error processing a product: {e}")

    try:
        with open(f"index_import_{date.today()}.csv", "w") as f:
            f.writelines(all_import_lines)
        logger.info("CSV import file created successfully.")
    except IOError as e:
        logger.error(f"Error writing import file: {e}")

if __name__ == "__main__":
    main()
