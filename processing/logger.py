import logging
import logging.config
from datetime import datetime
import os


def setup_logger():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.today().date()}.log")

    # Explicitly create the log file
    with open(log_file, "a") as f:
        pass  # This ensures the file is created without writing any content

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s - %(filename)s <line: %(lineno)d>] %(message)s",
        level=logging.INFO,  # Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        handlers=[
            # logging.StreamHandler(),  # This sends log output to the console
            # You can also add FileHandler() if you want to log to xa file
            logging.FileHandler(log_file)
        ],
    )


# Run the logger setup function on import
setup_logger()

# Optional: Retrieve the root logger instance
logger = logging.getLogger(__name__)
