"""
Configuration management system

This module provides configuration management for the Trade-Up Engine.
"""
import logging

logger = logging.getLogger(__name__)

# Import from facade - the only configuration system
from .facade import (
    get as get_config_value,
    get_decimal,
    get_int,
    get_bool,
    get_list,
    get_gps_fees,
    get_payment_tiers,
    get_interest_rate,
    get_down_payment,
    set as set_config_value,
    reload as reload_config,
    validate as validate_config
)

# Export all functions regardless of which system is active
__all__ = [
    'get_config_value',
    'get_decimal',
    'get_int', 
    'get_bool',
    'get_list',
    'get_gps_fees',
    'get_payment_tiers',
    'get_interest_rate',
    'get_down_payment',
    'set_config_value',
    'reload_config',
    'validate_config'
]