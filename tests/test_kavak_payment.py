import numpy_financial as npf
import pytest
from core.engine import _calculate_manual_payment
from core.config import IVA_RATE

def test_kavak_payment_equals_pmt():
    loan = 100000
    rate = 0.2
    term = 60
    payment = _calculate_manual_payment(
        loan_amount=loan,
        interest_rate=rate,
        term=term,
        service_fee_amt=0.0,
        kavak_total_amt=0.0,
        insurance_amt=0.0,
        gps_monthly_fee=0.0,
    )
    expected = abs(npf.pmt((rate * IVA_RATE) / 12, term, -loan))
    assert payment == pytest.approx(expected)
