import numpy_financial as npf
from config.config import IVA_RATE
from config.facade import ConfigProxy
from .payment_utils import calculate_payment_components, calculate_final_npv

# Use configuration facade
config = ConfigProxy()


def calculate_npv(offer: dict) -> float:
    """Legacy helper to compute NPV of interest income.

    Args:
        offer: Dictionary containing at least ``total_financed`` (or ``loan_amount``),
            ``interest_rate`` and ``term`` keys.

    Returns:
        Calculated NPV value as ``float``.
    """
    loan_amount = float(
        offer.get("total_financed")
        or offer.get("loan_amount")
        or 0.0
    )
    interest_rate = float(offer.get("interest_rate", 0.0))
    term_months = int(offer.get("term", 0))

    if loan_amount <= 0 or term_months <= 0:
        return 0.0

    return calculate_final_npv(loan_amount, interest_rate, term_months)


def generate_amortization_table(offer_details: dict) -> list[dict]:
    """. 
    Generate month-by-month amortization table using the EXACT audited logic.
    CRITICAL: This follows the exact calculation from the risk team.
    """
    # Extract offer details
    loan_amount = float(offer_details.get("loan_amount", 0.0) or offer_details.get(1, 0.0))
    term = int(offer_details.get("term", 0) or offer_details.get(2, 0))
    rate = float(offer_details.get("interest_rate", 0.0) or offer_details.get(3, 0.0))
    service_fee = float(offer_details.get("service_fee_amount", 0.0) or offer_details.get(4, 0.0))
    kavak_total = float(offer_details.get("kavak_total_amount", 0.0) or offer_details.get(5, 0.0))
    insurance_amt = float(offer_details.get("insurance_amount", 0.0) or offer_details.get(6, 0.0))
    
    # Get GPS monthly fee from offer_details if provided, otherwise from config
    if "gps_monthly_fee" in offer_details:
        gps_monthly_fee = float(offer_details.get("gps_monthly_fee", 0.0))
    else:
        gps_monthly_fee = float(config.get_decimal("gps_fees.monthly")) * (1 + IVA_RATE)
    gps_install_fee = float(offer_details.get("gps_install_fee", 0.0) or 0.0)

    # CRITICAL: Apply IVA to the rate once (as per audited logic)
    # SAFETY: Guard against zero or invalid rates
    if rate <= 0:
        rate = 0.01  # Use 1% as minimum rate to avoid division by zero
    monthly_rate = rate / 12
    rate_with_iva = rate * (1 + IVA_RATE)
    monthly_rate_with_iva = rate_with_iva / 12

    # Extract main principal portion for amortization buckets
    financed_main = loan_amount - service_fee - kavak_total - insurance_amt
    financed_sf = service_fee
    financed_kt = kavak_total

    balance_main = financed_main
    balance_sf = financed_sf
    balance_kt = financed_kt
    balance_ins = insurance_amt  # first cycle

    table = []

    for month in range(1, term + 1):
        # Beginning balances
        beginning_balance_main = balance_main
        beginning_balance_sf = balance_sf
        beginning_balance_kt = balance_kt
        # Insurance balance only for first 12 months
        beginning_balance_ins = balance_ins if insurance_amt > 0 and month <= 12 else 0.0

        # Use the SINGLE SOURCE OF TRUTH for payment calculations
        components = calculate_payment_components(
            loan_base=financed_main,
            service_fee_amount=financed_sf,
            kavak_total_amount=financed_kt,
            insurance_amount=insurance_amt,
            annual_rate_nominal=rate,
            term_months=term,
            period=month,
            insurance_term=12
        )
        
        # Extract component values
        principal_main = components["principal_main"]
        principal_sf = components["principal_sf"]
        principal_kt = components["principal_kt"]
        principal_ins = components["principal_ins"]
        interest_main = components["interest_main"]
        interest_sf = components["interest_sf"]
        interest_kt = components["interest_kt"]
        interest_ins = components["interest_ins"]

        # --- Aggregate payment ---
        # Add GPS install fee only to first month
        gps_install_this_month = gps_install_fee if month == 1 else 0.0
        
        # For Excel compatibility: GPS installation WITH IVA is part of principal in month 1
        gps_install_principal = gps_install_fee if month == 1 else 0.0  # 870 with IVA
        
        # Calculate total principal for DISPLAY (including GPS install in month 1 per Excel)
        total_principal_display = principal_main + principal_sf + principal_kt + principal_ins + gps_install_principal
        
        # Use totals from the single source of truth
        total_principal = components["total_principal"]
        total_interest_with_iva = components["total_interest"]
        
        payment = (
            principal_main + principal_sf + principal_kt + principal_ins  # Component principals
            + total_interest_with_iva
            + gps_monthly_fee
            + gps_install_this_month
        )

        # --- Update balances ---
        balance_main -= principal_main
        balance_sf -= principal_sf
        balance_kt -= principal_kt
        # Only update insurance balance for first 12 months
        if insurance_amt > 0 and month <= 12:
            balance_ins -= principal_ins

        ending_balance_main = max(balance_main, 0)
        ending_balance_sf = max(balance_sf, 0)
        ending_balance_kt = max(balance_kt, 0)
        # Insurance balance becomes 0 after month 12
        ending_balance_ins = max(balance_ins, 0) if insurance_amt > 0 and month <= 12 else 0.0

        # Calculate interest components for display
        # Extract base interest from what we already calculated (remove IVA)
        # SAFETY: Ensure IVA divisor is never zero
        iva_divisor = 1 + IVA_RATE
        if iva_divisor == 0:
            iva_divisor = 1.16  # Default to 16% IVA
        interest_base_main = interest_main / iva_divisor
        interest_base_sf = interest_sf / iva_divisor
        interest_base_kt = interest_kt / iva_divisor
        interest_base_ins = interest_ins / iva_divisor if insurance_amt > 0 else 0.0
        
        # Total base interest
        interest_base_total = interest_base_main + interest_base_sf + interest_base_kt + interest_base_ins
        
        # For Excel compatibility: GPS without IVA for display
        gps_monthly_no_iva = gps_monthly_fee / iva_divisor  # 350
        # GPS installation is now in principal, not in cargos
        cargos_no_iva = gps_monthly_no_iva  # Only monthly fee, no installation
        
        # IVA calculation
        # IVA on interest AND GPS monthly (Excel formula: (Interest + Cargos) * 16%)
        # Note: GPS installation IVA is NOT included separately - it's already in the payment
        iva_total = (interest_base_total + cargos_no_iva) * IVA_RATE
        
        # --- Append detailed row ---
        table.append({
            "month": month,
            # Spanish column names for Excel compatibility
            "cuota": month,  # Payment number
            "saldo_insoluto": beginning_balance_main + beginning_balance_sf + beginning_balance_kt + beginning_balance_ins,  # Beginning balance
            "capital": total_principal_display,  # Principal (includes GPS install in month 1)
            "interes": interest_base_total,  # Interest without IVA
            "cargos": cargos_no_iva,  # GPS fees WITHOUT IVA (Excel format)
            "iva": iva_total,  # IVA on (interest + GPS + GPS install)
            "exigible": payment,  # Total payment
            
            # Legacy fields for backward compatibility
            "beginning_balance": beginning_balance_main + beginning_balance_sf + beginning_balance_kt + beginning_balance_ins,
            "payment": payment,
            "principal": total_principal_display,  # Matches capital column
            "interest": interest_main + interest_sf + interest_kt + interest_ins,  # Interest with IVA
            "ending_balance": ending_balance_main + ending_balance_sf + ending_balance_kt + ending_balance_ins,
            "balance": ending_balance_main + ending_balance_sf + ending_balance_kt + ending_balance_ins,
            
            # Detailed balances
            "end_balance_main": ending_balance_main,
            "end_balance_service_fee": ending_balance_sf,
            "end_balance_kavak_total": ending_balance_kt,
            "end_balance_insurance": ending_balance_ins,
            "end_balance_total": ending_balance_main + ending_balance_sf + ending_balance_kt + ending_balance_ins,
        })

    return table