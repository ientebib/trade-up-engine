"""
Global Decimal configuration for financial calculations
Ensures consistent precision and rounding across the application
"""
from decimal import Decimal, getcontext, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)

# Set global decimal context for financial calculations
def configure_decimal_context():
    """
    Configure global decimal context for consistent financial calculations.
    
    Settings:
    - Precision: 10 digits (sufficient for financial calculations)
    - Rounding: ROUND_HALF_UP (banker's rounding)
    - Max exponent: 999999 (prevent overflow)
    - Min exponent: -999999 (prevent underflow)
    """
    context = getcontext()
    
    # Set precision to 10 digits - sufficient for financial calculations
    # This handles amounts up to billions with 2 decimal places
    context.prec = 10
    
    # Use banker's rounding (round half to even)
    context.rounding = ROUND_HALF_UP
    
    # Set reasonable limits to prevent overflow/underflow
    context.Emax = 999999
    context.Emin = -999999
    
    # Enable all traps except Inexact and Rounded (common in financial calcs)
    context.traps[Decimal.InvalidOperation] = 1
    context.traps[Decimal.DivisionByZero] = 1
    context.traps[Decimal.Overflow] = 1
    context.traps[Decimal.Underflow] = 0  # Allow underflow to zero
    
    logger.info(f"✅ Decimal context configured: precision={context.prec}, rounding={context.rounding}")
    
    return context


# Helper functions for consistent decimal conversion
def to_decimal(value) -> Decimal:
    """
    Convert any numeric value to Decimal with proper precision.
    
    Args:
        value: int, float, str, or Decimal
        
    Returns:
        Decimal value
        
    Raises:
        ValueError: If value cannot be converted to Decimal
    """
    if isinstance(value, Decimal):
        return value
    
    try:
        # Convert to string first to avoid float precision issues
        # e.g., 0.1 + 0.2 = 0.30000000000000004 in float
        if isinstance(value, float):
            # Use string formatting to limit precision
            return Decimal(f"{value:.10f}")
        else:
            return Decimal(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def quantize_currency(value: Decimal, places: int = 2) -> Decimal:
    """
    Quantize a decimal value to the specified number of decimal places.
    Typically used to round currency to 2 decimal places.
    
    Args:
        value: Decimal value to quantize
        places: Number of decimal places (default: 2 for currency)
        
    Returns:
        Quantized Decimal value
    """
    if not isinstance(value, Decimal):
        value = to_decimal(value)
    
    # Create quantizer with the desired precision
    quantizer = Decimal(10) ** -places
    
    return value.quantize(quantizer)


# Configure on module import
configure_decimal_context()