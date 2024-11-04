import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from google.cloud import storage
from processing.logger import logger
from processing.utils.utils import download_from_gcs
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_LOCAL = os.getenv("OVERWRITE_LOCAL") == "True"


def sync_down(blob_name, bucket, download_count, download_lock, overwrite=False):
    status = download_from_gcs(blob_name, bucket, OVERWRITE_LOCAL)

    if status == 0:
        with download_lock:
            download_count[0] += 1  # Use a list to allow mutable reference


def main():
    # Initialize the GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    # Get all image files in the specified directories
    blobs_details = client.list_blobs(BUCKET_NAME, prefix="details/")
    blobs_listing = client.list_blobs(BUCKET_NAME, prefix="listing/")

    download_lock = threading.Lock()
    download_count = [0]  # Use a list to allow mutable reference

    # Combine the files from both directories
    all_blobs = [blob.name for blob in blobs_details] + [
        blob.name for blob in blobs_listing
    ]
    blobs_count = len(all_blobs)

    # Sync files to GCS
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(
            partial(
                sync_down,
                bucket=bucket,
                download_count=download_count,
                download_lock=download_lock,
            ),
            all_blobs,
        )

    logger.info(f"Total downloaded files: {download_count[0]}")


if __name__ == "__main__":
    start = time.time()

    logger.info("Starting GCS download sync process")

    main()

    logger.info(
        f"Completed GCS download sync process. Execution time: {time.time() - start}"
    )
