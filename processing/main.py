from collection import collect
from extraction import extract
from logger import logger
import time
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting main processing")

    # collect
    collect.main()

    # extraction
    extract.main()

    end_time = time.time()
    logger.info("Finished main processing Run")
    logger.info(f"Elapsed time {timedelta(seconds=end_time - start_time)}")
