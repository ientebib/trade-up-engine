"""
Scenario Management Center - Deal scenario tracking and comparison
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.scenario_service import scenario_service
from app.services.customer_service import customer_service
from app.core.template_utils import static_url
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize templates with absolute path
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)
templates.env.globals["static_url"] = static_url


@router.get("/scenarios", response_class=HTMLResponse)
async def scenario_center(request: Request):
    """
    Scenario Management Center - Overview of all saved deal scenarios
    """
    try:
        # Get all scenarios
        all_scenarios = scenario_service.get_all_scenarios()
        
        # Get scenario statistics
        stats = scenario_service.get_scenario_statistics()
        
        # Get recent activity
        recent_activity = scenario_service.get_recent_activity(limit=10)
        
        return templates.TemplateResponse(
            "scenario_center.html",
            {
                "request": request,
                "scenarios": all_scenarios,
                "stats": stats,
                "recent_activity": recent_activity,
                "active_page": "scenarios"
            }
        )
    except Exception as e:
        logger.error(f"Error loading scenario center: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/customer/{customer_id}", response_class=HTMLResponse)
async def customer_scenarios(request: Request, customer_id: str):
    """
    View all scenarios for a specific customer
    """
    try:
        # Get customer details
        customer = customer_service.get_customer_details(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get customer's scenarios
        scenarios = scenario_service.get_customer_scenarios(customer_id)
        
        return templates.TemplateResponse(
            "customer_scenarios.html",
            {
                "request": request,
                "customer": customer,
                "scenarios": scenarios
            }
        )
    except Exception as e:
        logger.error(f"Error loading customer scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/compare", response_class=HTMLResponse)
async def compare_scenarios(request: Request, ids: str):
    """
    Compare multiple scenarios side by side
    
    Args:
        ids: Comma-separated list of scenario IDs
    """
    try:
        scenario_ids = ids.split(',')
        
        # Get scenarios for comparison
        scenarios = []
        for scenario_id in scenario_ids:
            scenario = scenario_service.get_scenario(scenario_id)
            if scenario:
                # Get customer info for each scenario
                customer = customer_service.get_customer_details(scenario['customer_id'])
                scenario['customer'] = customer
                scenarios.append(scenario)
        
        if not scenarios:
            raise HTTPException(status_code=404, detail="No scenarios found")
        
        # Calculate comparison metrics
        comparison_data = scenario_service.generate_comparison_data(scenarios)
        
        return templates.TemplateResponse(
            "scenario_comparison.html",
            {
                "request": request,
                "scenarios": scenarios,
                "comparison": comparison_data
            }
        )
    except Exception as e:
        logger.error(f"Error comparing scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))