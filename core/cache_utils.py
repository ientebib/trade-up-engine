import os
import json
import time
import hashlib
import pickle

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
    except Exception:
        _redis_client = None

# Fallback in-memory cache
_memory_cache = {}

# TTL settings in seconds
CUSTOMER_CACHE_TTL = int(os.getenv("CUSTOMER_CACHE_TTL", 86400))
INVENTORY_CACHE_TTL = int(os.getenv("INVENTORY_CACHE_TTL", 86400))


def compute_config_hash(config: dict) -> str:
    """Create a stable hash for a config dictionary."""
    serialized = json.dumps(config, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get(key: str):
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


def _set(key: str, value, ttl: int | None = None):
    if _redis_client:
        _redis_client.set(key, pickle.dumps(value), ex=ttl)
        return
    expire_at = None if ttl is None else time.time() + ttl
    _memory_cache[key] = (value, expire_at)


# Offer cache helpers -------------------------------------------------

def get_cached_offers(customer_id: str, config_hash: str):
    key = f"offers:{customer_id}:{config_hash}"
    return _get(key)


def set_cached_offers(customer_id: str, config_hash: str, offers_df):
    key = f"offers:{customer_id}:{config_hash}"
    _set(key, offers_df, CUSTOMER_CACHE_TTL)


# Inventory cache helpers ---------------------------------------------

def get_cached_inventory():
    return _get("inventory")


def set_cached_inventory(df):
    _set("inventory", df, INVENTORY_CACHE_TTL)


# Customer cache helpers ----------------------------------------------

def get_cached_customers():
    return _get("customers")


def set_cached_customers(df):
    _set("customers", df, CUSTOMER_CACHE_TTL)
