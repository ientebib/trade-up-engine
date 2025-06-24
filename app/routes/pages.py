"""
Web page routes - HTML responses
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])

# Templates are initialized in main app
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Modern dashboard page"""
    from app.utils.helpers import get_data_context
    from app.core.data import customers_df, inventory_df
    
    context = {
        "request": request,
        "active_page": "dashboard",
        "stats": {
            "total_customers": len(customers_df),
            "total_inventory": len(inventory_df),
            "avg_payment": customers_df["current_monthly_payment"].mean() if len(customers_df) > 0 else 0,
            "avg_equity": customers_df["vehicle_equity"].mean() if len(customers_df) > 0 else 0
        },
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_dashboard.html", context)


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
    from engine.basic_matcher import basic_matcher
    from app.core.data import customers_df, inventory_df
    from app.utils.helpers import get_data_context
    
    customer = customers_df[customers_df["customer_id"] == customer_id]
    
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_dict = customer.iloc[0].to_dict()
    
    # Convert pandas Timestamp to string for template
    if 'contract_date' in customer_dict and pd.notna(customer_dict['contract_date']):
        try:
            # Handle pandas Timestamp
            if hasattr(customer_dict['contract_date'], 'strftime'):
                customer_dict['contract_date'] = customer_dict['contract_date'].strftime('%Y-%m-%d')
            else:
                customer_dict['contract_date'] = str(customer_dict['contract_date'])
        except:
            customer_dict['contract_date'] = ''
    
    # Format numeric fields
    for field in ['current_monthly_payment', 'vehicle_equity', 'current_car_price', 'outstanding_balance']:
        if field in customer_dict and pd.notna(customer_dict[field]):
            customer_dict[field] = float(customer_dict[field])
    
    # Generate offers if requested
    offers_data = None
    if generate == "true":
        offers_data = basic_matcher.find_all_viable(customer_dict, inventory_df.to_dict('records'))
    
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
    from engine.basic_matcher import basic_matcher
    from engine.calculator import generate_amortization_table
    from app.core.data import customers_df, inventory_df
    from app.utils.helpers import get_data_context
    
    # Get customer
    customer = customers_df[customers_df["customer_id"] == customer_id]
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_dict = customer.iloc[0].to_dict()
    
    # Get car
    inventory_mask = inventory_df["car_id"].astype(str) == str(car_id)
    if not inventory_mask.any():
        raise HTTPException(status_code=404, detail="Car not found")
    
    car = inventory_df[inventory_mask].iloc[0].to_dict()
    
    # Generate offer for this specific car
    basic_matcher_instance = basic_matcher
    offers = basic_matcher_instance.find_all_viable(customer_dict, [car])
    
    # Find the specific offer
    offer = None
    for tier_offers in offers['offers'].values():
        for o in tier_offers:
            if str(o['car_id']) == str(car_id):
                offer = o
                break
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Generate amortization schedule
    schedule = generate_amortization_table(offer)
    
    # Calculate totals for display
    total_payments = sum(row['payment'] for row in schedule)
    total_interest = sum(row['interest'] for row in schedule)
    
    context = {
        "request": request,
        "customer": customer_dict,
        "offer": offer,
        "schedule": schedule,
        "term": offer['term'],
        "total_payments": total_payments,
        "total_interest": total_interest,
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
    from engine.basic_matcher import basic_matcher
    from app.core.data import customers_df, inventory_df
    from app.utils.helpers import get_data_context
    
    customer = customers_df[customers_df["customer_id"] == customer_id]
    
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_dict = customer.iloc[0].to_dict()
    
    # Generate offers
    offers_data = basic_matcher.find_all_viable(customer_dict, inventory_df.to_dict('records'))
    
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
    from app.utils.helpers import get_data_context
    
    context = {
        "request": request,
        "active_page": "inventory",
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_inventory.html", context)


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    from app.utils.helpers import get_data_context
    from config.config import DEFAULT_FEES, PAYMENT_DELTA_TIERS, TERM_SEARCH_ORDER
    import os
    import json
    
    # Load any saved config overrides
    config_path = "engine_config.json"
    saved_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load saved config: {e}")
    
    # Merge with defaults for display
    current_config = {
        "service_fee_pct": saved_config.get('service_fee_pct', DEFAULT_FEES['service_fee_pct']),
        "cxa_pct": saved_config.get('cxa_pct', DEFAULT_FEES['cxa_pct']),
        "cac_min": saved_config.get('cac_min', DEFAULT_FEES['cac_bonus_range'][0]),
        "cac_max": saved_config.get('cac_max', DEFAULT_FEES['cac_bonus_range'][1]),
        "cac_bonus": saved_config.get('cac_bonus', 0),
        "kavak_total_enabled": saved_config.get('kavak_total_enabled', True),
        "kavak_total_amount": saved_config.get('kavak_total_amount', DEFAULT_FEES['kavak_total_amount']),
        "gps_monthly": saved_config.get('gps_monthly', DEFAULT_FEES['gps_monthly']),
        "gps_installation": saved_config.get('gps_installation', DEFAULT_FEES['gps_installation']),
        "insurance_annual": saved_config.get('insurance_annual', DEFAULT_FEES['insurance_annual']),
        "payment_delta_tiers": saved_config.get('payment_delta_tiers', PAYMENT_DELTA_TIERS),
        "available_terms": saved_config.get('available_terms', TERM_SEARCH_ORDER)
    }
    
    context = {
        "request": request,
        "active_page": "config",
        "config": current_config,
        **get_data_context()
    }
    
    return templates.TemplateResponse("modern_config.html", context)


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
    from app.core.data import customers_df
    
    # If customer_id provided, pre-fill form
    customer_data = None
    if customer_id:
        customer = customers_df[customers_df["customer_id"] == customer_id]
        if not customer.empty:
            customer_data = customer.iloc[0].to_dict()
    
    context = {
        "request": request,
        "active_page": "simulate",
        "customer_data": customer_data,
        **get_data_context()
    }
    
    return templates.TemplateResponse("manual_simulation.html", context)


# REMOVED: calculator route - api/calculator.py was deleted
# @app.get("/calculator/{customer_id}/{car_id}", response_class=HTMLResponse)
# async def offer_calculator_page(request: Request, customer_id: str, car_id: str):
#     """Detailed offer calculator for specific car"""
#     # from api.calculator import offer_calculator  # REMOVED - api/calculator.py deleted
#     # return await offer_calculator(request, customer_id, car_id, data_loader)