"""
Configuration Manager for Trade-Up Engine
Handles storage and retrieval of engine configuration settings
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_file="engine_config.json"):
        self.config_file = config_file
        self._default_config = {
            'use_custom_params': False,
            'use_range_optimization': True,
            'include_kavak_total': True,
            'service_fee_pct': 0.05,
            'cxa_pct': 0.04,
            'cac_bonus': 5000.0,
            'insurance_amount': 10999.0,
            'gps_fee': 350.0,
            'service_fee_range': [0.0, 5.0],
            'cxa_range': [0.0, 4.0],
            'cac_bonus_range': [0.0, 10000.0],
            'service_fee_step': 0.1,
            'cxa_step': 0.1,
            'cac_bonus_step': 100.0,
            'max_offers_per_tier': 50,
            'payment_delta_tiers': {
                'refresh': [-0.05, 0.05],
                'upgrade': [0.0501, 0.25],
                'max_upgrade': [0.2501, 1.0]
            },
            'term_priority': 'standard',
            'min_npv_threshold': 5000.0
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load engine configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    print(f"✅ Loaded engine configuration from {self.config_file}")
                    return config
        except Exception as e:
            print(f"⚠️ Could not load config: {e}")
        
        # Return default configuration
        return self._default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save engine configuration to file"""
        try:
            # Add timestamp
            config['last_updated'] = datetime.now().isoformat()
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Engine configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def reset_config(self) -> bool:
        """Reset configuration to defaults"""
        return self.save_config(self._default_config.copy())
    
    @property
    def default_config(self) -> Dict[str, Any]:
        """Get a copy of the default configuration"""
        return self._default_config.copy()


# ------------------------------------------------------------------
# Convenience module-level helpers using a shared ConfigManager
# ------------------------------------------------------------------

_manager = ConfigManager()
SCENARIO_RESULTS_FILE = "scenario_results.json"


def load_engine_config() -> Dict[str, Any]:
    """Load the engine configuration using the shared manager."""
    return _manager.load_config()


def save_engine_config(config: Dict[str, Any]) -> bool:
    """Save the engine configuration via the shared manager."""
    return _manager.save_config(config)


def save_scenario_results(results: Dict[str, Any]) -> bool:
    """Persist scenario analysis results to disk."""
    try:
        with open(SCENARIO_RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2)
        print(f"✅ Scenario results saved to {SCENARIO_RESULTS_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving scenario results: {e}")
        return False


def load_latest_scenario_results() -> Optional[Dict[str, Any]]:
    """Load the most recently saved scenario results if available."""
    try:
        if os.path.exists(SCENARIO_RESULTS_FILE):
            with open(SCENARIO_RESULTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load scenario results: {e}")
    return None
