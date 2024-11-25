import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from google.cloud import storage
import glob
from processing.logger import logger
from processing.utils.utils import upload_to_gcs
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_CLOUD = os.getenv("OVERWRITE_CLOUD") == "True"
SUCCESS_CODE = os.getenv('SUCCESS_CODE')
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))



def sync_up(local_file, bucket, upload_lock, upload_count):
    # Create a blob (file) in the GCS bucket
    status = upload_to_gcs(local_file, bucket, OVERWRITE_CLOUD)
    # Safely increment the upload count
    if status == SUCCESS_CODE:
        with upload_lock:
            upload_count[0] += 1  # Use a list to allow mutable reference


def main(upload_list='all'):
    # Initialize the GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    # Define file paths
    file_groups = {
        'listing': glob.glob(os.path.join(ROOT_DIR, "listing/**/*")),
        'details': glob.glob(os.path.join(ROOT_DIR, "details/**/*"), recursive=True),
        'indices': glob.glob(os.path.join(ROOT_DIR, "indices/*")),
    }

    # Select files to upload
    if upload_list == 'all':
        files = sum(file_groups.values(), [])  # Combine all files
    elif isinstance(upload_list, list):
        files = sum((file_groups.get(group, []) for group in upload_list), [])
    else:
        logger.error("Invalid upload_list argument")
        return

    # Filter only valid files
    files = [file for file in files if os.path.isfile(file)]
    if not files:
        logger.info("No files to upload.")
        return

    # Upload files to GCS
    upload_count = 0
    upload_lock = Lock()

    def sync_with_lock(file_path):
        nonlocal upload_count
        try:
            sync_up(file_path, bucket, upload_lock, upload_count)
            with upload_lock:
                upload_count += 1
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(sync_with_lock, files)

    logger.info(f"Total uploaded files: {upload_count}")


if __name__ == "__main__":
    start_time = time.time()

    logger.info("Starting GCS upload sync process")

    main()

    logger.info(
        f"Completed GCS upload sync process. Execution time: {timedelta(seconds=time.time() - start_time)}"
    )
