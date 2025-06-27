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

