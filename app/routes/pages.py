"""
Web page routes - HTML responses
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import pandas as pd
import logging
import os

from app.core.template_utils import get_template_context, static_url

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])

# Templates with absolute path
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)

# Add static_url to template globals
templates.env.globals["static_url"] = static_url


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Modern dashboard page"""
    try:
        from app.utils.helpers import get_data_context
        from app.services.customer_service import customer_service
        
        # Get dashboard stats from service layer
        stats = customer_service.get_dashboard_stats()
        
        context = {
            "request": request,
            "active_page": "dashboard",
            "stats": {
                "total_customers": stats["total_customers"],
                "total_inventory": stats["total_inventory"],
                "avg_payment": stats["avg_payment"],
                "avg_equity": stats["avg_equity"]
            },
            "metrics": {
                "total_customers": stats["total_customers"],
                "total_inventory": stats["total_inventory"],
                "avg_price": stats["avg_price"],
                "brands": stats["brands"],
                "conversion_rate": stats["conversion_rate"],
                "avg_npv": stats["avg_npv"]
            },
            **get_data_context()
        }
        
        return templates.TemplateResponse("modern_dashboard.html", context)
    except Exception as e:
        import traceback
        logger.error(f"Error in dashboard page: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


@router.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    """Customer search and management page"""
    from app.utils.helpers import get_data_context
    
    context = {
        "request": request,
        "active_page": "customers",
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_customers.html", context)


@router.get("/customer/{customer_id}", response_class=HTMLResponse)
async def customer_detail(request: Request, customer_id: str, generate: Optional[str] = None):
    """Individual customer view with instant offer generation"""
    from app.utils.helpers import get_data_context
    from app.services.offer_service import offer_service
    
    try:
        # Get customer data and optionally generate offers - all business logic in service
        data = offer_service.prepare_customer_detail_data(
            customer_id=customer_id,
            generate_offers=(generate == "true")
        )
        
        customer_dict = data["customer"]
        offers_data = data.get("offers_data")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Error loading customer data")
    
    context = {
        "request": request, 
        "customer": customer_dict,
        "active_page": "customers",
        "offers_data": offers_data,
        "show_offers": generate == "true",
        **get_data_context()
    }
    
    # Use enhanced template (fixed by other AI)
    return templates.TemplateResponse(
        "modern_customer_detail_enhanced.html",
        context
    )


@router.get("/customer/{customer_id}/offer/{car_id}/amortization", response_class=HTMLResponse)
async def offer_amortization(request: Request, customer_id: str, car_id: str):
    """Show detailed amortization table for a specific offer"""
    from app.utils.helpers import get_data_context
    from app.services.offer_service import offer_service
    
    try:
        # Get amortization data - all business logic in service
        amortization_data = offer_service.generate_amortization_for_offer(customer_id, car_id)
        
        # Get customer for display
        customer_dict = offer_service.get_customer_details(customer_id)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating amortization for {customer_id}/{car_id}: {e}")
        raise HTTPException(status_code=500, detail="Error generating amortization")
    
    context = {
        "request": request,
        "customer": customer_dict,
        "offer": amortization_data["offer"],
        "schedule": amortization_data["schedule"],
        "term": amortization_data["term"],
        "total_payments": amortization_data["total_payments"],
        "total_interest": amortization_data["total_interest"],
        "active_page": "customers",
        **get_data_context()
    }
    
    return templates.TemplateResponse(
        "amortization_table.html",
        context
    )


@router.get("/customer/{customer_id}/offers-test", response_class=HTMLResponse)
async def customer_offers_test(request: Request, customer_id: str):
    """Test page showing server-side rendered offers for a customer"""
    from app.utils.helpers import get_data_context
    from app.services.offer_service import offer_service
    
    try:
        # Get customer and generate offers - all business logic in service
        customer_dict = offer_service.get_customer_details(customer_id)
        if not customer_dict:
            raise ValueError("Customer not found")
            
        offers_data = offer_service.generate_offers_for_customer(customer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in offers test for {customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Error generating offers")
    
    context = {
        "request": request,
        "customer": customer_dict,
        "offers_data": offers_data,
        "active_page": "customers",
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_offers_full.html", context)


@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    """Inventory management page"""
    try:
        from app.utils.helpers import get_data_context
        from data import database
        
        # Get inventory data
        inventory = database.get_all_inventory()
        
        context = {
            "request": request,
            "active_page": "inventory",
            "inventory": inventory,
            **get_data_context()
        }
        
        return templates.TemplateResponse("modern_inventory.html", context)
    except Exception as e:
        logger.error(f"Error in inventory page: {e}")
        raise


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    from app.utils.helpers import get_data_context
    from app.services.config_service import config_service
    
    try:
        # Get configuration formatted for template
        current_config = config_service.get_config_for_template()
        
        context = {
            "request": request,
            "active_page": "config",
            "config": current_config,
            **get_data_context()
        }
        
        return templates.TemplateResponse("modern_config.html", context)
    except Exception as e:
        logger.error(f"Error in config page: {e}")
        raise HTTPException(status_code=500, detail="Error loading configuration")


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """Health monitoring page"""
    from app.utils.helpers import get_data_context
    
    context = {
        "request": request,
        "active_page": "health",
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_health.html", context)


@router.get("/manual-simulation", response_class=HTMLResponse)
async def manual_simulation_page(request: Request, customer_id: Optional[str] = None):
    """Manual simulation page with optional customer pre-fill"""
    from app.utils.helpers import get_data_context
    from data import database
    
    # If customer_id provided, pre-fill form
    customer_data = None
    if customer_id:
        customer_data = database.get_customer_by_id(customer_id)
    
    context = {
        "request": request,
        "active_page": "simulate",
        "customer_data": customer_data,
        **get_data_context()
    }
    
    return templates.TemplateResponse("manual_simulation.html", context)