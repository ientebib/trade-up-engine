"""
Cache configuration settings
"""

# Cache settings - easily adjustable
CACHE_CONFIG = {
    "enabled": True,                    # Master switch for caching
    "default_ttl_hours": 4.0,          # Default time-to-live in hours
    "inventory_ttl_hours": 4.0,        # Specific TTL for inventory data
    "stats_ttl_hours": 1.0,            # Specific TTL for statistics
    "max_entries": 100,                # Maximum number of cache entries
    "enable_metrics": True,            # Track hit/miss statistics
    "force_refresh_on_error": True,    # Clear cache if errors occur
}

# Cache keys used in the application
CACHE_KEYS = {
    "inventory_all": "All inventory data from Redshift",
    "inventory_stats": "Inventory statistics",
    "customer_search": "Customer search results",
}

# Feature flags for different cache strategies
CACHE_FEATURES = {
    "use_redis": False,                # Future: Use Redis instead of in-memory
    "use_disk_backup": False,          # Future: Backup to disk
    "compress_large_entries": False,   # Future: Compress large data
}