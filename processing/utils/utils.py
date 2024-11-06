import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
import re
from pathlib import Path
from processing.logger import logger
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_CLOUD = os.getenv("OVERWRITE_CLOUD") == "True"

SUCCESS_CODE = os.getenv("SUCCESS_CODE")
ERROR_CODE = os.getenv("ERROR_CODE")
EXIST_CODE = os.getenv("EXIST_CODE")
IS_DIR_CODE = os.getenv("IS_DIR_CODE")


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
        json.dump(data, write_file, indent=2)
    logger.info(f"Saved data to {file_path}")


def sanitize_product_name(product_name):
    sanitized_name = re.sub(r"[\n\t\/\|]+", " ", product_name).strip()
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


def upload_to_gcs(local_file, bucket, overwrite=False):
    """Uploads a single file to GCP"""
    # Create a blob (file) in the GCS bucket
    try:
        # Create a blob (file) in the GCS bucket
        gcs_destination = str(Path(local_file).as_posix())
        if os.path.isdir(gcs_destination):
            logger.info(f"{gcs_destination} is a directory, skipping upload.")
            return IS_DIR_CODE
        
        blob = bucket.blob(gcs_destination)
        if blob.exists() and not overwrite:
            logger.info(f"{gcs_destination} already exists in GCS, skipping upload.")
            return EXIST_CODE

        # Upload the local file to GCS
        blob.upload_from_filename(gcs_destination)
        logger.info(f"Uploaded {local_file} to gs://{bucket.name}/{gcs_destination}")
        return SUCCESS_CODE

    except Exception as e:
        logger.error(f"Failed to upload {gcs_destination} to GCS: {e}")  # Log the error
        return ERROR_CODE


def download_from_gcs(blob_name, bucket, overwrite=False):
    """Downloads a single file from GCS to the specified local directory."""
    try:
        # Create a blob object
        blob = bucket.blob(blob_name)

        # Create the local path
        local_file_path = blob_name

        if os.path.exists(local_file_path) and not overwrite:
            logger.info(f"{local_file_path} exists in local")
            return EXIST_CODE

        # Create the directory if it doesn't exist
        local_file_dir = os.path.dirname(local_file_path)
        create_dir_if_not_exists(local_file_dir)

        # Download the blob to a local file
        blob.download_to_filename(local_file_path)
        logger.info(f"Downloaded gs://{BUCKET_NAME}/{blob_name} to {local_file_path}")
        return SUCCESS_CODE

    except Exception as e:
        logger.error(f"Failed to download {blob_name} from GCS: {e}")  # Log the error
        return ERROR_CODE
