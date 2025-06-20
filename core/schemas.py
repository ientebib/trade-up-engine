from typing import List, Optional
from pydantic import BaseModel, Field

class PaymentDeltaTiers(BaseModel):
    refresh: List[float] = Field(default_factory=lambda: [-0.05, 0.05])
    upgrade: List[float] = Field(default_factory=lambda: [0.0501, 0.25])
    max_upgrade: List[float] = Field(default_factory=lambda: [0.2501, 1.0])

class EngineSettings(BaseModel):
    # Engine Mode
    use_custom_params: bool = False
    use_range_optimization: bool = False
    include_kavak_total: bool = True

    # Fee Structure
    service_fee_pct: float = 0.05
    cxa_pct: float = 0.04
    cac_bonus: float = 5000.0
    insurance_amount: float = 10999.0
    gps_fee: float = 350.0

    # Range Optimization
    service_fee_range: List[float] = Field(default_factory=lambda: [0.0, 5.0])
    cxa_range: List[float] = Field(default_factory=lambda: [0.0, 4.0])
    cac_bonus_range: List[float] = Field(default_factory=lambda: [0.0, 10000.0])
    service_fee_step: float = 0.01
    cxa_step: float = 0.01
    cac_bonus_step: float = 100.0
    max_offers_per_tier: int = 50

    # Payment Delta Thresholds
    payment_delta_tiers: PaymentDeltaTiers = PaymentDeltaTiers()

    # Engine Behavior
    term_priority: str = "standard"
    min_npv_threshold: float = 5000.0
    last_updated: Optional[str] = None
