"""
Offer domain model
"""
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .customer import Customer
from .vehicle import Vehicle


class OfferTier(str, Enum):
    """Offer categorization by payment change"""
    REFRESH = "Refresh"        # -5% to +5% payment change
    UPGRADE = "Upgrade"        # +5% to +25% payment change
    MAX_UPGRADE = "Max Upgrade"  # +25% to +100% payment change
    OUT_OF_RANGE = "Out of Range"  # Outside acceptable ranges


class OfferStatus(str, Enum):
    """Offer lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class LoanTerms:
    """Loan terms and financial details"""
    term_months: int
    interest_rate: Decimal
    interest_rate_with_iva: Decimal
    monthly_rate: Decimal
    loan_amount: Decimal
    down_payment: Decimal
    
    # Fee breakdown
    service_fee_amount: Decimal
    cxa_amount: Decimal
    cac_bonus: Decimal
    kavak_total_amount: Decimal
    insurance_amount: Decimal
    
    # GPS fees
    gps_installation_fee: Decimal
    gps_monthly_fee: Decimal
    gps_monthly_fee_iva: Decimal
    
    # Calculated values
    total_financed: Decimal
    effective_equity: Decimal
    iva_on_interest: Decimal
    
    def __post_init__(self):
        """Ensure all monetary values are Decimals"""
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if field_name != 'term_months' and not isinstance(value, Decimal):
                setattr(self, field_name, Decimal(str(value)))


@dataclass
class PaymentDetails:
    """Payment calculation details"""
    monthly_payment: Decimal
    current_payment: Decimal
    payment_delta: Decimal
    payment_delta_percentage: Decimal
    
    # Payment components
    principal_payment: Decimal
    interest_payment: Decimal
    iva_payment: Decimal
    gps_payment: Decimal
    total_payment: Decimal
    
    def __post_init__(self):
        """Ensure all values are Decimals"""
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if not isinstance(value, Decimal):
                setattr(self, field_name, Decimal(str(value)))


@dataclass
class Offer:
    """
    Trade-up offer domain model
    
    Represents a complete offer for a customer to trade their current
    vehicle for a new one, including all financial calculations and terms.
    """
    offer_id: str
    customer: Customer
    vehicle: Vehicle
    loan_terms: LoanTerms
    payment_details: PaymentDetails
    npv: Decimal
    tier: OfferTier
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: OfferStatus = OfferStatus.DRAFT
    
    # Cached calculations
    _amortization_table: Optional[List[Dict]] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Validate offer and ensure proper types"""
        self.npv = Decimal(str(self.npv))
        
        # Determine tier if not set
        if isinstance(self.tier, str):
            self.tier = OfferTier(self.tier)
        elif self.tier is None:
            self.tier = self._calculate_tier()
        
        # Set expiration if not provided (default 7 days)
        if self.expires_at is None:
            from datetime import timedelta
            self.expires_at = self.created_at + timedelta(days=7)
    
    def _calculate_tier(self) -> OfferTier:
        """Calculate offer tier based on payment delta"""
        delta = self.payment_details.payment_delta
        
        # Load tier boundaries from config
        from config.facade import get_decimal
        
        refresh_min = get_decimal('tiers.refresh.min', -0.05)
        refresh_max = get_decimal('tiers.refresh.max', 0.05)
        upgrade_min = get_decimal('tiers.upgrade.min', 0.05)
        upgrade_max = get_decimal('tiers.upgrade.max', 0.25)
        max_upgrade_min = get_decimal('tiers.max_upgrade.min', 0.25)
        max_upgrade_max = get_decimal('tiers.max_upgrade.max', 1.0)
        
        if refresh_min <= delta <= refresh_max:
            return OfferTier.REFRESH
        elif upgrade_min < delta <= upgrade_max:
            return OfferTier.UPGRADE
        elif max_upgrade_min < delta <= max_upgrade_max:
            return OfferTier.MAX_UPGRADE
        else:
            return OfferTier.OUT_OF_RANGE
    
    @property
    def is_viable(self) -> bool:
        """Check if offer is within acceptable parameters"""
        return (
            self.tier != OfferTier.OUT_OF_RANGE and
            self.npv > 0 and
            self.payment_details.payment_delta <= Decimal('1.0')  # Max 100% increase
        )
    
    @property
    def is_active(self) -> bool:
        """Check if offer is currently active"""
        return (
            self.status == OfferStatus.ACTIVE and
            self.expires_at > datetime.now()
        )
    
    @property
    def payment_increase_amount(self) -> Decimal:
        """Calculate absolute payment increase"""
        return (
            self.payment_details.monthly_payment - 
            self.payment_details.current_payment
        )
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost over loan term"""
        return (
            self.payment_details.monthly_payment * 
            self.loan_terms.term_months
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "offer_id": self.offer_id,
            "customer_id": self.customer.customer_id,
            "car_id": self.vehicle.car_id,
            "car_model": f"{self.vehicle.brand} {self.vehicle.model}",
            "new_car_price": float(self.vehicle.effective_price),
            "term": self.loan_terms.term_months,
            "monthly_payment": float(self.payment_details.monthly_payment),
            "new_monthly_payment": float(self.payment_details.monthly_payment),
            "payment_delta": float(self.payment_details.payment_delta),
            "payment_delta_percentage": float(self.payment_details.payment_delta_percentage * 100),
            "loan_amount": float(self.loan_terms.loan_amount),
            "effective_equity": float(self.loan_terms.effective_equity),
            "cxa_amount": float(self.loan_terms.cxa_amount),
            "service_fee_amount": float(self.loan_terms.service_fee_amount),
            "cac_bonus": float(self.loan_terms.cac_bonus),
            "kavak_total_amount": float(self.loan_terms.kavak_total_amount),
            "insurance_amount": float(self.loan_terms.insurance_amount),
            "gps_install_fee": float(self.loan_terms.gps_installation_fee),
            "gps_monthly_fee": float(self.loan_terms.gps_monthly_fee),
            "gps_monthly_fee_base": float(self.loan_terms.gps_monthly_fee / Decimal('1.16')),
            "gps_monthly_fee_iva": float(self.loan_terms.gps_monthly_fee_iva),
            "iva_on_interest": float(self.loan_terms.iva_on_interest),
            "npv": float(self.npv),
            "interest_rate": float(self.loan_terms.interest_rate),
            "tier": self.tier.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_calculation_result(cls, 
                              customer: Customer,
                              vehicle: Vehicle,
                              calculation: Dict[str, Any],
                              offer_id: Optional[str] = None) -> "Offer":
        """Create Offer from engine calculation result"""
        from uuid import uuid4
        
        if offer_id is None:
            offer_id = str(uuid4())
        
        # Create loan terms
        loan_terms = LoanTerms(
            term_months=calculation["term"],
            interest_rate=Decimal(str(calculation["interest_rate"])),
            interest_rate_with_iva=Decimal(str(calculation["interest_rate"])) * Decimal('1.16'),
            monthly_rate=Decimal(str(calculation["interest_rate"])) * Decimal('1.16') / 12,
            loan_amount=Decimal(str(calculation["loan_amount"])),
            down_payment=Decimal(str(vehicle.effective_price)) - Decimal(str(calculation["loan_amount"])),
            service_fee_amount=Decimal(str(calculation["service_fee_amount"])),
            cxa_amount=Decimal(str(calculation["cxa_amount"])),
            cac_bonus=Decimal(str(calculation.get("cac_bonus", 0))),
            kavak_total_amount=Decimal(str(calculation.get("kavak_total_amount", 0))),
            insurance_amount=Decimal(str(calculation.get("insurance_amount", 0))),
            gps_installation_fee=Decimal(str(calculation["gps_install_fee"])),
            gps_monthly_fee=Decimal(str(calculation["gps_monthly_fee"])),
            gps_monthly_fee_iva=Decimal(str(calculation.get("gps_monthly_fee_iva", 0))),
            total_financed=Decimal(str(calculation["loan_amount"])),
            effective_equity=Decimal(str(calculation["effective_equity"])),
            iva_on_interest=Decimal(str(calculation.get("iva_on_interest", 0)))
        )
        
        # Create payment details
        payment_details = PaymentDetails(
            monthly_payment=Decimal(str(calculation["monthly_payment"])),
            current_payment=customer.current_monthly_payment,
            payment_delta=Decimal(str(calculation["payment_delta"])),
            payment_delta_percentage=Decimal(str(calculation["payment_delta"])),
            principal_payment=Decimal('0'),  # Would need to calculate
            interest_payment=Decimal('0'),   # Would need to calculate
            iva_payment=Decimal('0'),         # Would need to calculate
            gps_payment=loan_terms.gps_monthly_fee,
            total_payment=Decimal(str(calculation["monthly_payment"]))
        )
        
        return cls(
            offer_id=offer_id,
            customer=customer,
            vehicle=vehicle,
            loan_terms=loan_terms,
            payment_details=payment_details,
            npv=Decimal(str(calculation["npv"])),
            tier=None  # Will be calculated in __post_init__
        )