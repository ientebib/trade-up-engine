"""
Configuration Service - Centralized configuration management
"""
import json
import logging
import os
from typing import Dict, Any

from config.config import DEFAULT_FEES, PAYMENT_DELTA_TIERS, TERM_SEARCH_ORDER
from config.facade import ConfigProxy

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Service layer for configuration management.
    Handles loading, merging, and saving configuration.
    """
    
    CONFIG_FILE = "engine_config.json"
    
    @classmethod
    def get_current_config(cls) -> Dict[str, Any]:
        """
        Get current engine configuration.
        Loads saved overrides and merges with defaults.
        
        Returns:
            Dict with current configuration
        """
        # Load any saved config overrides
        saved_config = cls._load_saved_config()
        
        # Use configuration facade to get current values
        config = ConfigProxy()
        
        # Merge with defaults from configuration facade
        current_config = {
            "fees": {
                "service_fee_pct": saved_config.get('service_fee_pct', float(config.get_decimal('fees.service.percentage'))),
                "cxa_pct": saved_config.get('cxa_pct', float(config.get_decimal('fees.cxa.percentage'))),
                "cac_min": saved_config.get('cac_min', 0),
                "cac_max": saved_config.get('cac_max', 5000),
                "cac_bonus": saved_config.get('cac_bonus', float(config.get_decimal('fees.cac_bonus.default'))),
                "kavak_total_enabled": saved_config.get('kavak_total_enabled', True),
                "kavak_total_amount": saved_config.get('kavak_total_amount', float(config.get_decimal('fees.kavak_total.amount'))),
                "gps_monthly": saved_config.get('gps_monthly', float(config.get_decimal('fees.gps.monthly'))),
                "gps_installation": saved_config.get('gps_installation', float(config.get_decimal('fees.gps.installation'))),
                "insurance_annual": saved_config.get('insurance_annual', float(config.get_decimal('insurance.amount'))),
                "insurance_by_profile": {
                    "A": float(config.get_decimal('insurance.amount_a')),
                    "B": float(config.get_decimal('insurance.amount_b')),
                    "C": float(config.get_decimal('insurance.amount_c')),
                    "default": float(config.get_decimal('insurance.amount_default'))
                }
            },
            "tiers": {
                "refresh": {
                    "min": saved_config.get('refresh_min', PAYMENT_DELTA_TIERS['refresh'][0]),
                    "max": saved_config.get('refresh_max', PAYMENT_DELTA_TIERS['refresh'][1])
                },
                "upgrade": {
                    "min": saved_config.get('upgrade_min', PAYMENT_DELTA_TIERS['upgrade'][0]),
                    "max": saved_config.get('upgrade_max', PAYMENT_DELTA_TIERS['upgrade'][1])
                },
                "max_upgrade": {
                    "min": saved_config.get('max_upgrade_min', PAYMENT_DELTA_TIERS['max_upgrade'][0]),
                    "max": saved_config.get('max_upgrade_max', PAYMENT_DELTA_TIERS['max_upgrade'][1])
                }
            },
            "business_rules": {
                "min_npv": saved_config.get('min_npv', 5000),
                "max_payment_increase": saved_config.get('max_payment_increase', 1.0),  # 100%
                "available_terms": saved_config.get('available_terms', TERM_SEARCH_ORDER)
            }
        }
        
        return current_config
    
    @classmethod
    def save_config(cls, config_data: Dict[str, Any]) -> None:
        """
        Save configuration overrides.
        
        Args:
            config_data: Configuration dictionary to save
            
        Raises:
            IOError: If unable to save configuration
        """
        # Flatten the nested config for storage
        flat_config = cls._flatten_config(config_data)
        
        # Save to file
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(flat_config, f, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise IOError(f"Failed to save configuration: {str(e)}")
    
    @classmethod
    def _load_saved_config(cls) -> Dict[str, Any]:
        """
        Load saved configuration from file.
        
        Returns:
            Dict with saved configuration or empty dict if not found
        """
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load saved config: {e}")
                return {}
        return {}
    
    @classmethod
    def _flatten_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested configuration for storage.
        
        Args:
            config: Nested configuration dictionary
            
        Returns:
            Flattened configuration dictionary
        """
        return {
            'service_fee_pct': config['fees']['service_fee_pct'],
            'cxa_pct': config['fees']['cxa_pct'],
            'cac_min': config['fees']['cac_min'],
            'cac_max': config['fees']['cac_max'],
            'cac_bonus': config['fees']['cac_bonus'],
            'kavak_total_enabled': config['fees']['kavak_total_enabled'],
            'kavak_total_amount': config['fees']['kavak_total_amount'],
            'gps_monthly': config['fees']['gps_monthly'],
            'gps_installation': config['fees']['gps_installation'],
            'insurance_annual': config['fees']['insurance_annual'],
            'refresh_min': config['tiers']['refresh']['min'],
            'refresh_max': config['tiers']['refresh']['max'],
            'upgrade_min': config['tiers']['upgrade']['min'],
            'upgrade_max': config['tiers']['upgrade']['max'],
            'max_upgrade_min': config['tiers']['max_upgrade']['min'],
            'max_upgrade_max': config['tiers']['max_upgrade']['max'],
            'min_npv': config['business_rules']['min_npv'],
            'max_payment_increase': config['business_rules']['max_payment_increase'],
            'available_terms': config['business_rules']['available_terms']
        }


    @classmethod
    def get_config_for_template(cls) -> Dict[str, Any]:
        """
        Get configuration formatted for template display.
        Returns a flattened structure suitable for HTML templates.
        
        Returns:
            Flattened configuration dictionary
        """
        # Get the nested config
        config_data = cls.get_current_config()
        
        # Flatten for template - same structure the template expects
        return {
            "service_fee_pct": config_data['fees']['service_fee_pct'],
            "cxa_pct": config_data['fees']['cxa_pct'],
            "cac_min": config_data['fees']['cac_min'],
            "cac_max": config_data['fees']['cac_max'],
            "cac_bonus": config_data['fees']['cac_bonus'],
            "kavak_total_enabled": config_data['fees']['kavak_total_enabled'],
            "kavak_total_amount": config_data['fees']['kavak_total_amount'],
            "gps_monthly": config_data['fees']['gps_monthly'],
            "gps_installation": config_data['fees']['gps_installation'],
            "insurance_annual": config_data['fees']['insurance_annual'],
            "payment_delta_tiers": {
                'refresh': config_data['tiers']['refresh'],
                'upgrade': config_data['tiers']['upgrade'],
                'max_upgrade': config_data['tiers']['max_upgrade']
            },
            "available_terms": config_data['business_rules']['available_terms']
        }


# Create singleton instance
config_service = ConfigService()