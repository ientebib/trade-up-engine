from __future__ import annotations

from typing import List
from pydantic import BaseModel

class PaymentDeltaTiers(BaseModel):
    refresh: List[float] = [-0.05, 0.05]
    upgrade: List[float] = [0.0501, 0.25]
    max_upgrade: List[float] = [0.2501, 1.0]

class EngineSettings(BaseModel):
    use_custom_params: bool = False
    use_range_optimization: bool = False
    include_kavak_total: bool = True

    service_fee_pct: float = 0.05
    cxa_pct: float = 0.04
    cac_bonus: float = 5000.0
    insurance_amount: float = 10999.0
    gps_installation_fee: float = 750.0
    gps_monthly_fee: float = 350.0

    service_fee_range: List[float] = [0.0, 5.0]
    cxa_range: List[float] = [0.0, 4.0]
    cac_bonus_range: List[float] = [0.0, 10000.0]
    service_fee_step: float = 0.1
    cxa_step: float = 0.1
    cac_bonus_step: float = 100.0
    max_offers_per_tier: int = 50

    max_combinations_to_test: int = 1000
    early_stop_on_offers: int = 100

    payment_delta_tiers: PaymentDeltaTiers = PaymentDeltaTiers()

    term_priority: str = "standard"
    min_npv_threshold: float = 5000.0
    last_updated: str | None = None
