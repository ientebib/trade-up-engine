"""
Configuration registry that manages multiple loaders and merges their results.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from .loaders.base import BaseLoader
from .loaders.defaults import DefaultsLoader
from .loaders.env import EnvLoader
from .loaders.file import FileLoader
from .loaders.database import DatabaseLoader

logger = logging.getLogger(__name__)


class ConfigRegistry:
    """
    Registry that manages configuration loaders and merges their results
    based on priority. Lower priority numbers override higher ones.
    """
    
    def __init__(self, loaders: Optional[List[BaseLoader]] = None):
        """
        Initialize registry with loaders.
        
        Args:
            loaders: List of loaders to use (default: all standard loaders)
        """
        if loaders is None:
            # Initialize with standard loaders
            self.loaders = [
                DefaultsLoader(),     # Priority 4
                EnvLoader(),         # Priority 3
                FileLoader(),        # Priority 2
                DatabaseLoader()     # Priority 1
            ]
        else:
            self.loaders = loaders
        
        # Sort by priority (reverse order for merging)
        self.loaders.sort(key=lambda x: x.PRIORITY, reverse=True)
        
        # Configuration cache
        self._config: Dict[str, Any] = {}
        self._loaded = False
    
    def load_all(self) -> Dict[str, Any]:
        """
        Load configuration from all sources and merge by priority.
        
        Returns:
            Merged configuration dictionary
        """
        logger.info("Loading configuration from all sources")
        merged_config = {}
        
        # Load from each source in priority order (lowest priority first)
        for loader in self.loaders:
            try:
                loader_config = loader.load()
                if loader_config:
                    # Update merged config (higher priority overwrites)
                    merged_config.update(loader_config)
                    logger.debug(f"{loader.name} contributed {len(loader_config)} values")
            except Exception as e:
                logger.error(f"Error loading from {loader.name}: {e}")
        
        self._config = merged_config
        self._loaded = True
        
        logger.info(f"Configuration loaded: {len(merged_config)} total values")
        return merged_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key in dot notation
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load_all()
        
        return self._config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        if not self._loaded:
            self.load_all()
        
        return self._config.copy()
    
    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """
        Get all configuration values with a given prefix.
        
        Args:
            prefix: Key prefix (e.g., "financial")
            
        Returns:
            Dict of matching configuration values
        """
        if not self._loaded:
            self.load_all()
        
        return {
            k: v for k, v in self._config.items()
            if k.startswith(prefix)
        }
    
    def set(self, key: str, value: Any, persist: bool = True) -> bool:
        """
        Set a configuration value at runtime.
        
        Args:
            key: Configuration key
            value: Configuration value
            persist: Whether to persist to override file
            
        Returns:
            bool: True if successful
        """
        # Update in-memory config
        self._config[key] = value
        
        # Persist to file if requested
        if persist:
            # Find file loader
            for loader in self.loaders:
                if isinstance(loader, FileLoader):
                    return loader.save_override(key, value)
        
        return True
    
    def reload(self) -> Dict[str, Any]:
        """
        Reload configuration from all sources.
        
        Returns:
            Newly loaded configuration
        """
        logger.info("Reloading configuration")
        self._loaded = False
        return self.load_all()
    
    def get_source_info(self) -> List[Dict[str, Any]]:
        """
        Get information about configuration sources.
        
        Returns:
            List of loader info dicts
        """
        return [
            {
                "name": loader.name,
                "priority": loader.PRIORITY,
                "type": loader.__class__.__name__
            }
            for loader in self.loaders
        ]
    
    def validate(self) -> List[str]:
        """
        Validate configuration consistency.
        
        Returns:
            List of validation errors (empty if valid)
        """
        if not self._loaded:
            self.load_all()
        
        errors = []
        
        # Check required keys
        required_keys = [
            "financial.iva_rate",
            "gps_fees.monthly", 
            "gps_fees.installation",
            "insurance.amount"
        ]
        
        for key in required_keys:
            if key not in self._config:
                errors.append(f"Missing required configuration: {key}")
        
        # Validate ranges
        validations = [
            ("financial.iva_rate", Decimal("0"), Decimal("1")),
            ("service_fees.service_percentage", Decimal("0"), Decimal("1")),
            ("service_fees.cxa_percentage", Decimal("0"), Decimal("1")),
            ("payment_tiers.refresh_min", Decimal("-1"), Decimal("0")),
            ("payment_tiers.refresh_max", Decimal("0"), Decimal("1")),
        ]
        
        for key, min_val, max_val in validations:
            value = self.get(key)
            if value is not None:
                if isinstance(value, (int, float)):
                    value = Decimal(str(value))
                if value < min_val or value > max_val:
                    errors.append(f"{key} value {value} outside valid range [{min_val}, {max_val}]")
        
        return errors