"""
Default configuration loader.
Provides all default values from the Pydantic schema.
"""
from typing import Dict, Any
from decimal import Decimal
import logging

from .base import BaseLoader
from ..schema import CoreSettings

logger = logging.getLogger(__name__)


class DefaultsLoader(BaseLoader):
    """
    Loads default configuration values from the Pydantic schema.
    This has the lowest priority and provides fallback values.
    """
    
    PRIORITY = 4  # Lowest priority
    
    def load(self) -> Dict[str, Any]:
        """
        Load default configuration from schema.
        
        Returns:
            Dict with all default values in dot-notation format
        """
        logger.debug("Loading default configuration values")
        
        # Create instance with all defaults
        defaults = CoreSettings()
        
        # Add hardcoded down payment matrix (not in schema defaults)
        downpayment_matrix = self._get_downpayment_matrix()
        
        # Flatten to dot notation
        flat_config = defaults.flatten()
        
        # Add downpayment matrix
        flat_config.update(downpayment_matrix)
        
        logger.info(f"Loaded {len(flat_config)} default configuration values")
        return flat_config
    
    def _get_downpayment_matrix(self) -> Dict[str, Decimal]:
        """Get the hardcoded down payment matrix"""
        # This matches the original data from configuration_manager.py
        matrix_data = [
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],    # Profile 0
            [0.25, 0.25, 0.25, 0.25, 0.25, 0.25],  # Profile 1
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 2
            [0.15, 0.15, 0.15, 0.15, 0.15, 0.15],  # Profile 3
            [0.15, 0.15, 0.15, 0.15, 0.15, 0.15],  # Profile 4
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 5
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 6
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 7
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 8
            [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],    # Profile 9
            [0.25, 0.25, 0.25, 0.25, 0.25, 0.25],  # Profile 10
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],    # Profile 11
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 12
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 13
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 14
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 15
            [0.75, 0.75, 0.75, 0.75, 0.75, 0.75],  # Profile 16
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 17
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 18
            [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],  # Profile 19
            [0.75, 0.75, 0.75, 0.75, 0.75, 0.75],  # Profile 20
            [0.25, 0.25, 0.25, 0.25, 0.25, 0.25],  # Profile 21
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],    # Profile 22
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],    # Profile 23
            [0.75, 0.75, 0.75, 0.75, 0.75, 0.75],  # Profile 24
            [0.9999, 0.9999, 0.9999, 0.9999, 0.9999, 0.9999]  # Profile 25
        ]
        
        terms = [12, 24, 36, 48, 60, 72]
        result = {}
        
        for profile_idx, profile_data in enumerate(matrix_data):
            for term_idx, term in enumerate(terms):
                key = f"downpayment.{profile_idx}.{term}"
                result[key] = Decimal(str(profile_data[term_idx]))
                
        return result