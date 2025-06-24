"""
Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict
import json
import logging

from config.config import DEFAULT_FEES, PAYMENT_DELTA_TIERS, TERM_SEARCH_ORDER

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config():
    """Get current engine configuration"""
    import os
    
    # Load any saved config overrides
    config_path = "engine_config.json"
    saved_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load saved config: {e}")
    
    # Merge with defaults
    current_config = {
        "fees": {
            "service_fee_pct": saved_config.get('service_fee_pct', DEFAULT_FEES['service_fee_pct']),
            "cxa_pct": saved_config.get('cxa_pct', DEFAULT_FEES['cxa_pct']),
            "cac_min": saved_config.get('cac_min', DEFAULT_FEES['cac_bonus_range'][0]),
            "cac_max": saved_config.get('cac_max', DEFAULT_FEES['cac_bonus_range'][1]),
            "cac_bonus": saved_config.get('cac_bonus', 0),
            "kavak_total_enabled": saved_config.get('kavak_total_enabled', True),
            "kavak_total_amount": saved_config.get('kavak_total_amount', DEFAULT_FEES['kavak_total_amount']),
            "gps_monthly": saved_config.get('gps_monthly', DEFAULT_FEES['gps_monthly']),
            "gps_installation": saved_config.get('gps_installation', DEFAULT_FEES['gps_installation']),
            "insurance_annual": saved_config.get('insurance_annual', DEFAULT_FEES['insurance_annual'])
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


@router.post("/save-config")
async def save_config(config: Dict = Body(...)):
    """Save engine configuration overrides"""
    # Flatten the nested config for storage
    flat_config = {
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
    
    # Save to file
    try:
        with open("engine_config.json", 'w') as f:
            json.dump(flat_config, f, indent=2)
        
        return JSONResponse({
            "status": "success",
            "message": "Configuration saved successfully"
        })
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")