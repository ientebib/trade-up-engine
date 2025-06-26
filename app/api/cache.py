"""
Cache management API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import logging
from data.cache_manager import cache_manager
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/status")
@handle_api_errors("get cache status")
async def get_cache_status():
    """Get current cache status and statistics"""
    return cache_manager.get_status()


@router.post("/refresh")
@handle_api_errors("refresh cache")
async def refresh_cache(key: str = None):
    """Force refresh specific cache key or all cached data"""
    if key:
        cache_manager.invalidate(key)
        logger.info(f"🔄 Force refreshed cache key: {key}")
        return {"message": f"Cache key '{key}' invalidated", "success": True}
    else:
        cache_manager.invalidate()
        logger.info("🔄 Force refreshed entire cache")
        return {"message": "All cache cleared", "success": True}


@router.post("/invalidate/pattern")
@handle_api_errors("invalidate cache by pattern")
async def invalidate_by_pattern(pattern: str):
    """
    Invalidate cache entries matching a pattern
    Examples: 'customer_*', 'offers_*', '*_stats'
    """
    cache_manager.invalidate(pattern=pattern)
    return {"message": f"Invalidated caches matching pattern: {pattern}", "success": True}


@router.post("/invalidate/entity")
@handle_api_errors("invalidate entity cache")
async def invalidate_entity(entity_type: str, entity_id: str = None):
    """
    Invalidate all caches related to an entity type
    
    Args:
        entity_type: 'customer', 'inventory', or 'offer'
        entity_id: Optional specific entity ID
    """
    valid_types = ['customer', 'inventory', 'offer']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    cache_manager.invalidate_related(entity_type, entity_id)
    
    if entity_id:
        return {"message": f"Invalidated {entity_type} cache for ID: {entity_id}", "success": True}
    else:
        return {"message": f"Invalidated all {entity_type} caches", "success": True}


@router.post("/toggle")
@handle_api_errors("toggle cache")
async def toggle_cache(enabled: bool):
    """Enable or disable caching"""
    cache_manager.set_enabled(enabled)
    return {
        "message": f"Cache {'enabled' if enabled else 'disabled'}",
        "enabled": enabled,
        "success": True
    }


@router.post("/ttl")
@handle_api_errors("update cache TTL")
async def update_cache_ttl(hours: float):
    """Update cache TTL in hours"""
    if hours < 0.1 or hours > 24:
        raise HTTPException(status_code=400, detail="TTL must be between 0.1 and 24 hours")
    
    cache_manager.set_ttl(hours)
    return {
        "message": f"Cache TTL updated to {hours} hours",
        "ttl_hours": hours,
        "success": True
    }