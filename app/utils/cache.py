"""
Simple caching mechanism for offers
"""
import functools
import hashlib
import json
from datetime import datetime, timedelta


class OfferCache:
    def __init__(self, ttl_minutes=15):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def __len__(self):
        """Return number of cached entries"""
        return len(self.cache)
    
    def get_key(self, customer_id: str, fees: dict = None):
        """Generate cache key from customer ID and fees"""
        fees_str = json.dumps(fees or {}, sort_keys=True)
        return hashlib.md5(f"{customer_id}:{fees_str}".encode()).hexdigest()
    
    def get(self, key: str):
        """Get from cache if not expired"""
        # DISABLED - Always return None to force recalculation
        return None
    
    def set(self, key: str, data: dict):
        """Set in cache with expiration"""
        self.cache[key] = {
            'data': data,
            'expires': datetime.now() + self.ttl
        }


# Global cache instance
offer_cache = OfferCache()