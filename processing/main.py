import os
import json
from collection import collect
from extraction import extract
from logger import logger
import time
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def run_collect():
    try:
        start_time = time.time()
        logger.info("Start Scraping Run")

        collect.scrape_listing()
        collect.unify_listings()
        collect.scrape_products()
        collect.scrape_images()
        collect.add_missing_extensions()
        collect.push_to_gcp()

        end_time = time.time()
        logger.info("Finished Scraping Run")
        logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")


def run_extract():
    try:
        start_time = time.time()
        logger.info("Start Extract Run")

        extract.extract_all()

        end_time = time.time()
        logger.info("Finished Extract Run")
        logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")


if __name__ == "__main__":
    # collect
    run_collect()

    # extraction
    run_extract()
