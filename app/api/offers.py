"""
Offer generation API endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List
import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from app.models import OfferRequest, BulkOfferRequest
from app.middleware.sanitization import sanitize_customer_id, InputSanitizer
from app.utils.error_handling import handle_api_errors
from app.utils.validation import UnifiedValidator as Validators, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["offers"])


@router.post("/generate-offers-basic")
@handle_api_errors("generate basic offers")
async def generate_offers_basic(request: OfferRequest):
    """
    Generate trade-up offers for a customer with standard fees.
    
    This endpoint analyzes a customer's current loan and financial situation,
    then generates all viable vehicle upgrade offers categorized by payment change.
    
    ## Request Body
    - **customer_id**: Unique customer identifier (e.g., "TMCJ33A32GJ053451")
    
    ## Response
    Returns offer data organized by payment tier:
    - **refresh**: Offers with -5% to +5% payment change
    - **upgrade**: Offers with +5% to +25% payment change  
    - **max_upgrade**: Offers with +25% to +100% payment change
    
    Each offer includes:
    - Vehicle details (make, model, year, price)
    - Financial terms (monthly payment, NPV, interest rate)
    - Payment comparison with current loan
    
    ## Example
    ```json
    {
        "customer_id": "TMCJ33A32GJ053451"
    }
    ```
    
    ## Errors
    - 404: Customer not found
    - 503: Service unavailable (database issues)
    """
    from app.services.offer_service import offer_service
    
    # Sanitize customer ID
    clean_customer_id = sanitize_customer_id(request.customer_id)
    
    # All business logic delegated to service layer
    return offer_service.generate_offers_for_customer(clean_customer_id)


@router.post("/generate-offers-bulk")
@handle_api_errors("generate bulk offers")
async def generate_offers_bulk(request: BulkOfferRequest):
    """
    Generate offers for multiple customers in parallel.
    
    Processes multiple customers concurrently for efficient bulk operations.
    Results are queued and can be retrieved via the bulk status endpoint.
    
    ## Request Body
    - **customer_ids**: List of customer IDs (max 100)
    - **max_offers_per_customer**: Optional limit on offers per customer (default: 50)
    
    ## Response
    Returns request status with:
    - **request_id**: Unique identifier for tracking
    - **status**: Processing status (queued/processing/completed)
    - **results**: Offer data for each customer (when completed)
    
    ## Limits
    - Maximum 100 customers per request
    - Maximum 3 concurrent bulk requests
    - 5-minute timeout for processing
    
    ## Example
    ```json
    {
        "customer_ids": ["CUST001", "CUST002", "CUST003"],
        "max_offers_per_customer": 20
    }
    ```
    """
    from app.services.offer_service import offer_service
    
    # Validate and sanitize bulk request
    try:
        validated_ids, max_offers = Validators.validate_bulk_request(
            request.customer_ids,
            request.max_offers_per_customer
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # All orchestration logic delegated to service layer
    return await offer_service.generate_for_multiple_customers(
        customer_ids=validated_ids,
        max_offers_per_customer=max_offers
    )


@router.post("/generate-offers-custom")
@handle_api_errors("generate custom offers")
async def generate_offers_custom(request: Dict):
    """Generate offers with custom configuration per customer"""
    from app.services.offer_service import offer_service
    
    # Sanitize and validate request data
    try:
        # Sanitize request data (may raise ValidationError)
        request = InputSanitizer.sanitize_dict(request)
        
        # Validate offer request
        validated_request = Validators.validate_offer_request(request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Process custom configuration
    custom_config = offer_service.process_custom_config(validated_request)
    
    # Generate offers with custom config - all business logic in service
    result = offer_service.generate_offers_for_customer(validated_request['customer_id'], custom_config)
    
    # Add configuration to response
    result['configuration'] = custom_config
    
    return result


@router.post("/amortization")
@handle_api_errors("generate amortization")
async def amortization_api(offer: Dict = Body(...)):
    """Return amortization schedule for a given offer.

    The *offer* param is exactly one of the objects returned by the matcher,
    containing at minimum:
      loan_amount, term, interest_rate, service_fee_amount, kavak_total_amount,
      insurance_amount, gps_monthly_fee.
    """
    from app.services.offer_service import offer_service
    
    # All formatting logic delegated to service layer
    return offer_service.format_amortization_for_frontend(offer)


@router.post("/amortization-table")
async def amortization_table_api(offer: Dict = Body(...)):
    """Alias for amortization API - frontend calls this endpoint"""
    return await amortization_api(offer)


@router.post("/calculate-payment")
@handle_api_errors("calculate real-time payment")
async def calculate_real_time_payment(request: Dict = Body(...)):
    """
    Calculate monthly payment in real-time for a specific car and configuration.
    
    This endpoint provides instant feedback for the Deal Architect interface,
    allowing users to see payment changes as they adjust fees and terms.
    
    ## Request Body
    - **customer_id**: Customer identifier
    - **car_id**: Vehicle identifier
    - **term**: Loan term in months
    - **service_fee_pct**: Service fee percentage (0.0-0.05)
    - **cxa_pct**: CXA fee percentage (0.0-0.04)
    - **cac_bonus**: CAC bonus amount
    - **kavak_total_enabled**: Whether to include Kavak Total
    - **insurance_amount**: Insurance amount
    - **interest_rate**: Optional interest rate override
    
    ## Response
    Returns payment calculation with breakdown:
    - **monthly_payment**: Total monthly payment
    - **payment_without_fees**: Base payment without optional fees
    - **payment_delta**: Percentage change from current payment
    - **payment_breakdown**: Detailed breakdown of payment components
    - **loan_details**: Loan structure details
    """
    from app.services.offer_service import offer_service
    
    # Extract parameters
    customer_id = request.get('customer_id')
    car_id = request.get('car_id')
    term = request.get('term', 48)
    
    # Validate inputs
    if not customer_id or not car_id:
        raise HTTPException(status_code=400, detail="customer_id and car_id are required")
    
    # Get specific offer with given parameters
    custom_config = offer_service.process_custom_config(request)
    custom_config['term_months'] = term
    
    # Get customer and car
    customer = offer_service.get_customer_details(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get car from database
    from data import database
    car = database.get_car_by_id(car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    
    # Calculate offer
    from engine.basic_matcher import basic_matcher
    offers = basic_matcher.find_all_viable(customer, [car], custom_config)
    
    # Find the specific offer
    offer = None
    for tier_offers in offers['offers'].values():
        for o in tier_offers:
            if str(o['car_id']) == str(car_id) and o['term'] == term:
                offer = o
                break
        if offer:
            break
    
    if not offer:
        # No viable offer with these parameters
        return {
            "viable": False,
            "reason": "No viable offer with these parameters",
            "monthly_payment": 0,
            "payment_delta": 0
        }
    
    # Calculate payment without optional fees for comparison
    base_config = custom_config.copy()
    base_config['service_fee_pct'] = 0
    base_config['cxa_pct'] = 0
    base_config['kavak_total_amount'] = 0
    
    base_offers = basic_matcher.find_all_viable(customer, [car], base_config)
    base_offer = None
    for tier_offers in base_offers['offers'].values():
        for o in tier_offers:
            if str(o['car_id']) == str(car_id) and o['term'] == term:
                base_offer = o
                break
    
    payment_without_fees = base_offer['monthly_payment'] if base_offer else offer['monthly_payment'] * 0.85
    
    return {
        "viable": True,
        "monthly_payment": offer['monthly_payment'],
        "payment_without_fees": payment_without_fees,
        "payment_delta": offer['payment_delta'],
        "fees_impact": offer['monthly_payment'] - payment_without_fees,
        "payment_breakdown": {
            "principal_and_interest": offer.get('principal_payment', 0),
            "service_fee": offer.get('service_fee_amount', 0),
            "kavak_total": offer.get('kavak_total_amount', 0),
            "insurance": offer.get('insurance_amount', 0),
            "gps_monthly": offer.get('gps_monthly_fee', 0),
            "iva_on_interest": offer.get('iva_on_interest', 0)
        },
        "loan_details": {
            "car_price": offer['new_car_price'],
            "effective_equity": offer['effective_equity'],
            "loan_amount": offer['loan_amount'],
            "interest_rate": offer['interest_rate'],
            "term": offer['term'],
            "npv": offer['npv']
        }
    }


@router.get("/offers/bulk-status/{request_id}")
@handle_api_errors("get bulk status")
async def get_bulk_status(request_id: str):
    """Get status of a bulk offer generation request"""
    from app.services.offer_service import offer_service
    
    # Sanitize request ID (UUIDs)
    clean_request_id = sanitize_customer_id(request_id)
    
    status = offer_service.get_bulk_request_status(clean_request_id)
    if not status:
        raise ValueError("Request not found")
    
    return status


@router.post("/search-inventory")
@handle_api_errors("search inventory for customer")
async def search_inventory_for_customer(request: Dict = Body(...)):
    """
    Search inventory based on customer preferences and filters.
    
    This endpoint enables the Smart Search feature, filtering inventory
    based on customer preferences, payment targets, and other criteria.
    
    ## Request Body
    - **customer_id**: Customer identifier
    - **filters**: Search filters
      - **payment_delta_min**: Min payment change (-0.1 = -10%)
      - **payment_delta_max**: Max payment change (0.2 = +20%)
      - **brands**: List of preferred brands
      - **min_year**: Minimum vehicle year
      - **max_km**: Maximum kilometers
      - **vehicle_types**: List of vehicle types (SUV, Sedan, etc.)
      - **min_price**: Minimum vehicle price
      - **max_price**: Maximum vehicle price
    - **sort_by**: Sort criteria (npv, payment, price, year, km)
    - **sort_order**: Sort order (asc, desc)
    - **limit**: Max results (default 50)
    - **quick_calc**: Whether to calculate quick payments (default true)
    
    ## Response
    Returns filtered inventory with quick calculations:
    - **total_matches**: Number of matching vehicles
    - **vehicles**: List of vehicles with estimated payments
    - **categories**: Vehicles grouped by payment delta
    """
    customer_id = request.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")
    
    from app.services.search_service import search_service
    
    # Get filters
    filters = request.get('filters', {})
    
    # Search inventory
    results = await search_service.search_inventory_for_customer(
        customer_id=customer_id,
        payment_delta_range=(
            filters.get('payment_delta_min', -0.1),
            filters.get('payment_delta_max', 0.25)
        ),
        brands=filters.get('brands'),
        min_year=filters.get('min_year'),
        max_km=filters.get('max_km'),
        vehicle_types=filters.get('vehicle_types'),
        min_price=filters.get('min_price'),
        max_price=filters.get('max_price'),
        sort_by=request.get('sort_by', 'payment_delta'),
        sort_order=request.get('sort_order', 'asc'),
        limit=request.get('limit', 50),
        quick_calc=request.get('quick_calc', True)
    )
    
    return results


@router.post("/search-inventory-live")
@handle_api_errors("live inventory search")
async def search_inventory_live(request: Dict = Body(...)):
    """
    Live inventory search with real-time NPV calculations.
    
    This endpoint provides real-time search results with full NPV calculations
    for the Deal Architect interface.
    
    ## Request Body
    - **customer_id**: Customer identifier
    - **search_term**: Text search (brand, model, etc.)
    - **config**: Current configuration from Deal Architect
    - **limit**: Max results (default 20)
    
    ## Response
    Returns vehicles with full financial calculations
    """
    customer_id = request.get('customer_id')
    search_term = request.get('search_term', '')
    config = request.get('config', {})
    limit = request.get('limit', 20)
    
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")
    
    from app.services.search_service import search_service
    
    # Perform live search with configuration
    results = await search_service.live_inventory_search(
        customer_id=customer_id,
        search_term=search_term,
        configuration=config,
        limit=limit
    )
    
    return results


@router.post("/scenarios/save")
@handle_api_errors("save deal scenario")
async def save_deal_scenario(request: Dict = Body(...)):
    """
    Save a deal scenario configuration for later retrieval.
    
    This endpoint allows users to save specific deal configurations
    for comparison and future reference.
    
    ## Request Body
    - **customer_id**: Customer identifier
    - **car_id**: Car identifier
    - **name**: Scenario name (e.g., "Conservative Offer", "Maximum Discount")
    - **configuration**: Deal configuration
    - **notes**: Optional notes about the scenario
    
    ## Response
    Returns saved scenario with ID
    """
    from app.services.scenario_service import scenario_service
    from app.models import SaveScenarioRequest
    
    # Validate request
    scenario_request = SaveScenarioRequest(**request)
    
    # Save scenario
    saved = scenario_service.save_scenario(
        customer_id=scenario_request.customer_id,
        car_id=scenario_request.car_id,
        name=scenario_request.name,
        configuration=scenario_request.configuration,
        notes=scenario_request.notes
    )
    
    return saved


@router.get("/scenarios/customer/{customer_id}")
@handle_api_errors("get customer scenarios")
async def get_customer_scenarios(customer_id: str):
    """
    Get all saved scenarios for a customer.
    
    Returns list of scenarios sorted by creation date (newest first).
    """
    from app.services.scenario_service import scenario_service
    
    scenarios = scenario_service.get_customer_scenarios(customer_id)
    
    return {
        "customer_id": customer_id,
        "scenarios": scenarios,
        "total": len(scenarios)
    }


@router.get("/scenarios/{scenario_id}")
@handle_api_errors("get scenario")
async def get_scenario(scenario_id: str):
    """Get a specific scenario by ID"""
    from app.services.scenario_service import scenario_service
    
    scenario = scenario_service.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario


@router.delete("/scenarios/{scenario_id}")
@handle_api_errors("delete scenario")
async def delete_scenario(scenario_id: str):
    """Delete a scenario"""
    from app.services.scenario_service import scenario_service
    
    deleted = scenario_service.delete_scenario(scenario_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {"message": "Scenario deleted", "id": scenario_id}


@router.post("/scenarios/compare")
@handle_api_errors("compare scenarios")
async def compare_scenarios(request: Dict = Body(...)):
    """
    Compare multiple scenarios side by side.
    
    ## Request Body
    - **scenario_ids**: List of scenario IDs to compare
    
    ## Response
    Returns comparison data with key metrics
    """
    scenario_ids = request.get('scenario_ids', [])
    if not scenario_ids:
        raise HTTPException(status_code=400, detail="scenario_ids required")
    
    from app.services.scenario_service import scenario_service
    
    comparison = scenario_service.compare_scenarios(scenario_ids)
    
    return comparison

