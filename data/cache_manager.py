"""
Smart caching layer for Trade-Up Engine
- 4-hour TTL by default (configurable)
- Cache status tracking
- Force refresh capability
- Thread-safe implementation
"""
import time
import threading
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
import logging
from app.utils.metrics import metrics_collector
from app.constants import DEFAULT_CACHE_TTL_HOURS

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with metadata"""
    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """Check if this entry has expired"""
        return time.time() - self.created_at > self.ttl_seconds
    
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds"""
        return int(time.time() - self.created_at)
    
    def age_human(self) -> str:
        """Get human-readable age"""
        age = self.age_seconds()
        if age < 60:
            return f"{age}s"
        elif age < 3600:
            return f"{age // 60}m"
        else:
            return f"{age // 3600}h {(age % 3600) // 60}m"


class CacheManager:
    """
    Thread-safe cache manager with TTL and monitoring
    """
    def __init__(self, default_ttl_hours: float = DEFAULT_CACHE_TTL_HOURS, enabled: bool = True):
        self.default_ttl_seconds = int(default_ttl_hours * 3600)
        self.enabled = enabled
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "force_refreshes": 0,
            "last_refresh": {}
        }
        logger.info(f"🗄️ Cache manager initialized: TTL={default_ttl_hours}h, Enabled={enabled}")
    
    def get(self, key: str, fetch_func=None, ttl_seconds: Optional[int] = None):
        """
        Get from cache or fetch if missing/expired
        
        Args:
            key: Cache key
            fetch_func: Function to call if cache miss
            ttl_seconds: Override default TTL for this entry
        
        Returns:
            Tuple of (data, from_cache: bool)
        """
        if not self.enabled and fetch_func:
            logger.debug(f"❌ Cache disabled, fetching {key} directly")
            data = fetch_func()
            return data, False
        
        with self._lock:
            # Check if we have valid cached data
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    entry.access_count += 1
                    self._stats["hits"] += 1
                    metrics_collector.track_cache_hit(key)
                    logger.info(f"✅ Cache hit: {key} (age: {entry.age_human()})")
                    return entry.data, True
                else:
                    logger.info(f"⏰ Cache expired: {key} (age: {entry.age_human()})")
                    del self._cache[key]
            
            self._stats["misses"] += 1
            metrics_collector.track_cache_miss(key)
        
        # Cache miss or expired - fetch new data
        if fetch_func:
            logger.info(f"🔄 Cache miss: {key} - fetching fresh data")
            start_time = time.time()
            data = fetch_func()
            fetch_time = time.time() - start_time
            
            # Store in cache
            ttl = ttl_seconds or self.default_ttl_seconds
            with self._lock:
                self._cache[key] = CacheEntry(data, ttl)
                self._stats["last_refresh"][key] = datetime.now()
            
            logger.info(f"💾 Cached {key} (fetch took {fetch_time:.2f}s, TTL: {ttl}s)")
            return data, False
        
        return None, False
    
    def invalidate(self, key: Optional[str] = None, pattern: Optional[str] = None):
        """
        Invalidate cache entries
        
        Args:
            key: Specific key to invalidate
            pattern: Pattern to match keys (e.g., "customer_*" to invalidate all customer data)
        """
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                    logger.info(f"🗑️ Invalidated cache key: {key}")
                    self._stats["force_refreshes"] += 1
                    metrics_collector.track_cache_invalidation(key)
            elif pattern:
                # Invalidate all keys matching pattern
                keys_to_remove = []
                for cache_key in self._cache.keys():
                    if pattern.endswith('*') and cache_key.startswith(pattern[:-1]):
                        keys_to_remove.append(cache_key)
                    elif pattern.startswith('*') and cache_key.endswith(pattern[1:]):
                        keys_to_remove.append(cache_key)
                    elif '*' in pattern:
                        prefix, suffix = pattern.split('*', 1)
                        if cache_key.startswith(prefix) and cache_key.endswith(suffix):
                            keys_to_remove.append(cache_key)
                
                for k in keys_to_remove:
                    del self._cache[k]
                
                if keys_to_remove:
                    logger.info(f"🗑️ Invalidated {len(keys_to_remove)} cache keys matching pattern: {pattern}")
            else:
                self._cache.clear()
                logger.info("🗑️ Cleared entire cache")
    
    def invalidate_related(self, entity_type: str, entity_id: Optional[str] = None):
        """
        Invalidate cache entries related to a specific entity
        
        Args:
            entity_type: Type of entity ('customer', 'inventory', 'offer')
            entity_id: Specific entity ID or None for all of that type
        """
        if entity_type == 'customer':
            if entity_id:
                # Invalidate specific customer data
                self.invalidate(f"customer_{entity_id}")
                self.invalidate(pattern=f"offers_{entity_id}_*")
            else:
                # Invalidate all customer-related data
                self.invalidate(pattern="customer_*")
                self.invalidate("customer_stats")
        
        elif entity_type == 'inventory':
            # Inventory changes affect many things
            self.invalidate("inventory_stats")
            self.invalidate(pattern="inventory_*")
            # Also invalidate offers since they depend on inventory
            self.invalidate(pattern="offers_*")
            logger.info("🔄 Inventory changed - invalidated inventory and offer caches")
        
        elif entity_type == 'offer':
            self.invalidate("offer_stats")
            if entity_id:
                self.invalidate(pattern=f"offers_{entity_id}_*")
    
    def get_status(self) -> Dict[str, Any]:
        """Get cache status and statistics"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            # Get info about cached entries
            entries = []
            for key, entry in self._cache.items():
                entries.append({
                    "key": key,
                    "age": entry.age_human(),
                    "age_seconds": entry.age_seconds(),
                    "expires_in": max(0, entry.ttl_seconds - entry.age_seconds()),
                    "access_count": entry.access_count,
                    "size_estimate": len(str(entry.data)) if hasattr(entry.data, '__len__') else 0
                })
            
            return {
                "enabled": self.enabled,
                "default_ttl_hours": self.default_ttl_seconds / 3600,
                "entries": entries,
                "stats": {
                    "hits": self._stats["hits"],
                    "misses": self._stats["misses"],
                    "hit_rate": round(hit_rate, 2),
                    "force_refreshes": self._stats["force_refreshes"],
                    "total_requests": total_requests
                },
                "last_refresh": {
                    k: v.isoformat() if isinstance(v, datetime) else v 
                    for k, v in self._stats["last_refresh"].items()
                }
            }
    
    def set_enabled(self, enabled: bool):
        """Enable or disable caching"""
        self.enabled = enabled
        if not enabled:
            self.invalidate()  # Clear cache when disabling
        logger.info(f"🔧 Cache {'enabled' if enabled else 'disabled'}")
    
    def set_ttl(self, ttl_hours: float):
        """Update default TTL"""
        self.default_ttl_seconds = int(ttl_hours * 3600)
        logger.info(f"🔧 Cache TTL updated to {ttl_hours} hours")


# Import configuration
try:
    from config.cache_config import CACHE_CONFIG
    default_ttl = CACHE_CONFIG.get("default_ttl_hours", 4.0)
    enabled = CACHE_CONFIG.get("enabled", True)
except ImportError:
    logger.warning("Cache config not found, using defaults")
    default_ttl = 4.0
    enabled = True

# Global cache instance
cache_manager = CacheManager(default_ttl_hours=default_ttl, enabled=enabled)