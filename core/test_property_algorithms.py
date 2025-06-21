import numpy_financial as npf
from hypothesis import given, strategies as st
import pytest
from core.engine import _calculate_manual_payment
from core.config import IVA_RATE

@given(
    loan=st.floats(min_value=1000, max_value=500000, allow_nan=False, allow_infinity=False),
    rate=st.floats(min_value=0.05, max_value=0.4, allow_nan=False, allow_infinity=False),
    term=st.integers(min_value=12, max_value=72),
    service_fee=st.floats(min_value=0, max_value=20000, allow_nan=False, allow_infinity=False),
    kavak_total=st.floats(min_value=0, max_value=15000, allow_nan=False, allow_infinity=False),
    insurance=st.floats(min_value=0, max_value=15000, allow_nan=False, allow_infinity=False),
    gps_monthly=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
)
def test_manual_payment_matches_pmt(loan, rate, term, service_fee, kavak_total, insurance, gps_monthly):
    payment = _calculate_manual_payment(
        loan_amount=loan,
        interest_rate=rate,
        term=term,
        service_fee_amt=service_fee,
        kavak_total_amt=kavak_total,
        insurance_amt=insurance,
        gps_monthly_fee=gps_monthly,
    )

    monthly_rate = (rate * IVA_RATE) / 12
    expected = (
        abs(npf.pmt(monthly_rate, term, -(loan + service_fee + kavak_total)))
        + abs(npf.pmt(monthly_rate, 12, -insurance))
        + gps_monthly
    )
    assert payment == pytest.approx(expected, rel=1e-4)
