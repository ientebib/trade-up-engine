import logging

def setup_logging(level=logging.INFO):
    """Configure logging for the application if not already configured."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
