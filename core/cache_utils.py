import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Base cache directories
CACHE_DIR = Path("cache")
OFFERS_CACHE_DIR = CACHE_DIR / "offers"
INVENTORY_CACHE_DIR = CACHE_DIR / "inventory"

# Ensure directories exist
OFFERS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
INVENTORY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


def compute_config_hash(config: dict) -> str:
    """Return a stable hash for a configuration dictionary."""
    config_json = json.dumps(config, sort_keys=True)
    return hashlib.md5(config_json.encode("utf-8")).hexdigest()


def _offers_cache_path(customer_id: str, config_hash: str) -> Path:
    filename = f"{customer_id}_{config_hash}.parquet"
    return OFFERS_CACHE_DIR / filename


def get_cached_offers(customer_id: str, config_hash: str) -> Optional[pd.DataFrame]:
    """Load cached offers if available."""
    path = _offers_cache_path(customer_id, config_hash)
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception as e:
            logger.error(f"Failed to read cached offers {path}: {e}")
    return None


def set_cached_offers(customer_id: str, config_hash: str, df: pd.DataFrame) -> None:
    """Persist offers DataFrame to cache."""
    path = _offers_cache_path(customer_id, config_hash)
    try:
        df.to_parquet(path, index=False)
    except Exception as e:
        logger.error(f"Failed to write offers cache {path}: {e}")


def _inventory_cache_path() -> Path:
    today = datetime.today().strftime("%Y%m%d")
    return INVENTORY_CACHE_DIR / f"inventory_{today}.parquet"


def inventory_cache_exists_today() -> bool:
    """Check whether today's inventory cache file exists."""
    return _inventory_cache_path().exists()


def load_inventory_cache() -> pd.DataFrame:
    """Load today's inventory cache if available."""
    path = _inventory_cache_path()
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception as e:
            logger.error(f"Failed to read inventory cache {path}: {e}")
    return pd.DataFrame()


def save_inventory_cache(df: pd.DataFrame) -> None:
    """Save inventory DataFrame to today's cache file."""
    path = _inventory_cache_path()
    try:
        df.to_parquet(path, index=False)
    except Exception as e:
        logger.error(f"Failed to write inventory cache {path}: {e}")
