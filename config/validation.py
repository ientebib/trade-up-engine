"""
Configuration validation to prevent startup crashes
"""
import logging
from typing import Dict, List, Tuple

from .facade import get_all, get_decimal

logger = logging.getLogger(__name__)


def validate_config() -> Tuple[bool, List[str]]:
    """
    Validate all critical configuration values on startup.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Critical financial parameters that must be positive
    positive_params = [
        ("financial.iva_rate", 0.0, 1.0),  # IVA must be between 0-100%
        ("fees.service.percentage", 0.0, 1.0),
        ("fees.cxa.percentage", 0.0, 1.0),
        ("fees.gps.monthly", 0.0, None),
        ("fees.gps.installation", 0.0, None),
        ("fees.insurance.amount", 0.0, None),
        ("fees.kavak_total.amount", 0.0, None),
    ]
    
    for param, min_val, max_val in positive_params:
        try:
            value = float(get_decimal(param))
            if min_val is not None and value < min_val:
                errors.append(f"{param} = {value} is below minimum {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"{param} = {value} is above maximum {max_val}")
        except Exception as e:
            errors.append(f"Failed to validate {param}: {e}")
    
    # Interest rates must be reasonable (0-100% annual)
    interest_rate_params = [
        "rates.A1", "rates.A2", "rates.B", "rates.C1", "rates.C2", "rates.C3",
        "rates.D1", "rates.D2", "rates.D3", "rates.E1", "rates.E2", "rates.E3",
        "rates.E4", "rates.E5", "rates.F1", "rates.F2", "rates.F3", "rates.F4"
    ]
    
    for param in interest_rate_params:
        try:
            value = float(get_decimal(param))
            if value < 0.0 or value > 1.0:  # 0-100% as decimal
                errors.append(f"{param} = {value} is not a valid interest rate (0-1)")
        except Exception:
            # Interest rates are optional, just log warning
            logger.warning(f"Interest rate {param} not configured")
    
    # Payment tiers must be ordered correctly
    try:
        all_config = get_all()
        tiers = all_config.get("tiers", {})
        
        refresh_max = float(tiers.get("refresh", {}).get("max", 0.05))
        upgrade_min = float(tiers.get("upgrade", {}).get("min", 0.05))
        upgrade_max = float(tiers.get("upgrade", {}).get("max", 0.25))
        max_upgrade_min = float(tiers.get("max_upgrade", {}).get("min", 0.25))
        
        if refresh_max > upgrade_min:
            errors.append(f"Refresh max ({refresh_max}) overlaps with upgrade min ({upgrade_min})")
        if upgrade_max > max_upgrade_min:
            errors.append(f"Upgrade max ({upgrade_max}) overlaps with max_upgrade min ({max_upgrade_min})")
            
    except Exception as e:
        errors.append(f"Failed to validate payment tiers: {e}")
    
    # Check for critical missing values
    critical_keys = [
        "financial.iva_rate",
        "fees.gps.monthly", 
        "fees.gps.installation",
        "fees.service.percentage"
    ]
    
    for key in critical_keys:
        try:
            value = get_decimal(key)
            if value is None:
                errors.append(f"Critical config key '{key}' is missing")
        except Exception:
            errors.append(f"Critical config key '{key}' is missing or invalid")
    
    # Log results
    if errors:
        logger.error(f"Configuration validation failed with {len(errors)} errors:")
        for error in errors:
            logger.error(f"  - {error}")
    else:
        logger.info("✅ Configuration validation passed")
    
    return len(errors) == 0, errors


def get_config_health() -> Dict:
    """
    Get configuration health status for monitoring.
    
    Returns:
        Dict with health status and any errors
    """
    is_valid, errors = validate_config()
    
    return {
        "status": "healthy" if is_valid else "unhealthy",
        "errors": errors,
        "error_count": len(errors),
        "checked_at": None  # Will be set by caller
    }