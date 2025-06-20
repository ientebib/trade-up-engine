import numpy_financial as npf
import pytest

from core.calculator import calculate_final_npv, generate_amortization_table
from core.config import IVA_RATE


def test_calculate_final_npv_matches_amortization():
    details = {
        "loan_amount": 100000.0,
        "term": 24,
        "interest_rate": 0.2,
        "service_fee_amount": 5000.0,
        "kavak_total_amount": 10000.0,
        "insurance_amount": 12000.0,
        "gps_monthly_fee": 0.0,
    }

    table = generate_amortization_table(details)
    monthly_rate_p = (details["interest_rate"] * IVA_RATE) / 12
    interest_stream = [row["interest"] for row in table]
    expected = npf.npv(monthly_rate_p, [0] + interest_stream)

    calculated = calculate_final_npv(
        details["loan_amount"],
        details["interest_rate"],
        details["term"],
        details["service_fee_amount"],
        details["insurance_amount"],
        details["kavak_total_amount"],
    )

    assert calculated == pytest.approx(expected)
