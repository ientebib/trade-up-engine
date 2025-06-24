"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class OfferRequest(BaseModel):
    customer_id: str
    max_offers: int = Field(default=10, le=50)
    use_smart_engine: bool = True


class BulkOfferRequest(BaseModel):
    customer_ids: List[str]
    max_offers_per_customer: int = Field(default=5, le=20)


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, le=100)
    filters: Optional[Dict] = None