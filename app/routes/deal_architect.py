"""
Deal Architect - Advanced deal crafting workspace
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.customer_service import customer_service
from app.services.scenario_service import scenario_service
from app.exceptions import CustomerNotFoundError, DatabaseError
from app.core.template_utils import static_url
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize templates with absolute path
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)
templates.env.globals["static_url"] = static_url


@router.get("/deal-architect/{customer_id}", response_class=HTMLResponse)
async def deal_architect_workspace(request: Request, customer_id: str):
    """
    Deal Architect workspace - Bloomberg Terminal for deal crafting
    """
    try:
        # Get customer data
        customer = customer_service.get_customer_details(customer_id)
        if not customer:
            raise CustomerNotFoundError(
                f"Customer {customer_id} not found",
                details={"customer_id": customer_id}
            )
        
        # Get saved scenarios for this customer
        scenarios = scenario_service.get_customer_scenarios(customer_id)
        
        return templates.TemplateResponse(
            "deal_architect.html",
            {
                "request": request,
                "customer": customer,
                "saved_scenarios": scenarios
            }
        )
    except CustomerNotFoundError as e:
        logger.warning(f"Customer not found: {e.message}")
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseError as e:
        logger.error(f"Database error in deal architect: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, 
            detail="Database temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in deal architect: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please contact support if this persists."
        ) from e


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
    except DatabaseError as e:
        logger.error(f"Database error in Deal Architect home: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )
    except ValueError as e:
        logger.error(f"Invalid data in Deal Architect home: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid data format. Please refresh the page."
        )
    except Exception as e:
        logger.error(f"Unexpected error in Deal Architect home: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please contact support if this persists."
        ) from e