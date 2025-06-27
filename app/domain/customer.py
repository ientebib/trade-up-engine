"""
Customer domain model
"""
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RiskProfile(str, Enum):
    """Customer risk profiles"""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    A1 = "A1"
    A2 = "A2"
    B = "B"
    B1 = "B1"
    B2 = "B2"
    C = "C"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    X = "X"
    Y = "Y"
    Z = "Z"


@dataclass
class CurrentVehicle:
    """Customer's current vehicle information"""
    price: Decimal
    brand: str
    model: str
    year: int
    outstanding_balance: Decimal
    equity: Decimal
    
    def __post_init__(self):
        """Validate and convert types"""
        self.price = Decimal(str(self.price))
        self.outstanding_balance = Decimal(str(self.outstanding_balance))
        self.equity = Decimal(str(self.equity))
        
        if self.year < 1900 or self.year > datetime.now().year + 1:
            raise ValueError(f"Invalid vehicle year: {self.year}")


@dataclass
class Customer:
    """
    Customer domain model representing a Kavak customer
    
    This model encapsulates all customer-related data and business rules,
    replacing the dictionary-based approach with a strongly-typed object.
    """
    customer_id: str
    current_monthly_payment: Decimal
    vehicle_equity: Decimal
    risk_profile: RiskProfile
    risk_profile_index: int
    current_vehicle: CurrentVehicle
    region: str
    
    # Optional fields
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Computed fields
    _eligibility_cache: Optional[Dict[str, Any]] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Validate and convert types after initialization"""
        # Ensure decimals
        self.current_monthly_payment = Decimal(str(self.current_monthly_payment))
        self.vehicle_equity = Decimal(str(self.vehicle_equity))
        
        # Validate risk profile
        if isinstance(self.risk_profile, str):
            self.risk_profile = RiskProfile(self.risk_profile)
        
        # Validate risk index
        if not 1 <= self.risk_profile_index <= 10:
            raise ValueError(f"Risk profile index must be between 1 and 10, got {self.risk_profile_index}")
        
        # Validate customer ID
        if not self.customer_id or len(self.customer_id) > 50:
            raise ValueError(f"Invalid customer ID: {self.customer_id}")
    
    @property
    def loan_to_value(self) -> Decimal:
        """Calculate current loan-to-value ratio"""
        if self.current_vehicle.price == 0:
            return Decimal('0')
        return self.current_vehicle.outstanding_balance / self.current_vehicle.price
    
    @property
    def is_eligible_for_tradeup(self) -> bool:
        """Check basic eligibility for trade-up offers"""
        return (
            self.vehicle_equity > 0 and
            self.current_monthly_payment > 0 and
            self.loan_to_value < Decimal('0.9')  # Less than 90% LTV
        )
    
    @property
    def payment_capacity_estimate(self) -> Decimal:
        """Estimate maximum payment capacity (rough estimate)"""
        # Assume they could afford up to 25% more than current payment
        return self.current_monthly_payment * Decimal('1.25')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return {
            "customer_id": self.customer_id,
            "current_monthly_payment": float(self.current_monthly_payment),
            "vehicle_equity": float(self.vehicle_equity),
            "current_car_price": float(self.current_vehicle.price),
            "outstanding_balance": float(self.current_vehicle.outstanding_balance),
            "risk_profile_name": self.risk_profile.value,
            "risk_profile_index": self.risk_profile_index,
            "region": self.region,
            "current_brand": self.current_vehicle.brand,
            "current_model": self.current_vehicle.model,
            "current_year": self.current_vehicle.year,
            "name": self.name,
            "email": self.email,
            "phone": self.phone
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        """Create Customer from dictionary (for migration)"""
        # Extract vehicle data
        current_vehicle = CurrentVehicle(
            price=data.get("current_car_price", 0),
            brand=data.get("current_brand", "Unknown"),
            model=data.get("current_model", "Unknown"),
            year=data.get("current_year", datetime.now().year),
            outstanding_balance=data.get("outstanding_balance", 0),
            equity=data.get("vehicle_equity", 0)
        )
        
        return cls(
            customer_id=data["customer_id"],
            current_monthly_payment=data["current_monthly_payment"],
            vehicle_equity=data["vehicle_equity"],
            risk_profile=data.get("risk_profile_name", "A"),
            risk_profile_index=data.get("risk_profile_index", 3),
            current_vehicle=current_vehicle,
            region=data.get("region", "Unknown"),
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            created_at=data.get("created_at")
        )
    
    def calculate_risk_score(self) -> int:
        """Calculate a risk score from 0-100 (lower is better)"""
        base_score = self.risk_profile_index * 10
        
        # Adjust based on equity
        if self.vehicle_equity < 0:
            base_score += 20
        elif self.vehicle_equity > self.current_vehicle.price * Decimal('0.3'):
            base_score -= 10
        
        # Adjust based on LTV
        if self.loan_to_value > Decimal('0.8'):
            base_score += 10
        elif self.loan_to_value < Decimal('0.5'):
            base_score -= 5
        
        return max(0, min(100, base_score))