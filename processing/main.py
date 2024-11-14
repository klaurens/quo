import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "collection")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "extraction")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "detection")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "sync")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "indexing")))

import time
from collection import collect
from extraction import extract
from detection import detect
from sync import to_cloud, from_cloud
from indexing import create_import_list, index
from logger import logger
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

if os.environ.get("GAE_ENV", "") == "standard":
    # Running on GCP
    ENVIRONMENT = "gcp"
else:
    # Running locally
    ENVIRONMENT = "local"

SYNC_LOCAL = os.getenv("SYNC_LOCAL") == "True"
SYNC_GCP = os.getenv("SYNC_GCP") == "True"


if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting main processing")

    if ENVIRONMENT == "local" and SYNC_LOCAL:
        ## Download from GCP
        from_cloud.main()

    ## collect
    collect.main()

    ## detection
    ## Detect bounding boxes with fpedia model
    detect.main()

    ## extraction
    extract.main()

    ## index
    ## 1. Combine extracted data from extraction with bounding boxes from detection into reference_images.csv file
    ## 2. Create google vision index
    create_import_list.main()

    ## Sync
    ## upload to gcp if necessary here
    if ENVIRONMENT == "local" and SYNC_GCP:
        ## Upload to GCP
        to_cloud.main()

    index.main()

    end_time = time.time()
    logger.info("Finished main processing Run")
    logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
