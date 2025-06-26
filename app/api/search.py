"""
Search-related API endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict
import time
import logging
import asyncio

from app.models import SearchRequest
from app.services.search_service import search_service
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
@handle_api_errors("universal search")
async def search_everything(request: SearchRequest):
    """Universal search across customers, inventory, and offers"""
    # All search logic delegated to service layer
    return search_service.universal_search(request.query, request.limit)


@router.post("/smart-search")
@handle_api_errors("smart search")
async def smart_search_api(request: Dict = Body(...)):
    """Smart search that finds minimum subsidy needed for viable offers"""
    import multiprocessing
    from concurrent.futures import ThreadPoolExecutor
    
    start_time = time.time()
    
    # Get customer ID
    customer_id = request.get('customer_id')
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id required")
    
    # Create executor for this request
    cpu_count = multiprocessing.cpu_count()
    executor = ThreadPoolExecutor(max_workers=cpu_count)
    
    # All smart search logic delegated to service layer
    result = await search_service.smart_search_minimum_subsidy(
        customer_id=customer_id,
        search_params=request,
        executor=executor
    )
    
    result['processing_time'] = round(time.time() - start_time, 2)
    return result


@router.get("/inventory/filters")
@handle_api_errors("get inventory filters")
async def get_inventory_filters():
    """Get available filter options from inventory data"""
    # All filter logic delegated to service layer
    return search_service.get_inventory_filters()