from __future__ import annotations
from typing import Dict
import numpy_financial as npf
from functools import lru_cache
from decimal import Decimal, ROUND_HALF_UP
from config.configuration_manager import get_config
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Get configuration manager
config = get_config()


class FinancialValidationError(ValueError):
    """Raised when financial inputs are invalid"""
    pass


def validate_financial_inputs(
    *,
    loan_base: float = None,
    service_fee_amount: float = None,
    kavak_total_amount: float = None,
    insurance_amount: float = None,
    annual_rate_nominal: float = None,
    term_months: int = None,
    period: int = None,
    gps_install_fee: float = None,
) -> None:
    """
    Validate financial calculation inputs to prevent invalid calculations.
    
    Raises:
        FinancialValidationError: If any input is out of valid bounds
    """
    # Get validation bounds from configuration
    min_loan = float(config.get_decimal("financial.min_loan_amount"))
    max_loan = float(config.get_decimal("financial.max_loan_amount"))
    min_rate = float(config.get_decimal("financial.min_interest_rate"))
    max_rate = float(config.get_decimal("financial.max_interest_rate"))
    min_term = config.get_int("financial.min_term_months")
    max_term = config.get_int("financial.max_term_months")
    max_fee = float(config.get_decimal("fees.cac_bonus.max") * 20)  # Use reasonable multiple of max bonus
    
    # Validate loan base amount
    if loan_base is not None:
        if not isinstance(loan_base, (int, float, Decimal)):
            raise FinancialValidationError(f"loan_base must be numeric, got {type(loan_base).__name__}")
        if loan_base < min_loan or loan_base > max_loan:
            raise FinancialValidationError(
                f"loan_base must be between {min_loan:,.0f} and {max_loan:,.0f}, got {loan_base:,.0f}"
            )
    
    # Validate fee amounts
    for fee_name, fee_value in [
        ("service_fee_amount", service_fee_amount),
        ("kavak_total_amount", kavak_total_amount),
        ("insurance_amount", insurance_amount),
        ("gps_install_fee", gps_install_fee),
    ]:
        if fee_value is not None:
            if not isinstance(fee_value, (int, float, Decimal)):
                raise FinancialValidationError(f"{fee_name} must be numeric, got {type(fee_value).__name__}")
            if fee_value < 0 or fee_value > max_fee:
                raise FinancialValidationError(
                    f"{fee_name} must be between 0 and {max_fee:,.0f}, got {fee_value:,.0f}"
                )
    
    # Validate interest rate
    if annual_rate_nominal is not None:
        if not isinstance(annual_rate_nominal, (int, float, Decimal)):
            raise FinancialValidationError(f"annual_rate_nominal must be numeric, got {type(annual_rate_nominal).__name__}")
        if annual_rate_nominal < min_rate or annual_rate_nominal > max_rate:
            raise FinancialValidationError(
                f"annual_rate_nominal must be between {min_rate:.0%} and {max_rate:.0%}, got {annual_rate_nominal:.2%}"
            )
    
    # Validate term
    if term_months is not None:
        if not isinstance(term_months, int):
            raise FinancialValidationError(f"term_months must be integer, got {type(term_months).__name__}")
        if term_months < min_term or term_months > max_term:
            raise FinancialValidationError(
                f"term_months must be between {min_term} and {max_term}, got {term_months}"
            )
    
    # Validate period
    if period is not None:
        if not isinstance(period, int):
            raise FinancialValidationError(f"period must be integer, got {type(period).__name__}")
        if period < 1:
            raise FinancialValidationError(f"period must be >= 1, got {period}")
        # Check period against term if both provided
        if term_months is not None and period > term_months:
            raise FinancialValidationError(f"period ({period}) cannot exceed term_months ({term_months})")
    
    # Validate combined amounts don't exceed reasonable limits
    if all(x is not None for x in [loan_base, service_fee_amount, kavak_total_amount, insurance_amount]):
        total_financed = loan_base + service_fee_amount + kavak_total_amount + insurance_amount
        if total_financed > max_loan * 1.5:  # Allow some headroom for total
            raise FinancialValidationError(
                f"Total financed amount ({total_financed:,.0f}) exceeds reasonable limits"
            )

def calculate_payment_components(
    *,
    loan_base: float,
    service_fee_amount: float,
    kavak_total_amount: float,
    insurance_amount: float,
    annual_rate_nominal: float,
    term_months: int,
    period: int,
    insurance_term: int = 12,
) -> Dict[str, float]:
    """
    Core payment calculation logic - SINGLE SOURCE OF TRUTH
    Calculates principal and interest components for any given period.
    
    This is the ONLY place where payment calculations should happen!
    Used by both calculate_monthly_payment() and generate_amortization_table()
    """
    # Validate all inputs before calculation
    validate_financial_inputs(
        loan_base=loan_base,
        service_fee_amount=service_fee_amount,
        kavak_total_amount=kavak_total_amount,
        insurance_amount=insurance_amount,
        annual_rate_nominal=annual_rate_nominal,
        term_months=term_months,
        period=period
    )
    
    # Additional validation for insurance term
    if not isinstance(insurance_term, int) or insurance_term < 1 or insurance_term > 60:
        raise FinancialValidationError(f"insurance_term must be between 1 and 60, got {insurance_term}")
    
    # Get IVA rate from configuration
    iva_rate = float(config.get_decimal("financial.iva_rate"))
    
    # Log calculation for audit trail
    if config.get_bool("features.enable_audit_logging"):
        from .financial_audit import get_audit_logger, CalculationType
        audit_logger = get_audit_logger()
        
        audit_inputs = {
            "loan_base": str(loan_base),
            "service_fee_amount": str(service_fee_amount),
            "kavak_total_amount": str(kavak_total_amount),
            "insurance_amount": str(insurance_amount),
            "annual_rate_nominal": str(annual_rate_nominal),
            "term_months": term_months,
            "period": period,
            "insurance_term": insurance_term,
            "iva_rate": str(iva_rate)
        }
    
    # Define rates exactly as in the audited Excel sheet
    monthly_rate = annual_rate_nominal / 12.0
    rate_with_iva = annual_rate_nominal * (1 + iva_rate)
    monthly_rate_with_iva = rate_with_iva / 12.0
    
    # Principal calculations (using IVA-inclusive rate)
    principal_main = abs(npf.ppmt(monthly_rate_with_iva, period, term_months, -loan_base)) if loan_base > 0 else 0.0
    principal_sf = abs(npf.ppmt(monthly_rate_with_iva, period, term_months, -service_fee_amount)) if service_fee_amount > 0 else 0.0
    principal_kt = abs(npf.ppmt(monthly_rate_with_iva, period, term_months, -kavak_total_amount)) if kavak_total_amount > 0 else 0.0
    
    # Insurance uses special period calculation (resets every 12 months)
    insurance_period = ((period - 1) % 12) + 1 if insurance_amount > 0 else 0
    principal_ins = abs(npf.ppmt(monthly_rate_with_iva, insurance_period, insurance_term, -insurance_amount)) if insurance_amount > 0 and insurance_period <= insurance_term else 0.0
    
    # Interest calculations WITH IVA (using contractual rate then applying IVA)
    interest_main = abs(npf.ipmt(monthly_rate, period, term_months, -loan_base)) * (1 + iva_rate) if loan_base > 0 else 0.0
    interest_sf = abs(npf.ipmt(monthly_rate, period, term_months, -service_fee_amount)) * (1 + iva_rate) if service_fee_amount > 0 else 0.0
    interest_kt = abs(npf.ipmt(monthly_rate, period, term_months, -kavak_total_amount)) * (1 + iva_rate) if kavak_total_amount > 0 else 0.0
    interest_ins = abs(npf.ipmt(monthly_rate, insurance_period, insurance_term, -insurance_amount)) * (1 + iva_rate) if insurance_amount > 0 and insurance_period <= insurance_term else 0.0
    
    results = {
        "principal_main": principal_main,
        "principal_sf": principal_sf,
        "principal_kt": principal_kt,
        "principal_ins": principal_ins,
        "interest_main": interest_main,
        "interest_sf": interest_sf,
        "interest_kt": interest_kt,
        "interest_ins": interest_ins,
        "total_principal": principal_main + principal_sf + principal_kt + principal_ins,
        "total_interest": interest_main + interest_sf + interest_kt + interest_ins,
    }
    
    # Log outputs for audit trail
    if config.get_bool("features.enable_audit_logging"):
        audit_outputs = {k: str(v) for k, v in results.items()}
        audit_logger.log_calculation(
            calculation_type=CalculationType.PAYMENT_COMPONENT,
            inputs=audit_inputs,
            outputs=audit_outputs,
            metadata={
                "monthly_rate": str(monthly_rate),
                "monthly_rate_with_iva": str(monthly_rate_with_iva),
                "insurance_period": insurance_period
            }
        )
    
    return results


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
    # Validate all inputs before calculation
    validate_financial_inputs(
        loan_base=loan_base,
        service_fee_amount=service_fee_amount,
        kavak_total_amount=kavak_total_amount,
        insurance_amount=insurance_amount,
        annual_rate_nominal=annual_rate_nominal,
        term_months=term_months,
        gps_install_fee=gps_install_fee
    )
    
    # Get fee configuration
    gps_fees = config.get_by_prefix("fees.gps")
    gps_monthly_base = float(config.get_decimal("fees.gps.monthly"))
    iva_rate = float(config.get_decimal("financial.iva_rate"))
    apply_iva = config.get_bool("fees.gps.apply_iva", True)
    
    # Calculate GPS monthly fee with IVA
    gps_monthly_fee = gps_monthly_base * (1 + iva_rate) if apply_iva else gps_monthly_base
    
    # Audit logging
    if config.get_bool("features.enable_audit_logging"):
        from .financial_audit import get_audit_logger, CalculationType
        audit_logger = get_audit_logger()
        customer_id = None  # Would be passed in if available
    
    # Use the single source of truth for calculations
    components = calculate_payment_components(
        loan_base=loan_base,
        service_fee_amount=service_fee_amount,
        kavak_total_amount=kavak_total_amount,
        insurance_amount=insurance_amount,
        annual_rate_nominal=annual_rate_nominal,
        term_months=term_months,
        period=1  # First month
    )
    
    # Total payment - INCLUDING GPS install fee (as per Excel)
    payment = components["total_principal"] + components["total_interest"] + gps_monthly_fee + gps_install_fee
    
    result = {
        "monthly_payment": payment,
        "payment_total": payment,  # For compatibility
        "principal": components["total_principal"],
        "interest": components["total_interest"],
        "gps_fee": gps_monthly_fee,
        "gps_install": gps_install_fee,
        "iva_on_interest": 0.0,  # Not used in new calculation
        "total_financed": loan_base + service_fee_amount + kavak_total_amount + insurance_amount
    }
    
    # Complete audit logging
    if config.get_bool("features.enable_audit_logging"):
        audit_logger.log_payment_calculation(
            loan_amount=Decimal(str(loan_base)),
            interest_rate=Decimal(str(annual_rate_nominal)),
            term_months=term_months,
            fees={
                "service_fee": Decimal(str(service_fee_amount)),
                "kavak_total": Decimal(str(kavak_total_amount)),
                "insurance": Decimal(str(insurance_amount)),
                "gps_monthly": Decimal(str(gps_monthly_fee)),
                "gps_install": Decimal(str(gps_install_fee))
            },
            monthly_payment=Decimal(str(payment)),
            customer_id=customer_id
        )
    
    return result


@lru_cache(maxsize=256)
def calculate_final_npv(loan_amount, interest_rate, term_months):
    """
    Calculates the Net Present Value of the interest income for the loan.
    This uses the audited method: interest cash flows are calculated with the
    contractual rate, and then discounted using the IVA-inclusive rate.
    
    Moved from calculator.py to consolidate all financial calculations.
    """
    # Validate inputs
    if not isinstance(loan_amount, (int, float)):
        raise FinancialValidationError(f"loan_amount must be numeric, got {type(loan_amount).__name__}")
    if not isinstance(interest_rate, (int, float)):
        raise FinancialValidationError(f"interest_rate must be numeric, got {type(interest_rate).__name__}")
    if not isinstance(term_months, int):
        raise FinancialValidationError(f"term_months must be integer, got {type(term_months).__name__}")
    
    # Validate ranges
    if loan_amount < 0 or loan_amount > MAX_LOAN_AMOUNT:
        raise FinancialValidationError(
            f"loan_amount must be between 0 and {MAX_LOAN_AMOUNT:,.0f}, got {loan_amount:,.0f}"
        )
    if interest_rate < MIN_INTEREST_RATE or interest_rate > MAX_INTEREST_RATE:
        raise FinancialValidationError(
            f"interest_rate must be between {MIN_INTEREST_RATE:.0%} and {MAX_INTEREST_RATE:.0%}, got {interest_rate:.2%}"
        )
    if term_months < MIN_TERM_MONTHS or term_months > MAX_TERM_MONTHS:
        raise FinancialValidationError(
            f"term_months must be between {MIN_TERM_MONTHS} and {MAX_TERM_MONTHS}, got {term_months}"
        )
    
    if loan_amount <= 0:
        return 0.0

    # Get IVA rate from configuration
    iva_rate = float(config.get_decimal("financial.iva_rate"))
    
    monthly_rate = interest_rate / 12
    monthly_rate_with_iva = (interest_rate * (1 + iva_rate)) / 12

    # Interest cash flow for each period (contractual interest, no IVA yet)
    interest_payments = [
        abs(npf.ipmt(monthly_rate, period, term_months, -loan_amount))
        for period in range(1, term_months + 1)
    ]
    
    # The actual cash flow includes IVA on interest
    cash_flows_with_iva = [payment * (1 + iva_rate) for payment in interest_payments]
    
    # Discount these cash flows using the IVA-inclusive discount rate
    npv = npf.npv(monthly_rate_with_iva, cash_flows_with_iva)
    
    # Audit logging
    if config.get_bool("features.enable_audit_logging"):
        from .financial_audit import get_audit_logger
        audit_logger = get_audit_logger()
        audit_logger.log_npv_calculation(
            loan_amount=Decimal(str(loan_amount)),
            interest_rate=Decimal(str(interest_rate)),
            term_months=term_months,
            npv=Decimal(str(npv)),
            monthly_rate=Decimal(str(monthly_rate)),
            monthly_rate_with_iva=Decimal(str(monthly_rate_with_iva)),
            iva_rate=Decimal(str(iva_rate))
        )
    
    return npv