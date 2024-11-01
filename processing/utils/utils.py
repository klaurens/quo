import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
import re
from processing.logger import logger
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_CLOUD = os.getenv("OVERWRITE_CLOUD") == "True"

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


def write_gcs(file_path, content):
    """Uploads content to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_path)

    # Write content to the blob
    blob.upload_from_string(content)
    logger.info(f"Written to GCS: {file_path}")


def upload_to_gcs(local_file, bucket, upload_count, upload_lock):
    """Uploads a single file to GCP"""
    # Create a blob (file) in the GCS bucket
    blob = bucket.blob(local_file)
    if blob.exists():
        logger.info(f"{local_file} already exists in GCS, skipping upload.")
        return

    # Upload the local file to GCS
    blob.upload_from_filename(local_file)
    logger.info(f"Uploaded {local_file} to gs://{bucket.name}/{local_file}")

    # Safely increment the upload count
    with upload_lock:
        upload_count[0] += 1  # Use a list to allow mutable reference
