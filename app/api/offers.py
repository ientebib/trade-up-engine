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
from app.utils.cache import offer_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["offers"])


@router.post("/generate-offers-basic")
async def generate_offers_basic(request: OfferRequest):
    """Generate ALL viable offers with standard fees - no fancy shit"""
    from engine.basic_matcher import basic_matcher
    from app.core.data import customers_df, inventory_df, executor
    
    start_time = time.time()
    
    # Check cache first
    cache_key = offer_cache.get_key(request.customer_id)
    cached_result = offer_cache.get(cache_key)
    if cached_result:
        logger.info(f"🚀 Cache hit for {request.customer_id}")
        cached_result['from_cache'] = True
        return cached_result
    
    # Get customer data
    customer_mask = customers_df["customer_id"] == request.customer_id
    if not customer_mask.any():
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = customers_df[customer_mask].iloc[0].to_dict()
    
    # Use basic matcher with parallel processing
    loop = asyncio.get_event_loop()
    inventory_records = inventory_df.to_dict("records")
    
    result = await loop.run_in_executor(
        executor,
        basic_matcher.find_all_viable,
        customer,
        inventory_records
    )
    
    # Cache the result
    offer_cache.set(cache_key, result)
    
    logger.info(f"📊 Basic matcher: {result['total_offers']} offers for {request.customer_id} in {result['processing_time']}s")
    
    return result


@router.post("/generate-offers-bulk")
async def generate_offers_bulk(request: BulkOfferRequest):
    """Generate offers for multiple customers in parallel"""
    from app.core.data import customers_df
    
    start_time = time.time()
    
    # Validate all customers exist
    valid_customers = []
    for cid in request.customer_ids[:50]:  # Max 50 at once
        if cid in customers_df["customer_id"].values:
            valid_customers.append(cid)
    
    if not valid_customers:
        raise HTTPException(status_code=400, detail="No valid customers found")
    
    # Process in parallel
    tasks = []
    for customer_id in valid_customers:
        req = OfferRequest(
            customer_id=customer_id,
            max_offers=request.max_offers_per_customer
        )
        tasks.append(generate_offers_basic(req))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Format results
    successful = []
    failed = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed.append({
                "customer_id": valid_customers[i],
                "error": str(result)
            })
        else:
            successful.append({
                "customer_id": valid_customers[i],
                "offers_count": sum(len(offers) for offers in result["offers"].values()),
                "best_npv": max(
                    (offer.get("npv", 0) for tier_offers in result["offers"].values() 
                     for offer in tier_offers),
                    default=0
                )
            })
    
    return {
        "processed": len(valid_customers),
        "successful": len(successful),
        "failed": len(failed),
        "results": successful,
        "errors": failed,
        "processing_time": round(time.time() - start_time, 2)
    }


@router.post("/generate-offers-custom")
async def generate_offers_custom(request: Dict):
    """Generate offers with custom configuration per customer"""
    from engine.basic_matcher import BasicMatcher
    from app.core.data import customers_df, inventory_df, executor
    
    start_time = time.time()
    
    # Get customer
    customer_id = request.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id required")
    
    customer_mask = customers_df["customer_id"] == customer_id
    if not customer_mask.any():
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = customers_df[customer_mask].iloc[0].to_dict()
    
    # Extract custom configuration
    kavak_total_enabled = request.get('kavak_total_enabled', True)
    kavak_total_amount = 25000 if kavak_total_enabled else 0
    
    custom_config = {
        'service_fee_pct': request.get('service_fee_pct', 0.04),
        'cxa_pct': request.get('cxa_pct', 0.04),
        'cac_bonus': request.get('cac_bonus', 0),
        'kavak_total_amount': kavak_total_amount,
        'gps_monthly_fee': request.get('gps_monthly_fee', 350),
        'gps_installation_fee': request.get('gps_installation_fee', 750),
        'insurance_amount': request.get('insurance_amount', 10999),
        'term_months': request.get('term_months')  # Optional specific term
    }
    
    # Use standard matcher with custom fees passed to find_all_viable
    from engine.basic_matcher import basic_matcher
    
    # Find offers with custom configuration
    loop = asyncio.get_event_loop()
    inventory_records = inventory_df.to_dict("records")
    
    result = await loop.run_in_executor(
        executor,
        basic_matcher.find_all_viable,
        customer,
        inventory_records,
        custom_config  # Pass custom fees as parameter
    )
    
    result['configuration'] = custom_config
    
    logger.info(f"📊 Custom matcher: {result['total_offers']} offers for {customer_id} in {round(time.time() - start_time, 2)}s")
    
    return result


@router.post("/amortization")
async def amortization_api(offer: Dict = Body(...)):
    """Return amortization schedule for a given offer.

    The *offer* param is exactly one of the objects returned by the matcher,
    containing at minimum:
      loan_amount, term, interest_rate, service_fee_amount, kavak_total_amount,
      insurance_amount, gps_monthly_fee.
    """
    from engine.calculator import generate_amortization_table
    schedule = generate_amortization_table(offer)

    # Fix field names to match frontend expectations
    for row in schedule:
        # Frontend expects 'balance' field
        row['balance'] = row.get('ending_balance', 0)

    return {
        "schedule": schedule,
        "table": schedule,  # Frontend expects 'table' field
        "payment_total": schedule[0]["payment"] if schedule else 0,
        "principal_month1": schedule[0]["principal"] if schedule else 0,
        "interest_month1": schedule[0]["interest"] if schedule else 0,
        "gps_fee": schedule[0]["cargos"] if schedule else 0,
        "cargos": schedule[0]["cargos"] if schedule else 0,
    }


@router.post("/amortization-table")
async def amortization_table_api(offer: Dict = Body(...)):
    """Alias for amortization API - frontend calls this endpoint"""
    return await amortization_api(offer)


# REMOVED: manual_simulation_api - calculate_offer_details doesn't exist
@router.post("/manual-simulation")
async def manual_simulation_api(request: Dict):
    """Calculate offers for manual simulation"""
    # TODO: Re-implement using basic_matcher
    raise HTTPException(status_code=501, detail="Manual simulation temporarily disabled - needs reimplementation")