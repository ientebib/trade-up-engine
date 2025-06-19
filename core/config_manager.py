"""
Configuration Manager for Trade-Up Engine
Handles storage and retrieval of engine configuration settings
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

CONFIG_FILE = "engine_config.json"
RESULTS_FILE = "scenario_results.json"

def save_engine_config(config: Dict[str, Any]) -> bool:
    """Save engine configuration to file"""
    try:
        # Add timestamp
        config['last_updated'] = datetime.now().isoformat()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Engine configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def load_engine_config() -> Dict[str, Any]:
    """Load engine configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print(f"✅ Loaded engine configuration from {CONFIG_FILE}")
                return config
    except Exception as e:
        print(f"⚠️ Could not load config: {e}")
    
    # Return default configuration
    return {
        'use_custom_params': False,
        'use_range_optimization': False,
        'include_kavak_total': True,
        'min_npv_threshold': 5000.0,
        'max_combinations_to_test': 100,  # Limit combinations for range optimization
        'early_stop_on_offers': 50  # Stop early if enough offers found
    }

def save_scenario_results(results: Dict[str, Any]) -> bool:
    """Save scenario analysis results"""
    try:
        # Add timestamp
        results['timestamp'] = datetime.now().isoformat()
        
        # Load existing results
        all_results = []
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE, 'r') as f:
                    all_results = json.load(f)
            except:
                all_results = []
        
        # Append new results
        all_results.append(results)
        
        # Keep only last 10 results
        if len(all_results) > 10:
            all_results = all_results[-10:]
        
        with open(RESULTS_FILE, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"✅ Scenario results saved to {RESULTS_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving results: {e}")
        return False

def load_latest_scenario_results() -> Dict[str, Any]:
    """Load the most recent scenario analysis results"""
    try:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r') as f:
                all_results = json.load(f)
                if all_results:
                    return all_results[-1]  # Return most recent
    except Exception as e:
        print(f"⚠️ Could not load results: {e}")
    
    return None

def clear_scenario_results() -> bool:
    """Clear all saved scenario results"""
    try:
        if os.path.exists(RESULTS_FILE):
            os.remove(RESULTS_FILE)
        return True
    except Exception as e:
        print(f"❌ Error clearing results: {e}")
        return False 