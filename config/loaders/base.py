"""
Base loader interface for configuration sources.
All configuration loaders must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLoader(ABC):
    """
    Abstract base class for configuration loaders.
    
    Each loader is responsible for loading configuration from a specific source
    (e.g., defaults, environment, files, database) and has a priority that
    determines the order of precedence when merging configurations.
    """
    
    # Priority determines precedence (lower number = higher priority)
    # Database: 1, File: 2, Environment: 3, Defaults: 4
    PRIORITY: int = 999
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the source.
        
        Returns:
            Dict[str, Any]: Configuration dictionary with dot-notation keys
                           (e.g., "financial.iva_rate": 0.16)
        """
        pass
    
    @property
    def name(self) -> str:
        """Get the loader name for logging purposes"""
        return self.__class__.__name__
    
    def __repr__(self) -> str:
        return f"{self.name}(priority={self.PRIORITY})"