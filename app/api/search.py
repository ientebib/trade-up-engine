"""
Search-related API endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict
import time
import logging
import asyncio

from app.models import SearchRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_everything(request: SearchRequest):
    """Universal search across customers, inventory, and offers"""
    from app.core.data import customers_df, inventory_df
    
    query = request.query.lower()
    results = {
        "customers": [],
        "inventory": [],
        "query": request.query,
        "total": 0
    }
    
    # Search customers
    if len(customers_df) > 0:
        customer_matches = customers_df[
            customers_df["customer_id"].str.contains(query, case=False, na=False) |
            customers_df["contract_id"].str.contains(query, case=False, na=False)
        ].head(request.limit)
        
        results["customers"] = customer_matches.to_dict("records")
    
    # Search inventory
    if len(inventory_df) > 0:
        inventory_matches = inventory_df[
            inventory_df["model"].str.contains(query, case=False, na=False)
        ].head(request.limit)
        
        results["inventory"] = inventory_matches.to_dict("records")
    
    results["total"] = len(results["customers"]) + len(results["inventory"])
    
    return results


@router.post("/smart-search")
async def smart_search_api(request: Dict = Body(...)):
    """Smart search that finds minimum subsidy needed for viable offers"""
    from engine.smart_search import smart_search_engine
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
    
    # Extract search parameters
    search_params = {
        'target_payment_delta': request.get('target_payment_delta', 0.05),  # 5% default
        'max_subsidy': request.get('max_subsidy', 50000),  # Max subsidy to try
        'subsidy_step': request.get('subsidy_step', 1000),  # Step size for search
        'service_fee_pct': request.get('service_fee_pct', 0.04),
        'cxa_pct': request.get('cxa_pct', 0.04),
        'kavak_total_amount': request.get('kavak_total_amount', 25000),
        'term_preference': request.get('term_preference'),  # Optional: 48, 60, 72
    }
    
    # Run smart search
    loop = asyncio.get_event_loop()
    inventory_records = inventory_df.to_dict("records")
    
    result = await loop.run_in_executor(
        executor,
        smart_search_engine.find_minimum_subsidy_offers,
        customer,
        inventory_records,
        search_params
    )
    
    result['processing_time'] = round(time.time() - start_time, 2)
    
    logger.info(f"🎯 Smart search for {customer_id}: {result.get('offers_found', 0)} offers in {result['processing_time']}s")
    
    return result


@router.get("/inventory/filters")
async def get_inventory_filters():
    """Get available filter options from inventory data"""
    from app.core.data import inventory_df
    
    if inventory_df.empty:
        return {
            "makes": [],
            "years": [],
            "price_range": {"min": 0, "max": 0},
            "total_cars": 0
        }
    
    # Get unique makes
    makes = sorted(inventory_df['make'].dropna().unique().tolist())
    
    # Get year range
    years = sorted(inventory_df['year'].dropna().unique().tolist())
    
    # Get price range
    price_min = float(inventory_df['sales_price'].min())
    price_max = float(inventory_df['sales_price'].max())
    
    return {
        "makes": makes,
        "years": years,
        "price_range": {
            "min": price_min,
            "max": price_max
        },
        "total_cars": len(inventory_df)
    }