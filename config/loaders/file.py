"""
File-based configuration loader.
Loads configuration from JSON files with support for base and override files.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from .base import BaseLoader

logger = logging.getLogger(__name__)


class FileLoader(BaseLoader):
    """
    Loads configuration from JSON files.
    Supports both base configuration and runtime overrides.
    """
    
    PRIORITY = 2  # Higher than env vars, lower than database
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize file loader.
        
        Args:
            config_dir: Directory containing config files (default: "config")
        """
        self.config_dir = config_dir or Path("config")
        self.base_config_file = self.config_dir / "base_config.json"
        self.override_file = self.config_dir / "engine_config.json"
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from JSON files.
        
        Returns:
            Dict with merged configuration from base and override files
        """
        logger.debug(f"Loading configuration from {self.config_dir}")
        config = {}
        
        # Load base configuration
        if self.base_config_file.exists():
            try:
                base_config = self._load_json_file(self.base_config_file)
                flat_base = self._flatten_dict(base_config)
                config.update(flat_base)
                logger.info(f"Loaded {len(flat_base)} values from {self.base_config_file.name}")
            except Exception as e:
                logger.error(f"Failed to load base config: {e}")
        
        # Load override configuration (higher precedence)
        if self.override_file.exists():
            try:
                override_config = self._load_json_file(self.override_file)
                flat_override = self._flatten_dict(override_config)
                config.update(flat_override)
                logger.info(f"Loaded {len(flat_override)} overrides from {self.override_file.name}")
            except Exception as e:
                logger.error(f"Failed to load override config: {e}")
        
        return config
    
    def save_override(self, key: str, value: Any) -> bool:
        """
        Save a configuration override to the override file.
        
        Args:
            key: Configuration key in dot notation
            value: Value to save
            
        Returns:
            bool: True if successful
        """
        try:
            # Load existing overrides
            overrides = {}
            if self.override_file.exists():
                overrides = self._load_json_file(self.override_file)
            
            # Convert dot notation to nested dict
            parts = key.split('.')
            current = overrides
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Convert Decimal to string for JSON
            if isinstance(value, Decimal):
                value = str(value)
            
            current[parts[-1]] = value
            
            # Save back
            with open(self.override_file, 'w') as f:
                json.dump(overrides, f, indent=2)
            
            logger.info(f"Saved override {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save override: {e}")
            return False
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file"""
        with open(file_path) as f:
            data = json.load(f)
        
        # Convert string decimals to Decimal objects
        return self._convert_decimals(data)
    
    def _convert_decimals(self, obj: Any) -> Any:
        """Recursively convert decimal strings to Decimal objects"""
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(v) for v in obj]
        elif isinstance(obj, str) and self._is_decimal_string(obj):
            try:
                return Decimal(obj)
            except:
                return obj
        return obj
    
    def _is_decimal_string(self, value: str) -> bool:
        """Check if a string should be converted to Decimal"""
        try:
            float(value)
            return '.' in value or 'e' in value.lower()
        except:
            return False
    
    def _flatten_dict(self, d: Dict, parent_key: str = '') -> Dict[str, Any]:
        """
        Flatten nested dictionary to dot notation.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)