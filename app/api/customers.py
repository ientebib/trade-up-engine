"""
Customer-related API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging
from app.services.customer_service import customer_service
from app.middleware.sanitization import sanitize_search_term, sanitize_pagination
from app.utils.validation import validate_customer_search
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["customers"])


@router.get("/customers")
@handle_api_errors("search customers")
async def get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    risk: Optional[str] = None
):
    """List customers with pagination, search, and filters"""
    # Validate and sanitize all inputs
    validated = validate_customer_search(
        search=search,
        risk=risk,
        sort=sort,
        page=page,
        limit=limit
    )
    
    # All business logic delegated to service layer
    return customer_service.search_customers(
        search_term=validated.get('search'),
        risk_filter=validated.get('risk'),
        sort_by=validated.get('sort'),
        page=validated['page'],
        limit=validated['limit']
    )


@router.get("/customers/stats")
@handle_api_errors("get customer statistics")
async def get_customer_stats():
    """Get aggregate statistics about customers"""
    return customer_service.get_customer_statistics()