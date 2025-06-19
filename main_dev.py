#!/usr/bin/env python3
"""
Trade-Up Engine - Development Version
Optimized for virtual agent environments with network restrictions
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import logging

# Configure logging for development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set development environment variables
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('DISABLE_EXTERNAL_CALLS', 'true')
os.environ.setdefault('USE_MOCK_DATA', 'true')

# Import core modules
try:
    from core.engine import TradeUpEngine
    from core.data_loader_dev import dev_data_loader  # Use development data loader
    from core.config_manager import ConfigManager
    from app.api.routes import router as api_router
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔧 Please run the setup script first: ./setup.sh")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="Trade-Up Engine - Development",
    description="Development version optimized for virtual agents",
    version="1.0.0-dev"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Initialize core components
config_manager = ConfigManager()
data_loader = dev_data_loader  # Use development data loader
engine = TradeUpEngine()

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
        "data_sources": "CSV and sample data only"
    }

# Include API routes
app.include_router(api_router, prefix="/api")

# Main dashboard
@app.get("/", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    """Main dashboard page"""
    try:
        return templates.TemplateResponse("main_dashboard.html", {"request": request})
    except Exception as e:
        logging.error(f"Error rendering main dashboard: {e}")
        return HTMLResponse(f"""
        <html>
            <head><title>Trade-Up Engine - Development</title></head>
            <body>
                <h1>Trade-Up Engine - Development Mode</h1>
                <p>External network calls are disabled for virtual agent compatibility.</p>
                <p>Using CSV files and sample data instead of Redshift.</p>
                <p>Error: {e}</p>
                <p><a href="/health">Health Check</a></p>
            </body>
        </html>
        """)

# Customer list page
@app.get("/customers", response_class=HTMLResponse)
async def customer_list(request: Request):
    """Customer list page"""
    try:
        return templates.TemplateResponse("customer_list.html", {"request": request})
    except Exception as e:
        logging.error(f"Error rendering customer list: {e}")
        return HTMLResponse(f"<h1>Customer List</h1><p>Error: {e}</p>")

# Customer view page
@app.get("/customer/{customer_id}", response_class=HTMLResponse)
async def customer_view(request: Request, customer_id: str):
    """Customer view page"""
    try:
        return templates.TemplateResponse("customer_view.html", {"request": request, "customer_id": customer_id})
    except Exception as e:
        logging.error(f"Error rendering customer view: {e}")
        return HTMLResponse(f"<h1>Customer View</h1><p>Error: {e}</p>")

# Calculations page
@app.get("/calculations", response_class=HTMLResponse)
async def calculations_page(request: Request):
    """Calculations page"""
    try:
        return templates.TemplateResponse("calculations.html", {"request": request})
    except Exception as e:
        logging.error(f"Error rendering calculations: {e}")
        return HTMLResponse(f"<h1>Calculations</h1><p>Error: {e}</p>")

# Global config page
@app.get("/config", response_class=HTMLResponse)
async def global_config_page(request: Request):
    """Global configuration page"""
    try:
        return templates.TemplateResponse("global_config.html", {"request": request})
    except Exception as e:
        logging.error(f"Error rendering global config: {e}")
        return HTMLResponse(f"<h1>Global Configuration</h1><p>Error: {e}</p>")

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
    print("🚀 Starting Trade-Up Engine in development mode...")
    print("🔧 External network calls are disabled")
    print("📁 Using CSV files and sample data")
    print("🚫 No Redshift connection required")
    print("🌐 Server will be available at: http://localhost:8000")
    print("📊 Health check: http://localhost:8000/health")
    print("🔍 Dev info: http://localhost:8000/dev-info")
    print()
    
    uvicorn.run(
        "main_dev:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
