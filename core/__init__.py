"""
Kavak Trade-Up Engine Core Module
Contains the main business logic for trade-up calculations
"""

from .engine import run_engine_for_customer
from .calculator import calculate_final_npv
from .config import *

# Data loader can introduce circular imports in certain environments.
# Import lazily when available and ignore failures.
try:
    from .data_loader import data_loader  # type: ignore
except Exception:
    data_loader = None

__all__ = ['run_engine_for_customer', 'calculate_final_npv', 'data_loader']
