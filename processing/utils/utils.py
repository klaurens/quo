import json
import os
import re
from ..logger import logger


# MAGIC_NUMBERS = {
#     b"\xFF\xD8": "jpg",
#     b"\x89\x50\x4E\x47": "png",
# }


def create_dir_if_not_exists(directory: str):
    """Create a directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)

def save_json(data: dict, file_path: str):
    """Saves data to a JSON file."""
    create_dir_if_not_exists(os.path.dirname(file_path))
    with open(file_path, "w") as write_file:
        json.dump(data, write_file)
    logger.info(f"Saved data to {file_path}")

def sanitize_product_name(product_name):
    sanitized_name = re.sub(r"[\n\t\/]+", " ", product_name).strip()
    return sanitized_name


# def add_missing_extensions():
#     files = glob.glob(f"{DETAILS_DIR}/**/**/*")
#     files = [file for file in files if "." not in file]
#     for file in files:
#         if not os.path.isfile(file):
#             continue
#         with open(file, "rb") as f:
#             file_header = f.read(8)  # Read the first 8 bytes, enough for most formats

#         # Check the file header against known magic numbers
#         for magic, fmt in MAGIC_NUMBERS.items():
#             if file_header.startswith(magic):
#                 os.rename(file, f"{file}.{fmt}")
#                 logger.info(f"Renaming {file} to {file}.{fmt}")
#                 break


## define GCP upload function here