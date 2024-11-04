import logging
import logging.config
from datetime import datetime


def setup_logger():
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s - %(filename)s <line: %(lineno)d>] %(message)s",
        level=logging.INFO,  # Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        handlers=[
            # logging.StreamHandler(),  # This sends log output to the console
            # You can also add FileHandler() if you want to log to xa file
            logging.FileHandler(f"processing/logs/{datetime.today().date()}.log")
        ],
    )


# Run the logger setup function on import
setup_logger()

# Optional: Retrieve the root logger instance
logger = logging.getLogger(__name__)
