import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
import logging

try:
    import redis  # type: ignore
except Exception:
    redis = None

logger = logging.getLogger(__name__)

CUSTOMER_CACHE_TTL = int(os.getenv("CUSTOMER_CACHE_TTL", 86400))
INVENTORY_CACHE_TTL = int(os.getenv("INVENTORY_CACHE_TTL", 86400))

REDIS_URL = os.getenv("REDIS_URL")
redis_client = None
if REDIS_URL and redis is not None:
    try:
        redis_client = redis.Redis.from_url(REDIS_URL)
        redis_client.ping()
    except Exception as e:
        logger.error("Failed to connect to Redis: %s", e)
        redis_client = None

_memory_cache = {}


def _now() -> datetime:
    return datetime.utcnow()


def set_cache(key: str, value, ttl_seconds: int) -> None:
    expire_at = _now() + timedelta(seconds=ttl_seconds)
    if redis_client:
        try:
            redis_client.setex(key, ttl_seconds, pickle.dumps(value))
            return
        except Exception as e:
            logger.error("Redis set failed: %s", e)
    _memory_cache[key] = (value, expire_at)


def get_cache(key: str):
    if redis_client:
        try:
            data = redis_client.get(key)
            if data is not None:
                return pickle.loads(data)
        except Exception as e:
            logger.error("Redis get failed: %s", e)
    entry = _memory_cache.get(key)
    if entry:
        value, expire_at = entry
        if expire_at > _now():
            return value
        del _memory_cache[key]
    return None


def invalidate_cache(key: str) -> None:
    if redis_client:
        try:
            redis_client.delete(key)
        except Exception as e:
            logger.error("Redis delete failed: %s", e)
    _memory_cache.pop(key, None)


# --- Offer Caching Helpers ---

def compute_config_hash(config: dict) -> str:
    cfg_json = json.dumps(config, sort_keys=True)
    return hashlib.md5(cfg_json.encode("utf-8")).hexdigest()


def get_cached_offers(customer_id: str, config_hash: str):
    return get_cache(f"offers:{customer_id}:{config_hash}")


def set_cached_offers(customer_id: str, config_hash: str, df, ttl: int = 86400) -> None:
    set_cache(f"offers:{customer_id}:{config_hash}", df, ttl)
