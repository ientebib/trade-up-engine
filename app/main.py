"""
Main FastAPI application entry point
"""
import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.utils.logging import setup_logging

# Import routers
from .api import cache, circuit_breaker, config, customers, health, metrics, offers, search
from .core.error_handlers import internal_error_handler, not_found_handler
from .core.startup import startup_event
from .middleware.request_id import RequestIDMiddleware
from .middleware.sanitization import SanitizationMiddleware
from .middleware.timeout import TimeoutMiddleware
from .routes import pages, deal_architect, scenarios, pipeline

# Setup logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kavak Trade-Up Engine",
    description="""
    ## Trade-Up Engine API
    
    Modern, fast, and intelligent trade-up offer generation for Kavak customers.
    
    ### Features
    - 🚀 Real-time offer generation with NPV optimization
    - 💰 Custom financial configurations per customer
    - 📊 Bulk processing for multiple customers
    - 🔄 Smart caching with invalidation
    - 📈 Comprehensive metrics and monitoring
    - 🔒 Security-first design with input validation
    
    ### Key Endpoints
    - **Offers**: Generate trade-up offers for customers
    - **Customers**: Search and manage customer data
    - **Configuration**: Manage system configuration
    - **Health**: Monitor system health and dependencies
    - **Metrics**: Track performance and usage
    
    ### Authentication
    Currently uses API key authentication (contact admin for access)
    
    ### Rate Limits
    - Standard endpoints: 100 requests/minute
    - Bulk endpoints: 10 requests/minute
    - Health checks: No limit
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "offers",
            "description": "Generate and manage trade-up offers"
        },
        {
            "name": "customers", 
            "description": "Customer data operations"
        },
        {
            "name": "config",
            "description": "System configuration management"
        },
        {
            "name": "health",
            "description": "Health monitoring endpoints"
        },
        {
            "name": "cache",
            "description": "Cache management operations"
        },
        {
            "name": "metrics",
            "description": "Performance metrics and monitoring"
        },
        {
            "name": "monitoring",
            "description": "Circuit breaker and system monitoring"
        },
        {
            "name": "pages",
            "description": "Web interface pages"
        }
    ]
)

# Add middleware (order matters - timeout should be inner)
app.add_middleware(TimeoutMiddleware, timeout_seconds=30)
app.add_middleware(SanitizationMiddleware)
app.add_middleware(RequestIDMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API v1 routers with versioned prefix (strip existing /api prefix)
app.include_router(customers.router, prefix="/v1")
app.include_router(offers.router, prefix="/v1")
app.include_router(health.router, prefix="/v1")
app.include_router(search.router, prefix="/v1")
app.include_router(config.router, prefix="/v1")
app.include_router(cache.router, prefix="/v1")
app.include_router(metrics.router, prefix="/v1")
app.include_router(circuit_breaker.router, prefix="/v1")

# Keep unversioned endpoints for backward compatibility
app.include_router(customers.router)
app.include_router(offers.router)
app.include_router(health.router)
app.include_router(search.router)
app.include_router(config.router)
app.include_router(cache.router)
app.include_router(metrics.router)
app.include_router(circuit_breaker.router)

# Pages don't need versioning
app.include_router(pages.router)
app.include_router(deal_architect.router)
app.include_router(scenarios.router)
app.include_router(pipeline.router)

# Register startup event
@app.on_event("startup")
async def on_startup():
    await startup_event()

# Register shutdown event
@app.on_event("shutdown")
async def on_shutdown():
    """Clean up resources on shutdown"""
    logger.info("🛑 Shutting down Trade-Up Engine...")
    
    # Stop bulk queue
    from app.services.bulk_queue import get_bulk_queue
    try:
        queue = get_bulk_queue()
        await queue.stop()
    except Exception as e:
        logger.error(f"Error stopping bulk queue: {e}")
        # Don't re-raise during shutdown to allow graceful exit
    
    # Close connection pool
    from data.connection_pool import close_connection_pool
    try:
        close_connection_pool()
    except Exception as e:
        logger.error(f"Error closing connection pool: {e}")
        # Don't re-raise during shutdown to allow graceful exit
    
    logger.info("👋 Shutdown complete")

# Register error handlers
app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, internal_error_handler)


if __name__ == "__main__":
    # Run with uvicorn when executed directly
    import os

    # Server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("ENV", "development") == "development"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )