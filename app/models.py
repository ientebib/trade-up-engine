"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


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
    custom_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom configuration overrides",
        example={
            "service_fee_pct": 0.03,
            "cxa_pct": 0.03,
            "cac_bonus": 2000,
            "insurance_amount": 15000
        }
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
    """Request model for searching customers"""
    query: str = Field(
        ...,
        description="Search query string",
        example="John Doe"
    )
    limit: int = Field(
        default=20,
        le=100,
        description="Maximum number of results to return",
        example=20
    )
    filters: Optional[Dict] = Field(
        default=None,
        description="Additional filters to apply",
        example={"risk_profile": "A1", "min_equity": 50000}
    )


class DealScenario(BaseModel):
    """Deal scenario configuration for saving/loading"""
    id: Optional[str] = Field(None, description="Scenario ID")
    name: str = Field(..., description="Scenario name")
    customer_id: str = Field(..., description="Customer ID")
    car_id: str = Field(..., description="Car ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    configuration: Dict[str, Any] = Field(..., description="Deal configuration")
    notes: Optional[str] = Field(None, description="User notes")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SaveScenarioRequest(BaseModel):
    """Request to save a deal scenario"""
    customer_id: str = Field(..., description="Customer ID")
    car_id: str = Field(..., description="Car ID")
    name: str = Field(..., description="Scenario name")
    configuration: Dict[str, Any] = Field(..., description="Deal configuration")
    notes: Optional[str] = Field(None, description="Optional notes")


class CustomerPreferences(BaseModel):
    """Customer preferences for vehicle search"""
    customer_id: str = Field(..., description="Customer ID")
    preferred_brands: Optional[List[str]] = Field(None, description="Preferred car brands")
    vehicle_types: Optional[List[str]] = Field(None, description="Preferred vehicle types")
    max_payment_increase: Optional[float] = Field(None, description="Max payment increase %")
    min_year: Optional[int] = Field(None, description="Minimum vehicle year")
    max_km: Optional[float] = Field(None, description="Maximum kilometers")
    color_preferences: Optional[List[str]] = Field(None, description="Preferred colors")
    must_have_features: Optional[List[str]] = Field(None, description="Required features")
