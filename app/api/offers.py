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
from app.services.async_offer_service import async_offer_service

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
    import os
    
    # Sanitize customer ID
    clean_customer_id = sanitize_customer_id(request.customer_id)
    
    # Check if async is disabled (temporary workaround)
    if os.getenv("DISABLE_ASYNC_OFFERS", "false").lower() == "true":
        logger.warning("⚠️ Async offers disabled, using synchronous processing")
        try:
            result = async_offer_service.process_offer_generation_sync(clean_customer_id, None)
            return result
        except Exception as e:
            logger.error(f"❌ Synchronous offer generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Get custom config if provided
    custom_config = getattr(request, 'custom_config', None)
    
    # Use async processing
    task_id = async_offer_service.submit_offer_generation(clean_customer_id, custom_config)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Offer generation started",
        "poll_url": f"/api/offers/status/{task_id}"
    }


@router.get("/offers/status/{task_id}")
@handle_api_errors("check offer generation status")
async def check_offer_status(task_id: str):
    """
    Check the status of an async offer generation task.
    
    ## Path Parameters
    - **task_id**: The task ID returned from generate-offers-basic
    
    ## Response
    Returns task status including:
    - **status**: pending/processing/completed/failed
    - **progress**: Progress percentage (0-100)
    - **summary**: Summary of results when completed
    """
    status = async_offer_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@router.get("/offers/health")
@handle_api_errors("check async service health")
async def check_async_health():
    """
    Check health of the async offer service.
    
    ## Response
    Returns service health status including:
    - **status**: Service status
    - **total_tasks**: Total tasks in memory
    - **active_tasks**: Currently running tasks
    - **completed_tasks**: Successfully completed tasks
    - **failed_tasks**: Failed tasks
    """
    return async_offer_service.get_health_status()


@router.get("/offers/result/{task_id}")
@handle_api_errors("get offer generation result")
async def get_offer_result(task_id: str):
    """
    Get the full result of a completed offer generation task.
    
    ## Path Parameters
    - **task_id**: The task ID returned from generate-offers-basic
    
    ## Response
    Returns the full offer data if task is completed
    """
    result = async_offer_service.get_task_result(task_id)
    if not result:
        # Check if task exists
        status = async_offer_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        elif status["status"] != "completed":
            raise HTTPException(status_code=425, detail=f"Task is {status['status']}")
    
    return result


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
    
    # Basic validation
    customer_id = request.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")
    
    # Process custom configuration
    custom_config = offer_service.process_custom_config(request)
    
    # Use async processing
    task_id = async_offer_service.submit_offer_generation(customer_id, custom_config)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Offer generation started with custom configuration",
        "poll_url": f"/api/offers/status/{task_id}",
        "configuration": custom_config
    }


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


@router.post("/manual-simulation")
@handle_api_errors("manual simulation")
async def manual_simulation(request: Dict = Body(...)):
    """
    Calculate payment details for manual loan simulation.
    
    This endpoint allows users to simulate loan payments without requiring
    a specific customer or vehicle from the database.
    """
    # Use YOUR existing math modules and offer generation logic
    from engine.basic_matcher_sync import basic_matcher_sync as matcher
    from config.facade import get
    
    try:
        # Extract parameters from frontend format
        current_payment = float(request.get('current_monthly_payment', 0))
        vehicle_equity = float(request.get('vehicle_equity', 0))
        car_price = float(request.get('car_price', 0))
        car_model = request.get('car_model', 'Manual Simulation')
        risk_profile = request.get('risk_profile', 'A')
        
        # Get fees from request (convert percentages)
        service_fee_pct = float(request.get('service_fee_pct', get('service_fees.service_percentage', 0.04)))
        cxa_pct = float(request.get('cxa_pct', get('service_fees.cxa_percentage', 0.0399)))
        cac_bonus = float(request.get('cac_bonus', 0))
        kavak_total_amount = float(request.get('kavak_total_amount', get('kavak_total.amount', 17599)))
        insurance_amount = float(request.get('insurance_amount', get('insurance.amount', 10999)))
        gps_installation_fee = float(request.get('gps_installation_fee', get('gps_fees.installation', 750)))
        gps_monthly_fee = float(request.get('gps_monthly_fee', get('gps_fees.monthly', 350)))
        
        # Match risk profile string to the numeric index required by the down payment table
        # This mapping should ideally live in a central data loader/service
        RISK_PROFILE_TO_INDEX = {
            'AAA': 0, 'AA': 1, 'A': 2, 'A1': 3, 'A2': 4, 'B': 5, 'C1': 6, 
            'C2': 7, 'C3': 8, 'D1': 9, 'D2': 10, 'D3': 11, 'E1': 12, 'E2': 13, 
            'E3': 14, 'E4': 15, 'E5': 16, 'F1': 17, 'F2': 18, 'F3': 19, 'F4': 20, 
            'B_SB': 21, 'C1_SB': 22, 'C2_SB': 23, 'E5_SB': 24, 'Z': 25
        }
        risk_profile_index = RISK_PROFILE_TO_INDEX.get(risk_profile, 2) # Default to 'A'
        
        # Create a fake customer dict that matches what your matcher expects
        fake_customer = {
            'customer_id': 'MANUAL_SIM',
            'current_monthly_payment': current_payment,
            'vehicle_equity': vehicle_equity,
            'current_car_price': float(request.get('current_car_price', 0)),
            'risk_profile': risk_profile,
            'risk_profile_name': risk_profile,
            'risk_profile_index': risk_profile_index
        }
        
        # Create a fake car dict
        fake_car = {
            'car_id': 'MANUAL_CAR',
            'car_price': car_price,
            'model': car_model,
            'year': 2024,
            'sales_price': car_price  # Your system uses sales_price
        }
        
        # Pass the exact values from the request to YOUR matcher
        # Don't use any hardcoded logic - let YOUR engine handle everything
        custom_config = {
            'service_fee_pct': service_fee_pct,
            'cxa_pct': cxa_pct,
            'cac_bonus': cac_bonus,
            'kavak_total': kavak_total_amount,
            'insurance_amount': insurance_amount,
            'gps_installation_fee': gps_installation_fee,
            'gps_monthly_fee': gps_monthly_fee,
            'skip_delta_filter': True  # Allow high payment deltas for simulation
        }
        
        # Calculate for all standard terms using YOUR matcher logic
        terms = [24, 36, 48, 60, 72]
        calculations = {}
        
        for term in terms:
            # Use YOUR existing matcher to generate offers
            result = matcher.find_all_viable(
                customer=fake_customer,
                inventory=[fake_car],
                custom_config=custom_config,
                terms_to_evaluate=[term]
            )
            
            # Extract the offer for this term
            offer = None
            for tier_offers in result.get('offers', {}).values():
                if tier_offers:
                    offer = tier_offers[0]  # First (only) offer
                    break
            
            if offer:
                # Use YOUR existing amortization logic
                from engine.calculator import generate_amortization_table
                
                # Debug logging
                logger.info(f"Offer GPS monthly fee: {offer.get('gps_monthly_fee', 'MISSING')}")
                
                # Create offer_details dict that YOUR function expects
                offer_details = {
                    'loan_amount': offer['loan_amount'],
                    'term': term,
                    'interest_rate': offer['interest_rate'],
                    'service_fee_amount': offer['service_fee_amount'],
                    'kavak_total_amount': kavak_total_amount,
                    'insurance_amount': insurance_amount,
                    'gps_install_fee': 0,  # Already included in loan
                    'gps_monthly_fee': offer.get('gps_monthly_fee', 0)  # Pass the GPS monthly fee
                }
                
                amortization = generate_amortization_table(offer_details)
                
                # Get ALL waterfall data from YOUR offer - no recalculation!
                # YOUR engine already calculated everything correctly
                pre_fee_base_loan = car_price - vehicle_equity
                
                # Use the values YOUR engine calculated
                cxa_amount = offer['cxa_amount']
                gps_install_with_iva = offer['gps_install_with_iva']
                effective_equity = offer['effective_equity']
                
                # The base loan YOUR engine used
                base_loan = car_price - effective_equity
                
                # Get payment breakdown using YOUR calculation
                from engine.payment_utils import calculate_payment_components
                
                # YOUR engine already included GPS install in the loan amount
                # So we need to extract the actual loan base for the payment calculation
                loan_base_for_payment = offer['loan_amount'] - offer['service_fee_amount'] - kavak_total_amount - insurance_amount
                
                # Get the detailed payment components for period 1
                components = calculate_payment_components(
                    loan_base=loan_base_for_payment,
                    service_fee_amount=offer['service_fee_amount'],
                    kavak_total_amount=kavak_total_amount,
                    insurance_amount=insurance_amount,
                    annual_rate_nominal=offer['interest_rate'],
                    term_months=term,
                    period=1,  # First month
                    insurance_term=12  # Insurance is always 12 months
                )
                
                # Base payment: principal + interest for **main loan only** (exclude service fee & KT)
                base_payment = components['principal_main'] + components['interest_main']
                
                # Monthly portions for additional financed fees
                service_fee_monthly = components['principal_sf'] + components['interest_sf']
                kavak_total_monthly = components['principal_kt'] + components['interest_kt']
                
                # GPS monthly with IVA from YOUR offer
                gps_monthly = offer.get('gps_monthly_fee', gps_monthly_fee)  # Use offer value or fallback to request
                iva_rate = float(get('financial.iva_rate', 0.16))
                apply_iva = get('gps_fees.apply_iva', True)
                gps_monthly_with_iva = gps_monthly * (1 + iva_rate) if apply_iva else gps_monthly
                
                # Insurance monthly (principal + interest)
                insurance_monthly = components['principal_ins'] + components['interest_ins']
                
                # Calculate total interest and total paid using YOUR offer's NPV
                # The NPV is the total interest income
                total_interest = offer.get('npv', 0)
                total_paid = offer['monthly_payment'] * term
                
                calculations[term] = {
                    'term': term,
                    'total_monthly': offer['monthly_payment'],
                    'loan_amount': offer['loan_amount'],
                    'effective_equity': offer['effective_equity'],
                    'interest_rate': offer['interest_rate'],
                    'service_fee': offer['service_fee_amount'],
                    'service_fee_amount': offer['service_fee_amount'],  # Frontend expects this name
                    'cxa_fee': offer['cxa_amount'],
                    'payment_delta': offer['payment_delta'],
                    # Payment breakdown for frontend
                    'base_payment': base_payment,
                    'gps_monthly': gps_monthly_with_iva,
                    'insurance_monthly': insurance_monthly,
                    'service_fee_monthly': service_fee_monthly,
                    'kavak_total_monthly': kavak_total_monthly,
                    # Monthly payment excluding GPS (already separated)
                    'monthly_with_fees': offer['monthly_payment'] - gps_monthly_with_iva,
                    # Waterfall data for loan construction display
                    'car_price': car_price,
                    'vehicle_equity': vehicle_equity,
                    'pre_fee_base_loan': pre_fee_base_loan,
                    'cxa_amount': cxa_amount,
                    'gps_install_with_iva': gps_install_with_iva,
                    'cac_bonus': cac_bonus,
                    'effective_equity_down': effective_equity,  # What's available as down payment
                    'base_loan': base_loan,
                    'kavak_total_amount': kavak_total_amount,
                    'insurance_amount': insurance_amount,
                    'total_financed': offer['loan_amount'],
                    'npv': offer.get('npv', 0),
                    # Summary data
                    'total_interest': total_interest,
                    'total_paid': total_paid,
                    'amortization_preview': amortization[:12] if amortization else []  # First year
                }
            else:
                # No viable offer for this term
                calculations[term] = {
                    'term': term,
                    'total_monthly': 0,
                    'loan_amount': 0,
                    'effective_equity': -1,  # Signal non-viable
                    'interest_rate': 0,
                    'service_fee': 0,
                    'service_fee_amount': 0,
                    'cxa_fee': 0,
                    'payment_delta': 0,
                    # Payment breakdown for frontend
                    'base_payment': 0,
                    'gps_monthly': 0,
                    'insurance_monthly': 0,
                    'service_fee_monthly': 0,
                    'kavak_total_monthly': 0,
                    # Monthly payment excluding GPS (already separated)
                    'monthly_with_fees': 0,
                    # Waterfall data for loan construction display
                    'car_price': car_price,
                    'vehicle_equity': vehicle_equity,
                    'pre_fee_base_loan': car_price - vehicle_equity,
                    'cxa_amount': 0,
                    'gps_install_with_iva': 0,
                    'cac_bonus': cac_bonus,
                    'effective_equity_down': -1,
                    'base_loan': 0,
                    'kavak_total_amount': kavak_total_amount,
                    'insurance_amount': insurance_amount,
                    'total_financed': 0,
                    'npv': 0,
                    # Summary data
                    'total_interest': 0,
                    'total_paid': 0,
                    'amortization_preview': []
                }
        
        # Pass all the request data back for display
        return {
            'success': True,
            'car_model': car_model,
            'car_price': car_price,
            'current_payment': current_payment,
            'vehicle_equity': vehicle_equity,
            'current_car_price': float(request.get('current_car_price', 0)),
            'service_fee_pct': service_fee_pct,
            'cxa_pct': cxa_pct,
            'cac_bonus': cac_bonus,
            'risk_profile': risk_profile,
            'calculations': calculations
        }
        
    except Exception as e:
        logger.error(f"Manual simulation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Simulation error: {str(e)}")


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
    from engine.basic_matcher_sync import basic_matcher_sync as basic_matcher
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

