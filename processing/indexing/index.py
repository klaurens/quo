import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from processing.logger import logger
from google.cloud import vision
from google.cloud import storage
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
PRODUCT_SET_A_NAME = os.getenv("PRODUCT_SET_A_NAME")
PRODUCT_SET_B_NAME = os.getenv("PRODUCT_SET_B_NAME")
LOCATION = os.getenv("LOCATION")


def get_latest_index_files():
    """Find the latest index_import_(date).csv file based on date in filename."""

    client = storage.Client(project=PROJECT_ID)
    blobs = client.list_blobs(BUCKET_NAME, prefix="indices")
    files = [file.name for file in blobs]
    files.sort(reverse=True)
    if files:
        latest_file = files[0]
        logger.info(f"Latest file found: {latest_file}")
        latest_file_date = latest_file.split('_')[2]
        latest_files = sorted([file for file in files if latest_file_date in file])
        return latest_files
    else:
        logger.warning("No index_import files found.")
        return None


def delete_product_set(client, product_set_id):
    """Delete a specified product set."""
    # client.delete_product_set(name=product_set_path)
    if product_set_id == None:
        logger.warning('No product set id given, skipping delete')
        return

    product_set_path = client.product_set_path(
        project=PROJECT_ID, location=LOCATION, product_set=product_set_id
    )

    # Delete the product set.
    client.delete_product_set(name=product_set_path)
    logger.info(f"Product set {product_set_id} deleted.")


def import_product_sets(client, gcs_uris):
    """Import images of different products in the product set."""
    location_path = f"projects/{PROJECT_ID}/locations/{LOCATION}"

    for gcs_uri in gcs_uris:
        logger.info(f"Indexing {gcs_uri} ({gcs_uris.index(gcs_uri) + 1}/{len(gcs_uris)})")
        gcs_source = vision.ImportProductSetsGcsSource(
            csv_file_uri=f"gs://{BUCKET_NAME}/{gcs_uri}"
        )
        input_config = vision.ImportProductSetsInputConfig(gcs_source=gcs_source)
        response = client.import_product_sets(
            parent=location_path, input_config=input_config
        )
        logger.info(f"Processing operation name: {response.operation.name}")
        result = response.result()  # Wait for the operation to complete
        logger.info("Processing done.")
        for i, status in enumerate(result.statuses):
            logger.info(f"Status of processing line {i} of the csv: {status}")


def get_older_product_set(client):
    """Retrieve and identify the older product set between set_A and set_B."""
    location_path = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    product_sets = client.list_product_sets(parent=location_path)

    set_a = set_b = None

    for product_set in product_sets:
        if product_set.name.endswith(f"/{PRODUCT_SET_A_NAME}"):
            set_a = product_set
        elif product_set.name.endswith(f"/{PRODUCT_SET_B_NAME}"):
            set_b = product_set

    if (set_a == None and set_b == None) or set_a:
        return set_a, set_b
    elif set_b:
        return set_b, set_a

    # Determine older product set by timestamp
    if set_a.index_time < set_b.index_time:
        return (
            set_a.name.split("/")[-1],
            PRODUCT_SET_B_NAME,
        )  # return older path and opposite ID to re-use
    else:
        return set_b.name.split("/")[-1], PRODUCT_SET_A_NAME


def main():
    client = vision.ProductSearchClient()
    latest_file = get_latest_index_files()

    if not latest_file:
        raise

    # Find the older product set and determine the new target set
    old_set_path, new_set_id = get_older_product_set(client)

    # Delete the older product set
    delete_product_set(client, old_set_path)

    # Import the new product set from the latest CSV file
    import_product_sets(client, latest_file)


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting indexing processing")
    main()

    end_time = time.time()
    logger.info("Finished main processing Run")
    logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
