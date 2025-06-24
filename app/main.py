"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import uvicorn

from utils.logging import setup_logging
from .core.startup import startup_event
from .core.error_handlers import not_found_handler, internal_error_handler

# Import routers
from .api import customers, offers, health, search, config
from .routes import pages

# Setup logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kavak Trade-Up Engine",
    description="Modern, fast, and intelligent trade-up offer generation",
    version="2.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(customers.router)
app.include_router(offers.router)
app.include_router(health.router)
app.include_router(search.router)
app.include_router(config.router)
app.include_router(pages.router)

# Register startup event
@app.on_event("startup")
async def on_startup():
    await startup_event()

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
    
    logger.info(f"🖥️ Using {app.state.executor._max_workers if hasattr(app, 'state') and hasattr(app.state, 'executor') else 'N/A'} worker threads")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )