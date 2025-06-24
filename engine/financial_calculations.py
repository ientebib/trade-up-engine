"""
Centralized financial calculations module
All payment, interest, and financial math in one place
"""
from typing import Dict, Tuple
import numpy_financial as npf
from config.config import IVA_RATE, GPS_MONTHLY, GPS_INSTALLATION, INSURANCE_ANNUAL

# Constants with clear documentation
MONTHS_PER_YEAR = 12
IVA_MULTIPLIER = 1 + IVA_RATE  # 1.16 for 16% IVA


def calculate_monthly_payment(
    loan_amount: float,
    annual_rate: float,
    term_months: int,
    include_gps_install: bool = True
) -> Dict[str, float]:
    """
    Calculate monthly payment for a Mexican auto loan.
    
    This follows the exact audited formula from the risk team:
    1. Apply IVA to the interest rate once at the beginning
    2. Calculate payment using IVA-inclusive rate
    3. Add GPS fees
    
    Args:
        loan_amount: Total amount to finance (principal)
        annual_rate: Annual interest rate (e.g., 0.1949 for 19.49%)
        term_months: Loan term in months (12, 24, 36, 48, 60, 72)
        include_gps_install: Whether to include GPS installation fee (first month only)
        
    Returns:
        Dictionary with payment components:
        - principal_payment: Principal portion
        - interest_payment: Interest portion (includes IVA)
        - gps_monthly: Monthly GPS fee (includes IVA)
        - gps_install: GPS installation fee (includes IVA, first month only)
        - total_payment: Total monthly payment
    """
    # Step 1: Calculate rates
    monthly_rate = annual_rate / MONTHS_PER_YEAR
    monthly_rate_with_iva = (annual_rate * IVA_MULTIPLIER) / MONTHS_PER_YEAR
    
    # Step 2: Calculate base payment components
    if loan_amount > 0 and term_months > 0:
        # Principal calculated with IVA-inclusive rate
        principal_payment = abs(npf.ppmt(monthly_rate_with_iva, 1, term_months, -loan_amount))
        
        # Interest calculated with base rate, then IVA applied
        interest_base = abs(npf.ipmt(monthly_rate, 1, term_months, -loan_amount))
        interest_payment = interest_base * IVA_MULTIPLIER
    else:
        principal_payment = 0.0
        interest_payment = 0.0
    
    # Step 3: Calculate GPS fees with IVA
    gps_monthly_with_iva = GPS_MONTHLY * IVA_MULTIPLIER
    gps_install_with_iva = GPS_INSTALLATION * IVA_MULTIPLIER if include_gps_install else 0.0
    
    # Step 4: Total payment
    total_payment = principal_payment + interest_payment + gps_monthly_with_iva + gps_install_with_iva
    
    return {
        'principal_payment': principal_payment,
        'interest_payment': interest_payment,
        'gps_monthly': gps_monthly_with_iva,
        'gps_install': gps_install_with_iva,
        'total_payment': total_payment
    }


def calculate_npv(
    loan_amount: float,
    annual_rate: float,
    term_months: int
) -> float:
    """
    Calculate Net Present Value of interest income.
    
    Uses the audited method:
    1. Calculate interest cash flows at contractual rate
    2. Apply IVA to get actual cash flows
    3. Discount at IVA-inclusive rate
    
    Args:
        loan_amount: Principal amount
        annual_rate: Annual interest rate
        term_months: Loan term in months
        
    Returns:
        NPV of interest income
    """
    if loan_amount <= 0:
        return 0.0
        
    monthly_rate = annual_rate / MONTHS_PER_YEAR
    monthly_rate_with_iva = (annual_rate * IVA_MULTIPLIER) / MONTHS_PER_YEAR
    
    # Calculate interest payments for each month
    interest_payments = []
    for month in range(1, term_months + 1):
        interest_base = abs(npf.ipmt(monthly_rate, month, term_months, -loan_amount))
        interest_payments.append(interest_base)
    
    # Apply IVA to get actual cash flows
    cash_flows_with_iva = [payment * IVA_MULTIPLIER for payment in interest_payments]
    
    # Discount at IVA-inclusive rate
    npv = npf.npv(monthly_rate_with_iva, [0] + cash_flows_with_iva)
    
    return npv


def calculate_effective_down_payment(
    vehicle_equity: float,
    car_price: float,
    cxa_pct: float = 0.04,
    cac_bonus: float = 0.0
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate effective down payment after fees.
    
    Args:
        vehicle_equity: Customer's vehicle trade-in value
        car_price: Price of new vehicle
        cxa_pct: CXA marketing fee percentage (default 4%)
        cac_bonus: CAC subsidy amount (reduces down payment requirement)
        
    Returns:
        Tuple of (effective_down_payment, fee_breakdown)
    """
    # Calculate fees
    cxa_fee = car_price * cxa_pct
    gps_install_with_iva = GPS_INSTALLATION * IVA_MULTIPLIER
    
    # Effective down payment calculation
    effective_down_payment = vehicle_equity - cxa_fee - gps_install_with_iva + cac_bonus
    
    fee_breakdown = {
        'vehicle_equity': vehicle_equity,
        'cxa_fee': cxa_fee,
        'gps_install_fee': gps_install_with_iva,
        'cac_bonus': cac_bonus,
        'effective_down_payment': effective_down_payment
    }
    
    return effective_down_payment, fee_breakdown


def calculate_loan_amount(
    car_price: float,
    down_payment: float,
    service_fee_pct: float = 0.04,
    kavak_total: float = 25000.0,
    insurance_annual: float = INSURANCE_ANNUAL
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate total loan amount including all financed items.
    
    Args:
        car_price: Vehicle price
        down_payment: Down payment amount
        service_fee_pct: Service fee percentage (default 4%)
        kavak_total: Kavak Total amount to finance
        insurance_annual: Annual insurance amount
        
    Returns:
        Tuple of (total_loan_amount, component_breakdown)
    """
    # Calculate components
    base_loan = car_price - down_payment
    service_fee = car_price * service_fee_pct
    
    # Total loan amount
    total_loan = base_loan + service_fee + kavak_total + insurance_annual
    
    component_breakdown = {
        'base_loan': base_loan,
        'service_fee': service_fee,
        'kavak_total': kavak_total,
        'insurance': insurance_annual,
        'total_loan': total_loan
    }
    
    return total_loan, component_breakdown


def calculate_payment_delta(
    new_payment: float,
    current_payment: float
) -> float:
    """
    Calculate payment change percentage.
    
    Args:
        new_payment: Proposed monthly payment
        current_payment: Current monthly payment
        
    Returns:
        Payment delta as decimal (0.05 = 5% increase)
    """
    if current_payment <= 0:
        return 0.0
        
    return (new_payment - current_payment) / current_payment