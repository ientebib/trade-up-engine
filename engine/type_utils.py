"""
Type conversion utilities for handling Decimal/float compatibility
"""
from decimal import Decimal
from typing import Union, Any

def to_numeric(value: Any, use_decimal: bool = False) -> Union[float, Decimal]:
    """
    Convert a value to numeric type (float or Decimal) based on configuration.
    
    Args:
        value: Value to convert
        use_decimal: Whether to use Decimal precision
        
    Returns:
        float or Decimal based on use_decimal flag
    """
    if value is None:
        return Decimal("0") if use_decimal else 0.0
    
    if use_decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    else:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value))

def ensure_float(value: Any) -> float:
    """
    Ensure a value is a float (for numpy_financial functions).
    
    Args:
        value: Value to convert
        
    Returns:
        float value
    """
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)

def safe_add(*values: Any, use_decimal: bool = False) -> Union[float, Decimal]:
    """
    Safely add multiple values of potentially different types.
    
    Args:
        *values: Values to add
        use_decimal: Whether to use Decimal precision
        
    Returns:
        Sum as float or Decimal
    """
    if use_decimal:
        result = Decimal("0")
        for val in values:
            if val is not None:
                result += to_numeric(val, use_decimal=True)
        return result
    else:
        result = 0.0
        for val in values:
            if val is not None:
                result += to_numeric(val, use_decimal=False)
        return result

def safe_multiply(a: Any, b: Any, use_decimal: bool = False) -> Union[float, Decimal]:
    """
    Safely multiply two values of potentially different types.
    
    Args:
        a, b: Values to multiply
        use_decimal: Whether to use Decimal precision
        
    Returns:
        Product as float or Decimal
    """
    a_num = to_numeric(a, use_decimal)
    b_num = to_numeric(b, use_decimal)
    return a_num * b_num

def safe_divide(a: Any, b: Any, use_decimal: bool = False) -> Union[float, Decimal]:
    """
    Safely divide two values of potentially different types.
    
    Args:
        a: Numerator
        b: Denominator
        use_decimal: Whether to use Decimal precision
        
    Returns:
        Quotient as float or Decimal
    """
    a_num = to_numeric(a, use_decimal)
    b_num = to_numeric(b, use_decimal)
    
    if b_num == 0:
        return to_numeric(0, use_decimal)
    
    return a_num / b_num

def zero_value(use_decimal: bool = False) -> Union[float, Decimal]:
    """
    Return zero in the appropriate type.
    
    Args:
        use_decimal: Whether to use Decimal precision
        
    Returns:
        0.0 or Decimal("0")
    """
    return Decimal("0") if use_decimal else 0.0