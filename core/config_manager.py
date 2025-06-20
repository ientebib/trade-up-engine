"""
Configuration Manager for Trade-Up Engine
Handles storage and retrieval of engine configuration settings
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Union
import logging
from core.logging_config import setup_logging
from .settings import EngineSettings

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file: str = "engine_config.json"):
        self.config_file = config_file
        # Default settings using the Pydantic model
        self._default_settings = EngineSettings()
    
    def load_config(self) -> EngineSettings:
        """Load engine configuration from file and validate it."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    logger.info(
                        f"✅ Loaded engine configuration from {self.config_file}"
                    )
                    return EngineSettings.model_validate(data)
        except Exception as e:
            logger.warning(f"⚠️ Could not load config: {e}")

        # Return default settings instance
        return self._default_settings
    
    def save_config(self, config: Union[Dict[str, Any], EngineSettings]) -> bool:
        """Save engine configuration to file."""
        try:
            settings = (
                config
                if isinstance(config, EngineSettings)
                else EngineSettings.model_validate(config)
            )
            settings.last_updated = datetime.now().isoformat()

            with open(self.config_file, "w") as f:
                json.dump(settings.model_dump(), f, indent=2)

            logger.info(f"✅ Engine configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False
    
    def reset_config(self) -> bool:
        """Reset configuration to defaults."""
        return self.save_config(self._default_settings)
    
    @property
    def default_config(self) -> EngineSettings:
        """Get the default configuration as ``EngineSettings``."""
        return self._default_settings


# ------------------------------------------------------------------
# Convenience module-level helpers using a shared ConfigManager
# ------------------------------------------------------------------

_manager = ConfigManager()
SCENARIO_RESULTS_FILE = "scenario_results.json"


def load_engine_config() -> EngineSettings:
    """Load the engine configuration using the shared manager."""
    return _manager.load_config()


def save_engine_config(config: Union[Dict[str, Any], EngineSettings]) -> bool:
    """Save the engine configuration via the shared manager."""
    return _manager.save_config(config)


def save_scenario_results(results: Dict[str, Any]) -> bool:
    """Persist scenario analysis results to disk."""
    try:
        with open(SCENARIO_RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"✅ Scenario results saved to {SCENARIO_RESULTS_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving scenario results: {e}")
        return False


def load_latest_scenario_results() -> Optional[Dict[str, Any]]:
    """Load the most recently saved scenario results if available."""
    try:
        if os.path.exists(SCENARIO_RESULTS_FILE):
            with open(SCENARIO_RESULTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Could not load scenario results: {e}")
    return None
