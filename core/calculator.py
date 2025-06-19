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


def generate_amortization_table(offer_details: dict) -> list[dict]:
    """Generate month-by-month amortization table for a single offer."""
    loan_amount = offer_details.get("loan_amount", 0.0)
    term = int(offer_details.get("term", 0))
    rate = offer_details.get("interest_rate", 0.0)

    service_fee = offer_details.get("service_fee_amount", 0.0)
    kavak_total = offer_details.get("kavak_total_amount", 0.0)
    insurance_amt = offer_details.get("insurance_amount", 0.0)
    gps_fee = offer_details.get("fees_applied", {}).get("fixed_fee", 0.0) * IVA_RATE

    monthly_rate_i = rate / 12
    monthly_rate_p = (rate * IVA_RATE) / 12

    financed_main = loan_amount + service_fee + kavak_total

    balance_main = financed_main
    balance_ins = insurance_amt

    table = []
    for month in range(1, term + 1):
        beginning_balance = balance_main + (balance_ins if month <= 12 else 0)

        principal_main = abs(npf.ppmt(monthly_rate_p, month, term, -financed_main))
        interest_main = (
            abs(npf.ipmt(monthly_rate_i, month, term, -financed_main)) * IVA_RATE
        )

        if month <= 12 and insurance_amt > 0:
            principal_ins = abs(npf.ppmt(monthly_rate_p, month, 12, -insurance_amt))
            interest_ins = (
                abs(npf.ipmt(monthly_rate_i, month, 12, -insurance_amt)) * IVA_RATE
            )
        else:
            principal_ins = 0.0
            interest_ins = 0.0

        payment = (
            principal_main + interest_main + principal_ins + interest_ins + gps_fee
        )

        balance_main -= principal_main
        if month <= 12:
            balance_ins -= principal_ins

        ending_balance = balance_main + (balance_ins if month < 12 else 0)

        table.append(
            {
                "month": month,
                "beginning_balance": beginning_balance,
                "payment": payment,
                "principal": principal_main + principal_ins,
                "interest": interest_main + interest_ins,
                "ending_balance": ending_balance,
            }
        )

    return table
