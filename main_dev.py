#!/usr/bin/env python3
"""
Trade-Up Engine - Development Version
Optimized for virtual agent environments with network restrictions
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from core.logging_config import setup_logging
from core.cache_utils import get_redis_status
import random

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Set development environment variables
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('DISABLE_EXTERNAL_CALLS', 'true')
os.environ.setdefault('USE_MOCK_DATA', 'true')

# Import core modules
try:
    from core.engine import TradeUpEngine
    from core.config_manager import ConfigManager
    from app.app_factory import create_app
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("🔧 Please run the setup script first: ./run_local.sh setup")
    sys.exit(1)

# Create FastAPI app via the shared factory
app = create_app("dev")

# Access shared components
templates = app.state.templates
data_loader = app.state.data_loader

# Initialize core components
config_manager = ConfigManager()
engine = TradeUpEngine()

def calculate_demo_metrics() -> dict:
    """Return mocked portfolio metrics for the dashboard."""
    customers_df = data_loader.load_customers()
    inventory_df = data_loader.load_inventory()

    total_customers = len(customers_df)
    total_offers = total_customers * 3

    metrics = {
        "total_customers": total_customers,
        "total_offers": total_offers,
        "avg_npv": 12000,
        "avg_offers_per_customer": 3.0,
        "tier_distribution": {"Refresh": 40, "Upgrade": 45, "Max Upgrade": 15},
        "top_cars": [],
    }

    if not inventory_df.empty:
        sample = inventory_df.head(10)
        metrics["top_cars"] = [
            {"Model": row["model"], "Estimated_Matches": random.randint(5, 20)}
            for _, row in sample.iterrows()
        ]

    return metrics

app.state.metrics_func = calculate_demo_metrics
app.state.load_customers_func = data_loader.load_customers

# Development mode indicator
@app.middleware("http")
async def development_middleware(request: Request, call_next):
    """Add development mode headers"""
    response = await call_next(request)
    response.headers["X-Development-Mode"] = "true"
    response.headers["X-External-Calls"] = "disabled"
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for development"""
    return {
        "status": "healthy",
        "environment": "development",
        "external_calls": "disabled",
        "mock_data": "enabled",
        "data_sources": "CSV and sample data only",
        "redis_connected": get_redis_status(),
    }

# Main dashboard

# Development info endpoint
@app.get("/dev-info")
async def development_info():
    """Development environment information"""
    return {
        "environment": "development",
        "external_calls_disabled": True,
        "mock_data_enabled": True,
        "network_restrictions": "handled",
        "virtual_agent_compatible": True,
        "data_sources": ["CSV files", "Sample data"],
        "no_redshift_connection": True,
        "available_endpoints": [
            "/",
            "/customers", 
            "/customer/{id}",
            "/calculations",
            "/config",
            "/health",
            "/dev-info",
            "/api/*"
        ]
    }


if __name__ == "__main__":
    logger.info("🚀 Starting Trade-Up Engine in development mode...")
    logger.info("🔧 External network calls are disabled")
    logger.info("📁 Using CSV files and sample data")
    logger.info("🚫 No Redshift connection required")
    logger.info("🌐 Server will be available at: http://localhost:8000")
    logger.info("📊 Health check: http://localhost:8000/health")
    logger.info("🔍 Dev info: http://localhost:8000/dev-info")
    logger.info("")
    
    uvicorn.run(
        "main_dev:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
