import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from google.cloud import storage
import glob
from processing.logger import logger
from processing.utils.utils import upload_to_gcs
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_CLOUD = os.getenv("OVERWRITE_CLOUD") == "True"
SUCCESS_CODE = os.getenv('SUCCESS_CODE')


def sync_up(local_file, bucket, upload_lock, upload_count):
    # Create a blob (file) in the GCS bucket
    status = upload_to_gcs(local_file, bucket, OVERWRITE_CLOUD)
    # Safely increment the upload count
    if status == SUCCESS_CODE:
        with upload_lock:
            upload_count[0] += 1  # Use a list to allow mutable reference


def main():
    # Initialize the GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    # Get all image files in the specified directories
    listing_files = glob.glob("alisting/**/*", recursive=True)
    details_files = glob.glob("adetails/**/*", recursive=True)
    indices_files = glob.glob("indices/*")

    upload_lock = threading.Lock()
    upload_count = [0]  # Use a list to allow mutable reference

    # Combine the files from both directories
    files = listing_files + details_files + indices_files
    files = [file for file in files if os.path.isfile(file)]

    # Sync files to GCS
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(
            partial(
                sync_up,
                bucket=bucket,
                upload_count=upload_count,
                upload_lock=upload_lock,
            ),
            files,
        )

    logger.info(f"Total uploaded files: {upload_count[0]}")


if __name__ == "__main__":
    start_time = time.time()

    logger.info("Starting GCS upload sync process")

    main()

    logger.info(
        f"Completed GCS upload sync process. Execution time: {timedelta(seconds=time.time() - start_time)}"
    )
