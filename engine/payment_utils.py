from __future__ import annotations
from typing import Dict
import numpy_financial as npf
from config import IVA_RATE

def calculate_monthly_payment(
    *,
    loan_base: float,
    service_fee_amount: float,
    kavak_total_amount: float,
    insurance_amount: float,
    annual_rate_nominal: float,
    term_months: int,
    gps_install_fee: float = 0.0,
) -> Dict[str, float]:
    """
    Calculates the first month's payment using the EXACT audited logic.
    CRITICAL: This must match the amortization table calculation exactly.
    """
    gps_monthly_fee = 350.0 * (1 + IVA_RATE)
    
    # Define rates exactly as in the audited Excel sheet
    monthly_rate = annual_rate_nominal / 12.0
    rate_with_iva = annual_rate_nominal * (1 + IVA_RATE)
    monthly_rate_with_iva = rate_with_iva / 12.0

    # Principal for month 1 (using IVA-inclusive rate)
    principal_main = abs(npf.ppmt(monthly_rate_with_iva, 1, term_months, -loan_base))
    principal_sf = abs(npf.ppmt(monthly_rate_with_iva, 1, term_months, -service_fee_amount))
    principal_kt = abs(npf.ppmt(monthly_rate_with_iva, 1, term_months, -kavak_total_amount))
    principal_ins = abs(npf.ppmt(monthly_rate_with_iva, 1, 12, -insurance_amount)) if insurance_amount > 0 else 0.0
    
    total_principal = principal_main + principal_sf + principal_kt + principal_ins

    # Interest for month 1 WITH IVA (using contractual rate then applying IVA)
    interest_main = abs(npf.ipmt(monthly_rate, 1, term_months, -loan_base)) * (1 + IVA_RATE)
    interest_sf = abs(npf.ipmt(monthly_rate, 1, term_months, -service_fee_amount)) * (1 + IVA_RATE)
    interest_kt = abs(npf.ipmt(monthly_rate, 1, term_months, -kavak_total_amount)) * (1 + IVA_RATE)
    interest_ins = abs(npf.ipmt(monthly_rate, 1, 12, -insurance_amount)) * (1 + IVA_RATE) if insurance_amount > 0 else 0.0

    total_interest = interest_main + interest_sf + interest_kt + interest_ins

    # Total payment - INCLUDING GPS install fee (as per Excel)
    payment = total_principal + total_interest + gps_monthly_fee + gps_install_fee
    
    return {
        "monthly_payment": payment,
        "payment_total": payment,  # For compatibility
        "principal": total_principal,
        "interest": total_interest,
        "gps_fee": gps_monthly_fee,
        "gps_install": gps_install_fee,
        "iva_on_interest": 0.0,  # Not used in new calculation
        "total_financed": loan_base + service_fee_amount + kavak_total_amount + insurance_amount
    }