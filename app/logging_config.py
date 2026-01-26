import logging
import sys


def setup_logging():
    """Configure logging for the booking system."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("booking_system")


# Initialize logger
logger = setup_logging()
