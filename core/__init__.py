"""
Kavak Trade-Up Engine Core Module
Contains the main business logic for trade-up calculations
"""

from .engine import run_engine_for_customer
from .calculator import calculate_final_npv
# Attempt to import heavy Redshift-connected loader; gracefully skip if dependencies missing
try:
    from .data_loader import data_loader
except ModuleNotFoundError as e:
    # Common in local/mock environments where redshift_connector isn't installed or supported
    data_loader = None
from .config import *

__all__ = ['run_engine_for_customer', 'calculate_final_npv', 'data_loader']
