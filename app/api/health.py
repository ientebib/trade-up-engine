"""
Health check and metrics API endpoints
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """Health check API endpoint"""
    from app.utils.helpers import get_data_context
    from app.core.data import customers_df, inventory_df
    
    data_ctx = get_data_context()
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "engine": "simple_v2",
        "mode": data_ctx["data_source"],
        "data": {
            "customers": len(customers_df),
            "inventory": len(inventory_df),
            "source": data_ctx["data_source"]
        }
    })


@router.get("/metrics")
async def get_metrics():
    """Get real-time metrics for dashboard"""
    # TODO: Implement real metrics collection
    # For now, return mock data
    return {
        "offers_generated_today": 342,
        "average_response_time": 1.2,
        "cache_hit_rate": 68,
        "active_sessions": 3,
        "top_customers": [
            {"id": "TMCJ33A32GJ053451", "offers": 28},
            {"id": "KAVA12345678901234", "offers": 24},
            {"id": "CUST98765432109876", "offers": 19}
        ]
    }