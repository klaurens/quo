import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from datetime import datetime
import glob
from processing.logger import logger
from google.cloud import vision
from datetime import timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
LOCATION = os.getenv("LOCATION")
DATETIME_FORMAT = os.getenv("DATETIME_FORMAT")

latest_index_file_path = "indices/latest.index"


def get_latest_index_time():
    """Retrieve the latest index time for product sets."""
    try:
        with open(latest_index_file_path, "r") as f:
            latest_index_time = datetime.strptime(f.read(), DATETIME_FORMAT).tzinfo(
                timezone.utc
            )
            return latest_index_time
    except:
        return datetime.min.replace(tzinfo=timezone.utc)


def parse_index_date(file_path):
    """Extract and parse the date from an index file path."""
    try:
        index_date_str = file_path.split("_")[2]
        index_date = datetime.strptime(index_date_str, DATETIME_FORMAT)
        tz_date = index_date.replace(tzinfo=timezone.utc)  # Make it offset-aware
        logger.info(f"Index {file_path} dated at {tz_date}")
        return tz_date
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing date from file {file_path}: {e}")
        return None


def find_new_indices(latest_index_time):
    """Find indices with dates newer than the latest indexed time."""
    index_files = glob.glob("indices/*.csv")
    if not latest_index_time:
        return index_files
    new_indices = sorted([
        index_file
        for index_file in index_files
        if (index_date := parse_index_date(index_file))
        and index_date > latest_index_time
    ])
    logger.info(f"Valid indices to index found: {new_indices}")
    return new_indices


def import_product_set(client, index_path):
    """Import a product set from a given index file."""
    try:
        logger.info(f"Indexing {index_path}")
        location_path = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        csv_file_uri = f"gs://{BUCKET_NAME}/{index_path}"

        gcs_source = vision.ImportProductSetsGcsSource(csv_file_uri=csv_file_uri)
        input_config = vision.ImportProductSetsInputConfig(gcs_source=gcs_source)

        response = client.import_product_sets(
            parent=location_path, input_config=input_config
        )
        result = response.result()  # Wait for the operation to complete

        # Log statuses
        for i, status in enumerate(result.statuses):
            if status.code == 0:
                logger.info(f"Line {i} processed successfully.")
            else:
                logger.error(f"Error on line {i}: {status.message}")

        logger.info(f"Indexing completed for {index_path}.")
    except Exception as e:
        logger.error(f"Failed to import product set {index_path}: {e}")


def update_latest_index_time(index_file):
    index_date_str = index_file.split("_")[2]
    latest_index_time = datetime.strptime(index_date_str, DATETIME_FORMAT)

    with open(latest_index_file_path, "w+") as f:
        f.write(str(latest_index_time))
    logger.info(f"Updated index tracker to latest as {latest_index_time}")


def main():
    client = vision.ProductSearchClient()
    latest_index_time = get_latest_index_time()

    logger.info(f"Finding indices older than {latest_index_time}")
    new_indices = find_new_indices(latest_index_time)
    if not new_indices:
        logger.info("No new indices to process.")
        return
    else:
        logger.info(f"New indices found: {new_indices}")

    logger.info(f"Found {len(new_indices)} new indices to process.")
    for index_file in new_indices:
        logger.info(f"Processing {index_file}")
        import_product_set(client, index_file)
        update_latest_index_time(index_file)


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting indexing process.")
    main()
    elapsed_time = timedelta(seconds=time.time() - start_time)
    logger.info(f"Indexing process completed in {elapsed_time}.")
