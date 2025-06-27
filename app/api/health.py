"""
Health check and metrics API endpoints
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
@handle_api_errors("health check")
async def health_check():
    """Health check API endpoint with dependency checks"""
    from app.utils.helpers import get_data_context
    from data import database
    from data.connection_pool import get_connection_pool
    from data.circuit_breaker import get_redshift_breaker
    from data.cache_manager import cache_manager
    
    data_ctx = get_data_context()
    health_status = "healthy"
    issues = []
    
    # Check database connections
    db_status = database.test_database_connection()
    
    # Check customer data (critical)
    if not db_status["customers"]["connected"]:
        health_status = "unhealthy"
        issues.append("Customer data unavailable")
    
    # Check Redshift (degraded if down)
    if not db_status["inventory"]["connected"]:
        if health_status == "healthy":
            health_status = "degraded"
        issues.append("Redshift connection failed")
    
    # Check connection pool
    try:
        pool = get_connection_pool()
        pool_stats = pool.get_stats()
        if pool_stats["available_connections"] == 0 and pool_stats["total_connections"] >= pool_stats["max_connections"]:
            if health_status == "healthy":
                health_status = "degraded"
            issues.append("Connection pool exhausted")
    except Exception as e:
        logger.error(f"Failed to check connection pool: {e}")
        issues.append("Connection pool check failed")
    
    # Check circuit breaker
    breaker = get_redshift_breaker()
    breaker_status = breaker.get_status()
    if breaker_status["state"] == "open":
        if health_status == "healthy":
            health_status = "degraded"
        issues.append(f"Redshift circuit breaker open (failures: {breaker_status['failure_count']})")
    
    # Check cache
    cache_status = cache_manager.get_status()
    
    response = {
        "status": health_status,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "engine": "simple_v2",
        "mode": data_ctx["data_source"],
        "data": {
            "customers": db_status["customers"]["count"],
            "inventory": db_status["inventory"]["count"],
            "source": data_ctx["data_source"]
        },
        "dependencies": {
            "customer_data": "ok" if db_status["customers"]["connected"] else "failed",
            "redshift": "ok" if db_status["inventory"]["connected"] else "failed",
            "connection_pool": pool_stats if 'pool_stats' in locals() else "unknown",
            "circuit_breaker": breaker_status["state"],
            "cache": "enabled" if cache_status["enabled"] else "disabled"
        }
    }
    
    if issues:
        response["issues"] = issues
    
    # Return appropriate status code
    status_code = 200 if health_status == "healthy" else 503 if health_status == "unhealthy" else 200
    
    return JSONResponse(response, status_code=status_code)


@router.get("/metrics")
@handle_api_errors("get metrics")
async def get_metrics():
    """Get real-time metrics for dashboard"""
    from app.utils.metrics import metrics_collector
    
    # Get real metrics from the metrics collector
    metrics = metrics_collector.get_metrics()
    
    # Extract key metrics for dashboard
    offers_data = metrics.get("offers", {})
    cache_data = metrics.get("cache", {})
    requests_data = metrics.get("requests", {})
    
    # Calculate cache hit rate
    cache_total = cache_data.get("hits", 0) + cache_data.get("misses", 0)
    cache_hit_rate = (cache_data.get("hits", 0) / cache_total * 100) if cache_total > 0 else 0
    
    # Calculate average response time
    response_times = requests_data.get("response_times", [])
    avg_response_time = sum(response_times[-100:]) / len(response_times[-100:]) if response_times else 0
    
    # Get top customers (this would need to be tracked separately)
    # For now, return the endpoint usage as a proxy
    by_endpoint = requests_data.get("by_endpoint", {})
    
    return {
        "offers_generated_today": offers_data.get("generated", 0),
        "average_response_time": round(avg_response_time, 3),
        "cache_hit_rate": round(cache_hit_rate, 1),
        "active_sessions": metrics.get("system", {}).get("active_requests", 0),
        "total_requests": requests_data.get("total", 0),
        "offers_by_tier": offers_data.get("by_tier", {}),
        "cache_stats": {
            "hits": cache_data.get("hits", 0),
            "misses": cache_data.get("misses", 0)
        },
        "errors": metrics.get("errors", {}).get("total", 0)
    }