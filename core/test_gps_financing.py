import pytest
from core.engine import _generate_single_offer
from core.config import (
    DEFAULT_FEES,
    PAYMENT_DELTA_TIERS,
    IVA_RATE,
    GPS_INSTALLATION_FEE,
    get_hardcoded_financial_parameters,
)

INTEREST_RATE_TABLE, _ = get_hardcoded_financial_parameters()


def test_gps_installation_not_financed():
    customer = {
        "current_car_price": 130000,
        "vehicle_equity": 50000,
        "current_monthly_payment": 9000,
        "risk_profile_name": "A",
        "risk_profile_index": 2,
    }
    car = {"car_id": "CAR1", "model": "Test", "sales_price": 200000}
    fees = DEFAULT_FEES.copy()
    term = 36
    interest_rate = INTEREST_RATE_TABLE["A"]

    offer = _generate_single_offer(
        customer, car, term, interest_rate, fees, PAYMENT_DELTA_TIERS
    )
    assert offer is not None

    gps_install_with_iva = GPS_INSTALLATION_FEE * IVA_RATE
    expected_loan = (
        car["sales_price"] - customer["vehicle_equity"] - fees["cac_bonus"]
    ) / (1 - fees["cxa_pct"])
    assert offer["loan_amount"] == pytest.approx(expected_loan)
    assert offer["loan_amount"] + offer["effective_equity"] == pytest.approx(
        car["sales_price"] - gps_install_with_iva
    )
