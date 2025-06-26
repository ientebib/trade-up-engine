"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class OfferRequest(BaseModel):
    """Request model for generating offers for a single customer"""
    customer_id: str = Field(
        ...,
        description="Unique customer identifier",
        example="TMCJ33A32GJ053451"
    )
    max_offers: int = Field(
        default=10,
        le=50,
        description="Maximum number of offers to return per tier",
        example=10
    )
    use_smart_engine: bool = Field(
        default=True,
        description="Whether to use smart filtering for better offers",
        example=True
    )


class BulkOfferRequest(BaseModel):
    """Request model for generating offers for multiple customers"""
    customer_ids: List[str] = Field(
        ...,
        description="List of customer IDs to process",
        example=["CUST001", "CUST002", "CUST003"],
        max_items=100
    )
    max_offers_per_customer: int = Field(
        default=5,
        le=20,
        description="Maximum offers to generate per customer",
        example=5
    )


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, le=100)
    filters: Optional[Dict] = None