import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging(level=logging.INFO):
    """Configure logging for the application"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Add a file handler only in production to avoid triggering Uvicorn's reload loop
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        log_path = os.path.join("/tmp", "tradeup_engine.log")
        try:
            logging.getLogger(__name__).addHandler(
                RotatingFileHandler(
                    log_path,
                    maxBytes=5 * 1024 * 1024,  # 5 MB
                    backupCount=3,
                    delay=True,
                )
            )
        except Exception as e:
            # Fall back to console-only logging if file handler cannot be created
            logging.getLogger(__name__).warning(
                "Could not attach file handler (%s). Continuing with console logging only.",
                e,
            )

    return logging.getLogger(__name__)