import json
import os
import re
from ..logger import logger
from google.cloud import storage


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


def upload_to_gcs(file_path, bucket):
    """Uploads a single file to GCP"""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    try:

        # Create a new blob (object) in the bucket
        blob = bucket.blob(file_path)

        if not blob.exists() or OVERWRITE_CLOUD:
            # Upload the file
            blob.upload_from_filename(file_path)
            logger.info(f"Uploaded {file_path} to gs://{BUCKET_NAME}/{file_path}")

    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {str(e)}")
