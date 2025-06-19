import numpy_financial as npf
from .config import IVA_RATE

def calculate_final_npv(loan_amount, interest_rate, term_months):
    """
    Calculates the Net Present Value of the interest income for the loan,
    discounted at the loan's own monthly rate. The result represents the
    present value of the interest cash-flows that Kavak earns over the
    life of the loan (therefore it should always be ≥ 0).
    """
    if loan_amount <= 0:
        return 0.0
    
    # Generate the cash-flow of interest income for each month.
    # `numpy_financial.ipmt` returns a POSITIVE value when the present value
    # (`pv`) is passed in as a negative number (i.e. cash outflow for the
    # borrower, cash inflow for the lender). Therefore **do not** invert the
    # sign here; we want positive cash-flows for the lender.

    tasa_mensual_sin_iva = interest_rate / 12
    interest_payments = [
        npf.ipmt(tasa_mensual_sin_iva, period, term_months, -loan_amount)
        for period in range(1, term_months + 1)
    ]
    
    # Calculate NPV using the same monthly rate as the discount rate
    npv = npf.npv(tasa_mensual_sin_iva, [0] + interest_payments)
    return npv