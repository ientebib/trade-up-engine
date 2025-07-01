"""
Configuration schema using Pydantic for type safety and validation.
This defines all configuration fields with their types, defaults, and validation rules.
"""
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class FinancialConfig(BaseSettings):
    """Financial calculation parameters"""
    iva_rate: Decimal = Field(default=Decimal("0.16"), ge=0, le=1, description="IVA tax rate")
    max_loan_amount: Decimal = Field(default=Decimal("10000000"), gt=0, description="Maximum loan amount")
    min_loan_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Minimum loan amount")
    max_interest_rate: Decimal = Field(default=Decimal("1.0"), gt=0, le=2, description="Maximum annual interest rate")
    min_interest_rate: Decimal = Field(default=Decimal("0.0"), ge=0, description="Minimum annual interest rate")
    max_term_months: int = Field(default=120, gt=0, le=360, description="Maximum loan term in months")
    min_term_months: int = Field(default=1, gt=0, description="Minimum loan term in months")

    class Config:
        env_prefix = "FINANCIAL_"


class GPSFeesConfig(BaseSettings):
    """GPS device fee configuration"""
    monthly: Decimal = Field(default=Decimal("350.0"), ge=0, description="Monthly GPS fee (before IVA)")
    installation: Decimal = Field(default=Decimal("750.0"), ge=0, description="GPS installation fee (before IVA)")
    apply_iva: bool = Field(default=True, description="Whether to apply IVA to GPS fees")

    class Config:
        env_prefix = "GPS_"


class InsuranceConfig(BaseSettings):
    """Insurance configuration"""
    amount: Decimal = Field(default=Decimal("10999.0"), ge=0, description="Default annual insurance amount")
    term_months: int = Field(default=12, gt=0, description="Insurance term in months")
    # Risk-based insurance amounts
    amount_a: Decimal = Field(default=Decimal("10999.0"), ge=0, description="Insurance amount for risk profile A")
    amount_b: Decimal = Field(default=Decimal("13799.0"), ge=0, description="Insurance amount for risk profile B")
    amount_c: Decimal = Field(default=Decimal("15599.0"), ge=0, description="Insurance amount for risk profile C")
    amount_default: Decimal = Field(default=Decimal("10999.0"), ge=0, description="Default insurance amount for other profiles")

    class Config:
        env_prefix = "INSURANCE_"


class ServiceFeesConfig(BaseSettings):
    """Service and commission fees"""
    service_percentage: Decimal = Field(default=Decimal("0.04"), ge=0, le=1, description="Service fee percentage")
    cxa_percentage: Decimal = Field(default=Decimal("0.0399"), ge=0, le=1, description="CXA fee percentage")
    
    class Config:
        env_prefix = "FEES_"


class KavakTotalConfig(BaseSettings):
    """Kavak Total program configuration"""
    amount: Decimal = Field(default=Decimal("17599.0"), ge=0, description="Kavak Total amount")
    cycle_months: int = Field(default=24, gt=0, description="Kavak Total cycle in months")

    class Config:
        env_prefix = "KAVAK_TOTAL_"


class CACBonusConfig(BaseSettings):
    """Customer acquisition cost bonus configuration"""
    min: Decimal = Field(default=Decimal("0"), ge=0, description="Minimum CAC bonus")
    max: Decimal = Field(default=Decimal("5000.0"), ge=0, description="Maximum CAC bonus")
    default: Decimal = Field(default=Decimal("0"), ge=0, description="Default CAC bonus")

    @field_validator('default')
    def default_within_range(cls, v, info):
        values = info.data
        if 'min' in values and v < values['min']:
            raise ValueError('default must be >= min')
        if 'max' in values and v > values['max']:
            raise ValueError('default must be <= max')
        return v

    class Config:
        env_prefix = "CAC_BONUS_"


class PaymentTierConfig(BaseSettings):
    """Payment change tier configuration"""
    refresh_min: Decimal = Field(default=Decimal("-0.05"), ge=-1, le=0, description="Refresh tier minimum")
    refresh_max: Decimal = Field(default=Decimal("0.05"), ge=0, le=1, description="Refresh tier maximum")
    upgrade_min: Decimal = Field(default=Decimal("0.05"), ge=0, le=1, description="Upgrade tier minimum")
    upgrade_max: Decimal = Field(default=Decimal("0.25"), ge=0, le=1, description="Upgrade tier maximum")
    max_upgrade_min: Decimal = Field(default=Decimal("0.25"), ge=0, le=1, description="Max upgrade tier minimum")
    max_upgrade_max: Decimal = Field(default=Decimal("1.0"), ge=0, le=2, description="Max upgrade tier maximum")

    @field_validator('refresh_max')
    def refresh_range_valid(cls, v, info):
        values = info.data
        if 'refresh_min' in values and v <= values['refresh_min']:
            raise ValueError('refresh_max must be > refresh_min')
        return v

    @field_validator('upgrade_max')
    def upgrade_range_valid(cls, v, info):
        values = info.data
        if 'upgrade_min' in values and v <= values['upgrade_min']:
            raise ValueError('upgrade_max must be > upgrade_min')
        return v

    @field_validator('max_upgrade_max')
    def max_upgrade_range_valid(cls, v, info):
        values = info.data
        if 'max_upgrade_min' in values and v <= values['max_upgrade_min']:
            raise ValueError('max_upgrade_max must be > max_upgrade_min')
        return v

    class Config:
        env_prefix = "TIERS_"


class TermConfig(BaseSettings):
    """Loan term configuration"""
    search_order: List[int] = Field(default=[60, 72, 48, 36, 24, 12], description="Term search order")
    priority: str = Field(default="default", pattern="^(default|ascending|descending)$", description="Term priority")

    class Config:
        env_prefix = "TERMS_"


class SystemConfig(BaseSettings):
    """System-level configuration"""
    max_concurrent_requests: int = Field(default=3, gt=0, le=100, description="Max concurrent bulk requests")
    request_timeout_seconds: int = Field(default=300, gt=0, description="Request timeout in seconds")
    cache_ttl_hours: float = Field(default=4.0, gt=0, description="Cache TTL in hours")
    max_customers_per_bulk: int = Field(default=50, gt=0, le=1000, description="Max customers per bulk request")

    class Config:
        env_prefix = "SYSTEM_"


class FeatureFlags(BaseSettings):
    """Feature toggles"""
    enable_caching: bool = Field(default=True, description="Enable caching")
    enable_audit_logging: bool = Field(default=False, description="Enable audit logging")
    enable_decimal_precision: bool = Field(default=True, description="Use Decimal for financial calculations")
    enable_payment_validation: bool = Field(default=True, description="Enable payment validation")

    class Config:
        env_prefix = "FEATURE_"


class CoreSettings(BaseSettings):
    """
    Root configuration schema containing all subsections.
    This is the main configuration class that aggregates all settings.
    """
    financial: FinancialConfig = Field(default_factory=FinancialConfig)
    gps_fees: GPSFeesConfig = Field(default_factory=GPSFeesConfig)
    insurance: InsuranceConfig = Field(default_factory=InsuranceConfig)
    service_fees: ServiceFeesConfig = Field(default_factory=ServiceFeesConfig)
    kavak_total: KavakTotalConfig = Field(default_factory=KavakTotalConfig)
    cac_bonus: CACBonusConfig = Field(default_factory=CACBonusConfig)
    payment_tiers: PaymentTierConfig = Field(default_factory=PaymentTierConfig)
    terms: TermConfig = Field(default_factory=TermConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    # Risk profile interest rates (loaded dynamically)
    rates: dict[str, Decimal] = Field(default_factory=lambda: {
        "AAA": Decimal("0.1949"), "AA": Decimal("0.1949"), "A": Decimal("0.1949"),
        "A1": Decimal("0.1949"), "A2": Decimal("0.2099"), "B": Decimal("0.2249"),
        "C1": Decimal("0.2299"), "C2": Decimal("0.2349"), "C3": Decimal("0.2549"),
        "D1": Decimal("0.2949"), "D2": Decimal("0.3249"), "D3": Decimal("0.3249"),
        "E1": Decimal("0.2399"), "E2": Decimal("0.31"), "E3": Decimal("0.3399"),
        "E4": Decimal("0.3649"), "E5": Decimal("0.4399"), "F1": Decimal("0.3649"),
        "F2": Decimal("0.3899"), "F3": Decimal("0.4149"), "F4": Decimal("0.4399"),
        "B_SB": Decimal("0.2349"), "C1_SB": Decimal("0.2449"), "C2_SB": Decimal("0.27"),
        "E5_SB": Decimal("0.4399"), "Z": Decimal("0.4399")
    })
    
    # Down payment matrix (profile_index.term -> percentage)
    downpayment: dict[str, Decimal] = Field(default_factory=dict)

    class Config:
        env_prefix = "KAVAK_"
        case_sensitive = False
        
    def flatten(self) -> dict[str, any]:
        """Flatten nested config to dot-notation keys for backward compatibility"""
        result = {}
        
        # Helper to recursively flatten
        def _flatten(obj, prefix=''):
            if isinstance(obj, BaseSettings):
                obj = obj.model_dump()
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, BaseSettings)):
                        _flatten(value, new_key)
                    else:
                        result[new_key] = value
            else:
                result[prefix] = obj
                
        _flatten(self.model_dump())
        return result