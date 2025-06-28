"""
Deal Architect - Advanced deal crafting workspace
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.customer_service import customer_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/deal-architect/{customer_id}", response_class=HTMLResponse)
async def deal_architect_workspace(request: Request, customer_id: str):
    """
    Deal Architect workspace - Bloomberg Terminal for deal crafting
    """
    try:
        # Get customer data
        customer = customer_service.get_customer_details(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get saved scenarios for this customer
        from app.services.scenario_service import scenario_service
        scenarios = scenario_service.get_customer_scenarios(customer_id)
        
        return templates.TemplateResponse(
            "deal_architect.html",
            {
                "request": request,
                "customer": customer,
                "saved_scenarios": scenarios
            }
        )
    except Exception as e:
        logger.error(f"Error loading deal architect: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deal-architect", response_class=HTMLResponse)
async def deal_architect_home(request: Request):
    """
    Deal Architect home - Select a customer to start
    """
    try:
        # Get only 12 recent customers for quick display
        customers_result = customer_service.search_customers(limit=12)
        customers = customers_result.get("customers", [])
        
        # Get recent scenarios
        from app.services.scenario_service import scenario_service
        recent_scenarios = scenario_service.get_recent_activity(limit=5)
        
        # Get basic statistics - use empty defaults if no scenarios exist
        stats = {
            'total_scenarios': 0,
            'unique_customers': 0,
            'avg_service_fee': 0.03  # Default display value
        }
        
        return templates.TemplateResponse(
            "deal_architect_home.html",
            {
                "request": request,
                "customers": customers,
                "recent_scenarios": recent_scenarios,
                "stats": stats,
                "active_page": "architect"
            }
        )
    except Exception as e:
        logger.error(f"Error loading Deal Architect home: {e}")
        raise HTTPException(status_code=500, detail=str(e))