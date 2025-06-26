"""
Environment variable configuration loader.
Loads configuration from environment variables with proper type conversion.
"""
import os
from typing import Dict, Any
from decimal import Decimal
import json
import logging

from .base import BaseLoader

logger = logging.getLogger(__name__)


class EnvLoader(BaseLoader):
    """
    Loads configuration from environment variables.
    Supports the legacy KAVAK_* prefix and new structured prefixes.
    """
    
    PRIORITY = 3  # Higher than defaults, lower than files
    
    # Legacy environment variable mappings for backward compatibility
    LEGACY_MAPPINGS = {
        "KAVAK_IVA_RATE": "financial.iva_rate",
        "KAVAK_GPS_MONTHLY": "gps_fees.monthly", 
        "KAVAK_GPS_INSTALLATION": "gps_fees.installation",
        "KAVAK_INSURANCE_AMOUNT": "insurance.amount",
        "KAVAK_SERVICE_FEE_PCT": "service_fees.service_percentage",
        "KAVAK_CXA_PCT": "service_fees.cxa_percentage",
        "KAVAK_TOTAL_AMOUNT": "kavak_total.amount",
        "KAVAK_CAC_BONUS_MAX": "cac_bonus.max",
        "KAVAK_CACHE_TTL_HOURS": "system.cache_ttl_hours",
        "KAVAK_ENABLE_CACHING": "features.enable_caching",
    }
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dict with configuration values from environment
        """
        logger.debug("Loading configuration from environment variables")
        config = {}
        
        # Load legacy mappings
        for env_var, config_key in self.LEGACY_MAPPINGS.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    parsed_value = self._parse_value(config_key, value)
                    config[config_key] = parsed_value
                    logger.debug(f"Loaded {env_var} -> {config_key} = {parsed_value}")
                except Exception as e:
                    logger.warning(f"Failed to parse env var {env_var}: {e}")
        
        # Load structured environment variables
        # These follow the pattern: SECTION_SUBSECTION_KEY
        # e.g., FINANCIAL_IVA_RATE, GPS_FEES_MONTHLY
        env_prefixes = {
            "FINANCIAL_": "financial.",
            "GPS_FEES_": "gps_fees.",
            "INSURANCE_": "insurance.",
            "SERVICE_FEES_": "service_fees.",
            "KAVAK_TOTAL_": "kavak_total.",
            "CAC_BONUS_": "cac_bonus.",
            "PAYMENT_TIERS_": "payment_tiers.",
            "TERMS_": "terms.",
            "SYSTEM_": "system.",
            "FEATURES_": "features.",
            "RATES_": "rates.",
            "DOWNPAYMENT_": "downpayment."
        }
        
        for env_key, env_value in os.environ.items():
            for prefix, config_prefix in env_prefixes.items():
                if env_key.startswith(prefix):
                    # Convert env key to config key
                    # FINANCIAL_IVA_RATE -> financial.iva_rate
                    key_part = env_key[len(prefix):].lower()
                    config_key = config_prefix + key_part
                    
                    try:
                        parsed_value = self._parse_value(config_key, env_value)
                        config[config_key] = parsed_value
                        logger.debug(f"Loaded {env_key} -> {config_key} = {parsed_value}")
                    except Exception as e:
                        logger.warning(f"Failed to parse env var {env_key}: {e}")
                    break
        
        logger.info(f"Loaded {len(config)} configuration values from environment")
        return config
    
    def _parse_value(self, key: str, value: str) -> Any:
        """
        Parse string value to appropriate type based on key.
        
        Args:
            key: Configuration key (e.g., "financial.iva_rate")
            value: String value from environment
            
        Returns:
            Parsed value in appropriate type
        """
        # Decimal types
        if any(k in key for k in ["rate", "percentage", "amount", "fee", "bonus", "min", "max", "downpayment"]):
            return Decimal(value)
        
        # Integer types
        elif any(k in key for k in ["months", "seconds", "count", "requests", "customers", "hours"]):
            # Special case for float hours
            if "hours" in key:
                return float(value)
            return int(value)
        
        # Boolean types
        elif any(k in key for k in ["enable", "enabled", "apply"]):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # List types (JSON arrays)
        elif "search_order" in key:
            return json.loads(value)
        
        # Default to string
        return value