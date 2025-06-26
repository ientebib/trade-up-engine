"""
Configuration facade providing a clean, backward-compatible API.
This is the main entry point for the new configuration system.
"""
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
import logging
import threading

from .registry import ConfigRegistry

logger = logging.getLogger(__name__)

# Global registry instance
_registry: Optional[ConfigRegistry] = None
_registry_lock = threading.Lock()


def _get_registry() -> ConfigRegistry:
    """Get or create the global registry instance (thread-safe)"""
    global _registry
    if _registry is None:
        with _registry_lock:
            # Double-check locking pattern
            if _registry is None:
                _registry = ConfigRegistry()
                _registry.load_all()
    return _registry


# Main API functions
def get(key: str, default: Any = None) -> Any:
    """
    Get a configuration value.
    
    Args:
        key: Configuration key in dot notation (e.g., "financial.iva_rate")
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    return _get_registry().get(key, default)


def get_decimal(key: str, default: Decimal = Decimal("0")) -> Decimal:
    """
    Get a configuration value as Decimal.
    
    Args:
        key: Configuration key
        default: Default Decimal value
        
    Returns:
        Configuration value as Decimal
    """
    value = get(key, default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_int(key: str, default: int = 0) -> int:
    """
    Get a configuration value as integer.
    
    Args:
        key: Configuration key
        default: Default integer value
        
    Returns:
        Configuration value as int
    """
    value = get(key, default)
    return int(value)


def get_float(key: str, default: float = 0.0) -> float:
    """
    Get a configuration value as float.
    
    Args:
        key: Configuration key
        default: Default float value
        
    Returns:
        Configuration value as float
    """
    value = get(key, default)
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def get_bool(key: str, default: bool = False) -> bool:
    """
    Get a configuration value as boolean.
    
    Args:
        key: Configuration key
        default: Default boolean value
        
    Returns:
        Configuration value as bool
    """
    value = get(key, default)
    return bool(value)


def get_list(key: str, default: Optional[List] = None) -> List:
    """
    Get a configuration value as list.
    
    Args:
        key: Configuration key
        default: Default list value
        
    Returns:
        Configuration value as list
    """
    value = get(key, default or [])
    if isinstance(value, list):
        return value
    
    # Handle string values
    if isinstance(value, str):
        # Try JSON parsing first
        import json
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        
        # Try comma-separated values
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # Single value as list
        return [value]
    
    # Try converting other iterables
    try:
        return list(value)
    except:
        # Last resort: wrap single value in list
        return [value]


def get_dict(key: str, default: Optional[Dict] = None) -> Dict:
    """
    Get a configuration value as dictionary.
    
    Args:
        key: Configuration key
        default: Default dict value
        
    Returns:
        Configuration value as dict
    """
    value = get(key, default or {})
    if isinstance(value, dict):
        return value
    return dict(value)


def set(key: str, value: Any, persist: bool = True) -> bool:
    """
    Set a configuration value at runtime.
    
    Args:
        key: Configuration key
        value: Configuration value
        persist: Whether to persist to override file
        
    Returns:
        bool: True if successful
    """
    return _get_registry().set(key, value, persist)


def get_all() -> Dict[str, Any]:
    """
    Get all configuration values.
    
    Returns:
        Dict of all configuration key-value pairs
    """
    return _get_registry().get_all()


def get_by_prefix(prefix: str) -> Dict[str, Any]:
    """
    Get all configuration values with a given prefix.
    
    Args:
        prefix: Key prefix (e.g., "financial", "fees.gps")
        
    Returns:
        Dict of matching configuration values
    """
    return _get_registry().get_by_prefix(prefix)


def reload() -> Dict[str, Any]:
    """
    Reload configuration from all sources.
    
    Returns:
        Newly loaded configuration
    """
    return _get_registry().reload()


def validate() -> List[str]:
    """
    Validate configuration consistency.
    
    Returns:
        List of validation errors (empty if valid)
    """
    return _get_registry().validate()


# Convenience functions for common configurations
def get_gps_fees() -> Dict[str, Union[Decimal, bool]]:
    """Get GPS fee configuration"""
    return {
        "monthly": get_decimal("gps_fees.monthly"),
        "installation": get_decimal("gps_fees.installation"),
        "apply_iva": get_bool("gps_fees.apply_iva", True)
    }


def get_payment_tiers() -> Dict[str, tuple]:
    """Get payment tier configuration"""
    return {
        "refresh": (
            float(get_decimal("payment_tiers.refresh_min")),
            float(get_decimal("payment_tiers.refresh_max"))
        ),
        "upgrade": (
            float(get_decimal("payment_tiers.upgrade_min")),
            float(get_decimal("payment_tiers.upgrade_max"))
        ),
        "max_upgrade": (
            float(get_decimal("payment_tiers.max_upgrade_min")),
            float(get_decimal("payment_tiers.max_upgrade_max"))
        ),
    }


def get_interest_rate(risk_profile: str) -> Decimal:
    """Get interest rate for a risk profile"""
    return get_decimal(f"rates.{risk_profile}", Decimal("0.4399"))


def get_down_payment(profile_index: int, term: int) -> Decimal:
    """Get down payment percentage for profile and term"""
    return get_decimal(f"downpayment.{profile_index}.{term}", Decimal("0.3"))


def get_term_search_order() -> List[int]:
    """Get loan term search order"""
    return get_list("terms.search_order", [60, 72, 48, 36, 24, 12])


def get_iva_rate() -> Decimal:
    """Get IVA tax rate"""
    return get_decimal("financial.iva_rate", Decimal("0.16"))


def get_service_fees() -> Dict[str, Decimal]:
    """Get service fee configuration"""
    return {
        "service_fee_pct": get_decimal("service_fees.service_percentage"),
        "cxa_pct": get_decimal("service_fees.cxa_percentage"),
        "cac_bonus": get_decimal("cac_bonus.default"),
        "kavak_total_amount": get_decimal("kavak_total.amount")
    }


# Backward compatibility alias
get_config_value = get


# For debugging/monitoring
def get_source_info() -> List[Dict[str, Any]]:
    """Get information about configuration sources"""
    return _get_registry().get_source_info()


class ConfigProxy:
    """
    Proxy object that provides attribute-style access to configuration functions.
    
    This eliminates the need for duplicate wrapper classes across the codebase.
    Usage:
        from config.facade import ConfigProxy
        config = ConfigProxy()
        value = config.get_decimal("some.key")
    """
    
    def __getattr__(self, name):
        """Dynamically proxy method calls to facade functions"""
        import sys
        # Get the function from this module
        func = getattr(sys.modules[__name__], name, None)
        if func and callable(func):
            return func
        raise AttributeError(f"'ConfigProxy' object has no attribute '{name}'")