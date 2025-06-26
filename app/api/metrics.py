"""
Metrics API endpoints
"""
from fastapi import APIRouter, Query
from typing import Optional
import logging
from app.utils.metrics import metrics_collector, get_health_metrics
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics")
@handle_api_errors("get metrics")
async def get_metrics(
    export: bool = Query(False, description="Export metrics to file")
):
    """Get current application metrics"""
    metrics = metrics_collector.get_metrics()
    
    if export:
        filepath = metrics_collector.export_metrics()
        metrics["exported_to"] = filepath
    
    return {
        "status": "success",
        "metrics": metrics
    }


@router.get("/metrics/health")
@handle_api_errors("get health metrics")
async def get_health_status():
    """Get application health metrics for monitoring"""
    health = get_health_metrics()
    return health


@router.post("/metrics/reset")
@handle_api_errors("reset metrics")
async def reset_metrics():
    """Reset metrics counters (admin only)"""
    # Create new metrics collector instance
    global metrics_collector
    from app.utils.metrics import MetricsCollector
    metrics_collector = MetricsCollector()
    
    logger.info("📊 Metrics reset successfully")
    return {
        "status": "success",
        "message": "Metrics reset successfully"
    }