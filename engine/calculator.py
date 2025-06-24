import numpy_financial as npf
from functools import lru_cache
from config import IVA_RATE

@lru_cache(maxsize=256)
def calculate_final_npv(loan_amount, interest_rate, term_months):
    """
    Calculates the Net Present Value of the interest income for the loan.
    This uses the audited method: interest cash flows are calculated with the
    contractual rate, and then discounted using the IVA-inclusive rate.
    """
    if loan_amount <= 0:
        return 0.0

    monthly_rate = interest_rate / 12
    monthly_rate_with_iva = (interest_rate * (1 + IVA_RATE)) / 12

    # Interest cash flow for each period (contractual interest, no IVA yet)
    interest_payments = [
        abs(npf.ipmt(monthly_rate, period, term_months, -loan_amount))
        for period in range(1, term_months + 1)
    ]
    
    # The actual cash flow includes IVA on interest
    interest_cash_flow_with_iva = [(p * (1 + IVA_RATE)) for p in interest_payments]

    # Discount at the IVA-inclusive rate
    npv = npf.npv(monthly_rate_with_iva, [0] + interest_cash_flow_with_iva)
    return npv


def generate_amortization_table(offer_details: dict) -> list[dict]:
    """
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
    
    gps_monthly_fee = 350.0 * (1 + IVA_RATE)
    gps_install_fee = float(offer_details.get("gps_install_fee", 0.0) or 0.0)

    # CRITICAL: Apply IVA to the rate once (as per audited logic)
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
    months_since_insurance_reset = 1

    table = []

    for month in range(1, term + 1):
        # Reset insurance financing every 12 months
        if months_since_insurance_reset > 12 and insurance_amt > 0:
            balance_ins = insurance_amt
            months_since_insurance_reset = 1

        # Beginning balances
        beginning_balance_main = balance_main
        beginning_balance_sf = balance_sf
        beginning_balance_kt = balance_kt
        beginning_balance_ins = balance_ins if insurance_amt > 0 else 0.0

        # --- Main loan bucket ---
        principal_main = abs(npf.ppmt(monthly_rate_with_iva, month, term, -financed_main))
        interest_main = abs(npf.ipmt(monthly_rate, month, term, -financed_main)) * (1 + IVA_RATE)
        
        # --- Service Fee bucket ---
        principal_sf = abs(npf.ppmt(monthly_rate_with_iva, month, term, -financed_sf))
        interest_sf = abs(npf.ipmt(monthly_rate, month, term, -financed_sf)) * (1 + IVA_RATE)

        # --- Kavak Total bucket ---
        principal_kt = abs(npf.ppmt(monthly_rate_with_iva, month, term, -financed_kt))
        interest_kt = abs(npf.ipmt(monthly_rate, month, term, -financed_kt)) * (1 + IVA_RATE)

        # --- Insurance bucket (recurring every 12 months) ---
        principal_ins = abs(npf.ppmt(monthly_rate_with_iva, months_since_insurance_reset, 12, -insurance_amt)) if insurance_amt > 0 else 0.0
        interest_ins = abs(npf.ipmt(monthly_rate, months_since_insurance_reset, 12, -insurance_amt)) * (1 + IVA_RATE) if insurance_amt > 0 else 0.0

        # --- Aggregate payment ---
        # Add GPS install fee only to first month
        gps_install_this_month = gps_install_fee if month == 1 else 0.0
        
        # For Excel compatibility: GPS installation WITH IVA is part of principal in month 1
        gps_install_principal = gps_install_fee if month == 1 else 0.0  # 870 with IVA
        
        # Calculate total principal for DISPLAY (including GPS install in month 1 per Excel)
        total_principal_display = principal_main + principal_sf + principal_kt + principal_ins + gps_install_principal
        
        # For payment calculation, use component principals only
        total_principal = principal_main + principal_sf + principal_kt + principal_ins
        
        # Calculate total interest WITH IVA (as used in actual payment)
        total_interest_with_iva = interest_main + interest_sf + interest_kt + interest_ins
        
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
        if insurance_amt > 0:
            balance_ins -= principal_ins
            months_since_insurance_reset += 1

        ending_balance_main = max(balance_main, 0)
        ending_balance_sf = max(balance_sf, 0)
        ending_balance_kt = max(balance_kt, 0)
        ending_balance_ins = max(balance_ins, 0) if insurance_amt > 0 else 0.0

        # Calculate interest components for display
        # Extract base interest from what we already calculated (remove IVA)
        interest_base_main = interest_main / (1 + IVA_RATE)
        interest_base_sf = interest_sf / (1 + IVA_RATE)
        interest_base_kt = interest_kt / (1 + IVA_RATE)
        interest_base_ins = interest_ins / (1 + IVA_RATE) if insurance_amt > 0 else 0.0
        
        # Total base interest
        interest_base_total = interest_base_main + interest_base_sf + interest_base_kt + interest_base_ins
        
        # For Excel compatibility: GPS without IVA for display
        gps_monthly_no_iva = gps_monthly_fee / (1 + IVA_RATE)  # 350
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