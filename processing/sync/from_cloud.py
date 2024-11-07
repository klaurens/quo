import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from google.cloud import storage
from processing.logger import logger
from processing.utils.utils import download_from_gcs
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import timedelta
import time
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")
OVERWRITE_LOCAL = os.getenv("OVERWRITE_LOCAL") == "True"


def sync_down(blob_name, bucket, download_count, download_lock, overwrite=False):
    status = download_from_gcs(blob_name, bucket, overwrite)

    if status == 0:
        with download_lock:
            download_count[0] += 1  # Use a list to allow mutable reference

def thread(files, bucket, download_count, download_lock):
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Directly iterate over blobs in the bucket
            for blob in files:
                # Submit the download task for each blob directly
                executor.submit(
                    sync_down,
                    blob_name=blob.name,  # Use the blob's name directly
                    bucket=bucket,
                    download_count=download_count,
                    download_lock=download_lock,
                    overwrite=OVERWRITE_LOCAL
                )


def main():
    # Initialize the GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    # Initialize shared variables for threading
    download_lock = threading.Lock()
    download_count = [0]  # Use a list to allow mutable reference

    listings = client.list_blobs(BUCKET_NAME, prefix="listing/")
    thread(listings, bucket, download_count, download_lock)

    details = client.list_blobs(BUCKET_NAME, prefix="details/")
    thread(details, bucket, download_count, download_lock)

    indices = client.list_blobs(BUCKET_NAME, prefix="indices/")
    thread(indices, bucket, download_count, download_lock)

    logger.info(f"Total downloaded files: {download_count[0]}")

if __name__ == "__main__":
    start_time = time.time()

    logger.info("Starting GCS download sync process")

    main()

    logger.info(
        f"Completed GCS download sync process. Execution time: {timedelta(seconds=time.time() - start_time)}"
    )
