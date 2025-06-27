import numpy_financial as npf
from decimal import Decimal, ROUND_HALF_UP
import os
from .payment_utils import calculate_payment_components, calculate_final_npv
from .financial_audit import get_audit_logger, CalculationType
from app.utils.data_validator import DataValidator, validate_calculation_input
from .type_utils import to_numeric, safe_add, zero_value
import logging

logger = logging.getLogger(__name__)

# Use configuration facade
from config.facade import ConfigProxy

config = ConfigProxy()


@validate_calculation_input
def generate_amortization_table(offer_details: dict) -> list[dict]:
    """
    Generate month-by-month amortization table using the EXACT audited logic.
    CRITICAL: This follows the exact calculation from the risk team.
    """
    # Use Decimal for precision if enabled
    use_decimal = config.get_bool("features.enable_decimal_precision", True)
    
    # Extract offer details and convert to appropriate type
    if use_decimal:
        loan_amount = Decimal(str(offer_details.get("loan_amount", 0.0) or offer_details.get(1, 0.0)))
        rate = Decimal(str(offer_details.get("interest_rate", 0.0) or offer_details.get(3, 0.0)))
        service_fee = Decimal(str(offer_details.get("service_fee_amount", 0.0) or offer_details.get(4, 0.0)))
        kavak_total = Decimal(str(offer_details.get("kavak_total_amount", 0.0) or offer_details.get(5, 0.0)))
        insurance_amt = Decimal(str(offer_details.get("insurance_amount", 0.0) or offer_details.get(6, 0.0)))
        gps_install_fee = Decimal(str(offer_details.get("gps_install_fee", 0.0) or 0.0))
    else:
        loan_amount = float(offer_details.get("loan_amount", 0.0) or offer_details.get(1, 0.0))
        rate = float(offer_details.get("interest_rate", 0.0) or offer_details.get(3, 0.0))
        service_fee = float(offer_details.get("service_fee_amount", 0.0) or offer_details.get(4, 0.0))
        kavak_total = float(offer_details.get("kavak_total_amount", 0.0) or offer_details.get(5, 0.0))
        insurance_amt = float(offer_details.get("insurance_amount", 0.0) or offer_details.get(6, 0.0))
        gps_install_fee = float(offer_details.get("gps_install_fee", 0.0) or 0.0)
    
    term = int(offer_details.get("term", 0) or offer_details.get(2, 0))
    
    # Get configuration values
    iva_rate = config.get_decimal("financial.iva_rate")
    gps_monthly_base = config.get_decimal("fees.gps.monthly")
    apply_iva = config.get_bool("fees.gps.apply_iva", True)
    
    # Calculate GPS monthly fee
    if use_decimal:
        gps_monthly_fee = gps_monthly_base * (Decimal("1") + iva_rate) if apply_iva else gps_monthly_base
    else:
        gps_monthly_fee = float(gps_monthly_base) * (1 + float(iva_rate)) if apply_iva else float(gps_monthly_base)

    # Start audit logging if enabled
    if config.get_bool("features.enable_audit_logging"):
        audit_logger = get_audit_logger()
        amortization_inputs = {
            "loan_amount": str(loan_amount),
            "interest_rate": str(rate),
            "term_months": term,
            "service_fee": str(service_fee),
            "kavak_total": str(kavak_total),
            "insurance_amount": str(insurance_amt),
            "gps_monthly_fee": str(gps_monthly_fee),
            "gps_install_fee": str(gps_install_fee),
            "iva_rate": str(iva_rate)
        }
    
    # CRITICAL: Apply IVA to the rate once (as per audited logic)
    if use_decimal:
        monthly_rate = rate / Decimal("12")
        rate_with_iva = rate * (Decimal("1") + iva_rate)
        monthly_rate_with_iva = rate_with_iva / Decimal("12")
    else:
        monthly_rate = rate / 12
        rate_with_iva = rate * (1 + float(iva_rate))
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
        gps_install_this_month = gps_install_fee if month == 1 else zero_value(use_decimal)
        
        # For Excel compatibility: GPS installation WITH IVA is part of principal in month 1
        gps_install_principal = gps_install_fee if month == 1 else zero_value(use_decimal)  # 870 with IVA
        
        # Calculate total principal for DISPLAY (including GPS install in month 1 per Excel)
        total_principal_display = safe_add(
            principal_main, principal_sf, principal_kt, principal_ins, gps_install_principal,
            use_decimal=use_decimal
        )
        
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
        if insurance_amt > 0:
            balance_ins -= principal_ins
            months_since_insurance_reset += 1

        ending_balance_main = max(balance_main, 0)
        ending_balance_sf = max(balance_sf, 0)
        ending_balance_kt = max(balance_kt, 0)
        ending_balance_ins = max(balance_ins, 0) if insurance_amt > 0 else 0.0

        # Calculate interest components for display
        # Extract base interest from what we already calculated (remove IVA)
        if use_decimal:
            iva_divisor = Decimal("1") + iva_rate
            interest_base_main = interest_main / iva_divisor
            interest_base_sf = interest_sf / iva_divisor
            interest_base_kt = interest_kt / iva_divisor
            interest_base_ins = interest_ins / iva_divisor if insurance_amt > 0 else Decimal("0")
        else:
            iva_divisor = 1 + float(iva_rate)
            interest_base_main = interest_main / iva_divisor
            interest_base_sf = interest_sf / iva_divisor
            interest_base_kt = interest_kt / iva_divisor
            interest_base_ins = interest_ins / iva_divisor if insurance_amt > 0 else 0.0
        
        # Total base interest
        interest_base_total = interest_base_main + interest_base_sf + interest_base_kt + interest_base_ins
        
        # For Excel compatibility: GPS without IVA for display
        if use_decimal:
            gps_monthly_no_iva = gps_monthly_fee / iva_divisor
        else:
            gps_monthly_no_iva = gps_monthly_fee / iva_divisor
        # GPS installation is now in principal, not in cargos
        cargos_no_iva = gps_monthly_no_iva  # Only monthly fee, no installation
        
        # IVA calculation
        # IVA on interest AND GPS monthly (Excel formula: (Interest + Cargos) * 16%)
        # Note: GPS installation IVA is NOT included separately - it's already in the payment
        if use_decimal:
            iva_total = (interest_base_total + cargos_no_iva) * iva_rate
        else:
            iva_total = (interest_base_total + cargos_no_iva) * float(iva_rate)
        
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

    # Complete audit logging
    if config.get_bool("features.enable_audit_logging"):
        amortization_outputs = {
            "rows_generated": len(table),
            "total_payments": sum(float(row["payment"]) for row in table),
            "total_principal": sum(float(row["principal"]) for row in table),
            "total_interest": sum(float(row["interest"]) for row in table),
            "first_payment": float(table[0]["payment"]) if table else 0,
            "last_payment": float(table[-1]["payment"]) if table else 0
        }
        
        audit_logger.log_calculation(
            calculation_type=CalculationType.AMORTIZATION,
            inputs=amortization_inputs,
            outputs=amortization_outputs,
            metadata={
                "monthly_rate": str(monthly_rate),
                "monthly_rate_with_iva": str(monthly_rate_with_iva),
                "use_decimal": use_decimal
            }
        )
    
    return table