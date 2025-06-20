import pytest
from core.engine import _run_range_optimization_search
from core.config import get_hardcoded_financial_parameters

INTEREST_RATE_TABLE, _ = get_hardcoded_financial_parameters()

customer = {
    "current_car_price": 100000,
    "vehicle_equity": 30000,
    "current_monthly_payment": 5000,
    "risk_profile_name": "A",
    "risk_profile_index": 2,
}

inventory = __import__('pandas').DataFrame([
    {"car_id": 1, "model": "Car", "sales_price": 150000}
])

def test_invalid_step_raises():
    config = {"service_fee_step": 0, "cxa_step": 0.01, "cac_bonus_step": 100}
    with pytest.raises(ValueError):
        _run_range_optimization_search(customer, inventory, INTEREST_RATE_TABLE["A"], config, 5000, {})

def test_reversed_range_raises():
    config = {
        "service_fee_step": 0.01,
        "cxa_step": 0.01,
        "cac_bonus_step": 100,
        "service_fee_range": [5, 0],
    }
    with pytest.raises(ValueError):
        _run_range_optimization_search(customer, inventory, INTEREST_RATE_TABLE["A"], config, 5000, {})
