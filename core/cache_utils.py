import os
import json
import time
import hashlib
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure cache directory exists
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

_redis_client = None
if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
    try:
        _redis_client = redis.from_url(os.getenv("REDIS_URL"))
        _redis_client.ping()
        logger.info("✅ Connected to Redis")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        _redis_client = None

# Fallback in-memory cache
_memory_cache = {}

# TTL settings in seconds
CUSTOMER_CACHE_TTL = int(os.getenv("CUSTOMER_CACHE_TTL", 86400))
INVENTORY_CACHE_TTL = int(os.getenv("INVENTORY_CACHE_TTL", 86400))


def compute_config_hash(config: dict) -> str:
    """Create a stable hash for a config dictionary."""
    try:
        serialized = json.dumps(config, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to compute config hash: {e}")
        return str(hash(str(config)))


def _get(key: str):
    """Get data from cache with better error handling."""
    try:
        if _redis_client:
            raw = _redis_client.get(key)
            if raw is not None:
                return pickle.loads(raw)
            return None

        item = _memory_cache.get(key)
        if item:
            value, exp = item
            if exp is None or exp > time.time():
                return value
            del _memory_cache[key]
        return None
    except Exception as e:
        logger.warning(f"Cache read error for key '{key}': {e}")
        return None


def _set(key: str, value, ttl: int | None = None):
    """Set data in cache with better error handling."""
    try:
        if _redis_client:
            _redis_client.set(key, pickle.dumps(value), ex=ttl)
            return
        expire_at = None if ttl is None else time.time() + ttl
        _memory_cache[key] = (value, expire_at)
    except Exception as e:
        logger.warning(f"Cache write error for key '{key}': {e}")


# Offer cache helpers -------------------------------------------------


def get_cached_offers(customer_id: str, config_hash: str):
    """Get cached offers with improved error handling."""
    key = f"offers:{customer_id}:{config_hash}"
    return _get(key)


def set_cached_offers(customer_id: str, config_hash: str, offers_df):
    """Set cached offers with improved error handling."""
    key = f"offers:{customer_id}:{config_hash}"
    _set(key, offers_df, CUSTOMER_CACHE_TTL)


# Inventory cache helpers ---------------------------------------------


def get_cached_inventory():
    """Get cached inventory with improved error handling."""
    return _get("inventory")


def set_cached_inventory(df):
    """Set cached inventory with improved error handling."""
    _set("inventory", df, INVENTORY_CACHE_TTL)


# Customer cache helpers ----------------------------------------------


def get_cached_customers():
    """Get cached customers with improved error handling."""
    return _get("customers")


def set_cached_customers(df):
    """Set cached customers with improved error handling."""
    _set("customers", df, CUSTOMER_CACHE_TTL)


def get_redis_status() -> str:
    """Return a simple status string for the Redis connection."""
    if not REDIS_AVAILABLE:
        return "redis library missing"

    if _redis_client is None:
        return "not configured"

    try:
        _redis_client.ping()
        return "connected"
    except Exception as e:
        return f"error: {type(e).__name__}"
