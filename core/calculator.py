import numpy_financial as npf
from .config import IVA_RATE


def calculate_final_npv(
    loan_amount: float,
    interest_rate: float,
    term_months: int,
    service_fee_amount: float = 0.0,
    insurance_amount: float = 0.0,
    kavak_total_amount: float = 0.0,
):
    """Return the NPV of all interest income from financed components.

    This expands the old behaviour which only considered the main loan
    amount.  Service fee, insurance and Kavak Total amounts are now also
    financed and therefore contribute interest that should be included in
    the NPV calculation.
    """

    total_financed = (
        loan_amount + service_fee_amount + insurance_amount + kavak_total_amount
    )
    if total_financed <= 0:
        return 0.0

    monthly_rate_i = interest_rate / 12
    monthly_rate_p = (interest_rate * IVA_RATE) / 12

    interest_payments = []
    months_since_insurance_reset = 1
    for month in range(1, term_months + 1):
        interest_main = (
            npf.ipmt(monthly_rate_i, month, term_months, -loan_amount) * IVA_RATE
        )
        interest_sf = (
            npf.ipmt(monthly_rate_i, month, term_months, -service_fee_amount)
            * IVA_RATE
        )
        interest_kt = (
            npf.ipmt(monthly_rate_i, month, term_months, -kavak_total_amount)
            * IVA_RATE
        )

        if insurance_amount > 0:
            month_in_cycle = months_since_insurance_reset
            interest_ins = (
                npf.ipmt(monthly_rate_i, month_in_cycle, 12, -insurance_amount)
                * IVA_RATE
            )
            months_since_insurance_reset += 1
            if months_since_insurance_reset > 12:
                months_since_insurance_reset = 1
        else:
            interest_ins = 0.0

        interest_payments.append(
            interest_main + interest_sf + interest_kt + interest_ins
        )

    npv = npf.npv(monthly_rate_p, [0] + interest_payments)
    return npv


def generate_amortization_table(offer_details: dict) -> list[dict]:
    """Generate month-by-month amortization table for a single offer."""
    loan_amount = offer_details.get("loan_amount", 0.0)
    term = int(offer_details.get("term", 0))
    rate = offer_details.get("interest_rate", 0.0)

    service_fee = offer_details.get("service_fee_amount", 0.0)
    kavak_total = offer_details.get("kavak_total_amount", 0.0)
    insurance_amt = offer_details.get("insurance_amount", 0.0)
    gps_monthly_fee = offer_details.get("gps_monthly_fee", 350.0 * IVA_RATE)

    # Apply the same "Kavak Method" as in the payment calculation
    monthly_rate_i = rate / 12
    monthly_rate_p = (rate * IVA_RATE) / 12

    financed_main = loan_amount
    financed_sf = service_fee
    financed_kt = kavak_total

    balance_main = financed_main
    balance_sf = financed_sf
    balance_kt = financed_kt
    balance_ins = insurance_amt  # first cycle
    months_since_insurance_reset = 1

    table: list[dict] = []

    for month in range(1, term + 1):
        # Reset insurance financing every 12 months
        if months_since_insurance_reset > 12 and insurance_amt > 0:
            balance_ins = insurance_amt
            months_since_insurance_reset = 1

        # --- Beginning balances ---
        beginning_balance_main = balance_main
        beginning_balance_sf = balance_sf
        beginning_balance_kt = balance_kt
        beginning_balance_ins = balance_ins if insurance_amt > 0 else 0.0

        # --- Main loan bucket ---
        principal_main = abs(npf.ppmt(monthly_rate_p, month, term, -financed_main))
        interest_main = abs(npf.ipmt(monthly_rate_i, month, term, -financed_main)) * IVA_RATE

        # --- Service Fee bucket ---
        principal_sf = abs(npf.ppmt(monthly_rate_p, month, term, -financed_sf))
        interest_sf = abs(npf.ipmt(monthly_rate_i, month, term, -financed_sf)) * IVA_RATE

        # --- Kavak Total bucket ---
        principal_kt = abs(npf.ppmt(monthly_rate_p, month, term, -financed_kt))
        interest_kt = abs(npf.ipmt(monthly_rate_i, month, term, -financed_kt)) * IVA_RATE

        # --- Insurance bucket (recurring every 12 months) ---
        if insurance_amt > 0:
            month_in_cycle = months_since_insurance_reset
            principal_ins = abs(npf.ppmt(monthly_rate_p, month_in_cycle, 12, -insurance_amt))
            interest_ins = abs(npf.ipmt(monthly_rate_i, month_in_cycle, 12, -insurance_amt)) * IVA_RATE
        else:
            principal_ins = interest_ins = 0.0

        # --- Aggregate payment ---
        payment = (
            principal_main + interest_main +
            principal_sf + interest_sf +
            principal_kt + interest_kt +
            principal_ins + interest_ins +
            gps_monthly_fee
        )

        # --- Update balances ---
        balance_main -= principal_main
        balance_sf -= principal_sf
        balance_kt -= principal_kt
        if insurance_amt > 0:
            balance_ins -= principal_ins
            months_since_insurance_reset += 1

        ending_balance_main = max(balance_main, 0)
        ending_balance_sf = max(balance_sf, 0)
        ending_balance_kt = max(balance_kt, 0)
        ending_balance_ins = max(balance_ins, 0) if insurance_amt > 0 else 0.0

        # --- Append detailed row ---
        table.append(
            {
                "month": month,
                # Balances
                "begin_balance_main": beginning_balance_main,
                "begin_balance_service_fee": beginning_balance_sf,
                "begin_balance_kavak_total": beginning_balance_kt,
                "begin_balance_insurance": beginning_balance_ins,
                # Components (principal + interest)
                "principal_main": principal_main,
                "interest_main": interest_main,
                "principal_service_fee": principal_sf,
                "interest_service_fee": interest_sf,
                "principal_kavak_total": principal_kt,
                "interest_kavak_total": interest_kt,
                "principal_insurance": principal_ins,
                "interest_insurance": interest_ins,
                "gps_fee": gps_monthly_fee,
                "payment_total": payment,
                # --- Legacy aggregate fields for UI backward-compatibility ---
                "beginning_balance": beginning_balance_main + beginning_balance_sf + beginning_balance_kt + beginning_balance_ins,
                "payment": payment,
                "principal": principal_main + principal_sf + principal_kt + principal_ins,
                "interest": interest_main + interest_sf + interest_kt + interest_ins,
                "ending_balance": ending_balance_main + ending_balance_sf + ending_balance_kt + ending_balance_ins,
                # Ending balances
                "end_balance_main": ending_balance_main,
                "end_balance_service_fee": ending_balance_sf,
                "end_balance_kavak_total": ending_balance_kt,
                "end_balance_insurance": ending_balance_ins,
                "end_balance_total": ending_balance_main + ending_balance_sf + ending_balance_kt + ending_balance_ins,
            }
        )

    return table
