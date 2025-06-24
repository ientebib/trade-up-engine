"""
Customer-related API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["customers"])


@router.get("/customers")
async def get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    risk: Optional[str] = None
):
    """List customers with pagination, search, and filters"""
    from app.core.data import customers_df
    
    # Copy DataFrame to avoid modifying original
    filtered_df = customers_df.copy()
    
    # Apply search filter
    if search:
        mask = (
            filtered_df["customer_id"].str.contains(search, case=False, na=False) |
            filtered_df["contract_id"].str.contains(search, case=False, na=False) |
            filtered_df["email"].str.contains(search, case=False, na=False) |
            filtered_df["current_car_model"].str.contains(search, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if risk:
        if risk == "low":
            filtered_df = filtered_df[filtered_df["risk_profile_index"] <= 5]
        elif risk == "medium":
            filtered_df = filtered_df[(filtered_df["risk_profile_index"] > 5) & 
                                    (filtered_df["risk_profile_index"] <= 15)]
        elif risk == "high":
            filtered_df = filtered_df[filtered_df["risk_profile_index"] > 15]
    
    # Sort
    if sort == "payment-high":
        filtered_df = filtered_df.sort_values("current_monthly_payment", ascending=False)
    elif sort == "payment-low":
        filtered_df = filtered_df.sort_values("current_monthly_payment")
    elif sort == "equity-high":
        filtered_df = filtered_df.sort_values("vehicle_equity", ascending=False)
    
    # Paginate
    start = (page - 1) * limit
    end = start + limit
    total = len(filtered_df)
    customers = filtered_df.iloc[start:end].to_dict("records")
    
    return {
        "customers": customers,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }