import pandas as pd
import logging

# Use facade for configuration
from .facade import (
    get_decimal, 
    get_payment_tiers, 
    get_interest_rate,
    ConfigProxy
)

logger = logging.getLogger(__name__)

# Use ConfigProxy instead of duplicate wrapper
_config = ConfigProxy()

# --- Hardcoded Financial Parameters ---

def get_hardcoded_financial_parameters():
    """
    Returns the core financial configuration tables as pandas DataFrames.
    This replaces reading from external files for the MVP.
    """
    
    # Interest Rate Table: A simple Series mapping profile name to annual rate.
    tasa_data = {
        'AAA': 0.1949, 'AA': 0.1949, 'A': 0.1949, 'A1': 0.1949,
        'A2': 0.2099, 'B': 0.2249, 'C1': 0.2299, 'C2': 0.2349,
        'C3': 0.2549, 'D1': 0.2949, 'D2': 0.3249, 'D3': 0.3249,
        'E1': 0.2399, 'E2': 0.31, 'E3': 0.3399, 'E4': 0.3649,
        'E5': 0.4399, 'F1': 0.3649, 'F2': 0.3899, 'F3': 0.4149,
        'F4': 0.4399, 'B_SB': 0.2349, 'C1_SB': 0.2449, 'C2_SB': 0.27,
        'E5_SB': 0.4399, 'Z': 0.4399
    }
    tasa_por_perfil_series = pd.Series(tasa_data, name='Tasa')
    tasa_por_perfil_series.index.name = 'Perfil de riesgo'

    # Down Payment Table: A DataFrame mapping profile index and term to required down payment %.
    enganche_data = [
        [0.3,0.3,0.3,0.3,0.3,0.3], [0.25,0.25,0.25,0.25,0.25,0.25],
        [0.2,0.2,0.2,0.2,0.2,0.2], [0.15,0.15,0.15,0.15,0.15,0.15],
        [0.15,0.15,0.15,0.15,0.15,0.15], [0.2,0.2,0.2,0.2,0.2,0.2],
        [0.2,0.2,0.2,0.2,0.2,0.2], [0.2,0.2,0.2,0.2,0.2,0.2],
        [0.2,0.2,0.2,0.2,0.2,0.2], [0.2,0.2,0.2,0.2,0.2,0.2],
        [0.25,0.25,0.25,0.25,0.25,0.25], [0.3,0.3,0.3,0.3,0.3,0.3],
        [0.35,0.35,0.35,0.35,0.35,0.35], [0.35,0.35,0.35,0.35,0.35,0.35],
        [0.35,0.35,0.35,0.35,0.35,0.35], [0.35,0.35,0.35,0.35,0.35,0.35],
        [0.75,0.75,0.75,0.75,0.75,0.75], [0.35,0.35,0.35,0.35,0.35,0.35],
        [0.35,0.35,0.35,0.35,0.35,0.35], [0.35,0.35,0.35,0.35,0.35,0.35],
        [0.75,0.75,0.75,0.75,0.75,0.75], [0.25,0.25,0.25,0.25,0.25,0.25],
        [0.3,0.3,0.3,0.3,0.3,0.3], [0.3,0.3,0.3,0.3,0.3,0.3],
        [0.75,0.75,0.75,0.75,0.75,0.75], [0.9999,0.9999,0.9999,0.9999,0.9999,0.9999]
    ]
    enganche_por_perfil_df = pd.DataFrame(enganche_data, columns=[12, 24, 36, 48, 60, 72])
    enganche_por_perfil_df.index.name = 'Perfil Row Index'

    return tasa_por_perfil_series, enganche_por_perfil_df


# --- Engine Business Logic Rules ---

# The specific order in which loan terms will be tested
TERM_SEARCH_ORDER = [60, 72, 48, 36, 24, 12]


def get_term_search_order(priority: str) -> list[int]:
    """Return loan term order based on priority setting."""
    if priority == "ascending":
        return sorted(TERM_SEARCH_ORDER)
    if priority == "descending":
        return sorted(TERM_SEARCH_ORDER, reverse=True)
    return TERM_SEARCH_ORDER

# The default fee structure (Max Profit scenario)
# These are now loaded from configuration but kept for backward compatibility
# SAFETY: All config loads wrapped with try/catch and defaults to prevent startup crashes
def _safe_get_decimal(key: str, default: float) -> float:
    """Safely get decimal config value with fallback"""
    try:
        value = _config.get_decimal(key)
        if value is None:
            logger.warning(f"Config key '{key}' returned None, using default: {default}")
            return default
        return float(value)
    except Exception as e:
        logger.error(f"Failed to load config '{key}': {e}, using default: {default}")
        return default

# DEFAULT_FEES dictionary is dynamically loaded from configuration
# Use config.facade.get_decimal() directly for individual values
DEFAULT_FEES = {
    'service_fee_pct': _safe_get_decimal("fees.service.percentage", 0.04),
    'cxa_pct': _safe_get_decimal("fees.cxa.percentage", 0.04),
    'cac_bonus': _safe_get_decimal("fees.cac_bonus.default", 0.0),
    'cac_bonus_range': (
        _safe_get_decimal("fees.cac_bonus.min", 0.0),
        _safe_get_decimal("fees.cac_bonus.max", 5000.0)
    ),
    'kavak_total_amount': _safe_get_decimal("fees.kavak_total.amount", 25000.0),
    'insurance_amount': _safe_get_decimal("fees.insurance.amount", 10999.0),
    'insurance_annual': _safe_get_decimal("fees.insurance.amount", 10999.0),
    'gps_installation': _safe_get_decimal("fees.gps.installation", 750.0),
    'gps_installation_fee': _safe_get_decimal("fees.gps.installation", 750.0),
    'gps_monthly': _safe_get_decimal("fees.gps.monthly", 350.0),
    'gps_monthly_fee': _safe_get_decimal("fees.gps.monthly", 350.0)
}

# The maximum CAC (Customer Bonus) - loaded from configuration
MAX_CAC_BONUS = _safe_get_decimal("fees.cac_bonus.max", 5000.0)

# Payment Delta Tiers to classify the final offer
try:
    PAYMENT_DELTA_TIERS = get_payment_tiers()
except Exception as e:
    logger.error(f"Failed to load payment tiers: {e}, using defaults")
    PAYMENT_DELTA_TIERS = {
        'refresh': {'min': -0.05, 'max': 0.05},
        'upgrade': {'min': 0.05, 'max': 0.25},
        'max_upgrade': {'min': 0.25, 'max': 1.0}
    }

# IVA Rate - loaded from configuration
IVA_RATE = _safe_get_decimal("financial.iva_rate", 0.16)

# GPS fees - dynamically loaded from configuration
# These are kept for backward compatibility but should use config.facade directly
GPS_INSTALLATION_FEE = _safe_get_decimal("fees.gps.installation", 750.0)
GPS_MONTHLY_FEE = _safe_get_decimal("fees.gps.monthly", 350.0)

# Insurance amount lookup by risk profile.
# Using configuration facade to get risk-based amounts
from config.facade import ConfigProxy
_config = ConfigProxy()

INSURANCE_TABLE = {}
# A profiles
for profile in ['AAA', 'AA', 'A', 'A1', 'A2']:
    INSURANCE_TABLE[profile] = float(_config.get_decimal("insurance.amount_a", 10999))
# B profiles  
for profile in ['B', 'B_SB']:
    INSURANCE_TABLE[profile] = float(_config.get_decimal("insurance.amount_b", 13799))
# C profiles
for profile in ['C1', 'C2', 'C3', 'C1_SB', 'C2_SB']:
    INSURANCE_TABLE[profile] = float(_config.get_decimal("insurance.amount_c", 15599))
# Default for all other profiles
for profile in ['D1', 'D2', 'D3', 'E1', 'E2', 'E3', 'E4', 'E5', 'E5_SB', 'F1', 'F2', 'F3', 'F4', 'Z']:
    INSURANCE_TABLE[profile] = float(_config.get_decimal("insurance.amount_default", 10999))
