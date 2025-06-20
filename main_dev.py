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
from core.logging_config import setup_logging
from core.cache_utils import redis_status

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

# Set development environment variables
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('DISABLE_EXTERNAL_CALLS', 'true')
os.environ.setdefault('USE_MOCK_DATA', 'true')

# Import core modules
try:
    from core.engine import TradeUpEngine
    # Use development data loader
    from core.data_loader_dev import dev_data_loader
    from core.config_manager import ConfigManager
    from app.api.routes import router as api_router
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("🔧 Please run the setup script first: ./setup.sh")
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
        "data_sources": "CSV and sample data only",
        "redis_connected": redis_status(),
    }

# Include API routes
app.include_router(api_router, prefix="/api")

# Main dashboard
@app.get("/", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    """Main dashboard page"""
    try:
        # Load data required for the dashboard
        customers = data_loader.load_customers()
        inventory = data_loader.load_inventory()
        
        # Calculate metrics, providing defaults if data is missing
        metrics = {
            "total_customers": len(customers) if customers is not None else 0,
            "total_inventory": len(inventory) if inventory is not None else 0,
            "total_offers": 12500,  # Mocked
            "avg_npv": 15230, # Mocked
            "avg_offers_per_customer": 4.5, # Mocked
            "tier_distribution": { # Mocked data for chart
                "Refresh": 450,
                "Upgrade": 650,
                "Max Upgrade": 150
            },
            "top_cars": [ # Mocked data for chart
                {"Model": "Honda Civic", "Estimated_Matches": 120},
                {"Model": "Toyota RAV4", "Estimated_Matches": 110},
                {"Model": "Ford F-150", "Estimated_Matches": 95},
                {"Model": "Nissan Sentra", "Estimated_Matches": 80},
                {"Model": "Jeep Wrangler", "Estimated_Matches": 75}
            ]
        }
        
        return templates.TemplateResponse(
            "main_dashboard.html",
            {
                "request": request,
                "metrics": metrics,
                "active_page": "dashboard"
            }
        )
    except Exception as e:
        logging.error(f"Error rendering main dashboard: {e}")
        # Render a safe error page if data loading fails
        return HTMLResponse(f"""
        <html>
            <head><title>Trade-Up Engine - Error</title></head>
            <body>
                <h1>An Error Occurred</h1>
                <p>Could not load the dashboard. Please check the logs.</p>
                <p>Error: {e}</p>
            </body>
        </html>
        """)

# Customer list page
@app.get("/customers", response_class=HTMLResponse)
async def customer_list(request: Request):
    """Customer list page"""
    try:
        return templates.TemplateResponse(
            "customer_list.html",
            {"request": request},
        )
    except Exception as e:
        logging.error(f"Error rendering customer list: {e}")
        return HTMLResponse(f"<h1>Customer List</h1><p>Error: {e}</p>")

# Customer view page
@app.get("/customer/{customer_id}", response_class=HTMLResponse)
async def customer_view(request: Request, customer_id: str):
    """Customer view page"""
    try:
        customers = data_loader.load_customers()
        if customers is None or customers.empty:
            raise HTTPException(status_code=500, detail="Customer data could not be loaded.")

        # Find the specific customer
        customer_data = customers[customers['customer_id'] == customer_id].to_dict('records')
        
        if not customer_data:
            raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found.")
            
        customer = customer_data[0]

        return templates.TemplateResponse(
            "customer_view.html",
            {
                "request": request,
                "customer": customer,
                "active_page": "customer"
            },
        )
    except Exception as e:
        logging.error(f"Error rendering customer view for {customer_id}: {e}")
        return HTMLResponse(f"<h1>Customer View - Error</h1><p>Could not render page for customer {customer_id}.</p><p>Error: {e}</p>")

# Calculations page
@app.get("/calculations", response_class=HTMLResponse)
async def calculations_page(request: Request):
    """Calculations page"""
    try:
        return templates.TemplateResponse(
            "calculations.html",
            {"request": request},
        )
    except Exception as e:
        logging.error(f"Error rendering calculations: {e}")
        return HTMLResponse(f"<h1>Calculations</h1><p>Error: {e}</p>")

# Global config page
@app.get("/config", response_class=HTMLResponse)
async def global_config_page(request: Request):
    """Global configuration page"""
    try:
        return templates.TemplateResponse(
            "global_config.html",
            {"request": request, "active_page": "config"},
        )
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
