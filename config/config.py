import pandas as pd
from .configuration_manager import get_config, get_interest_rate, get_payment_tiers

# Get configuration manager
_config = get_config()

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
DEFAULT_FEES = {
    'service_fee_pct': float(_config.get_decimal("fees.service.percentage")),
    'cxa_pct': float(_config.get_decimal("fees.cxa.percentage")),
    'cac_bonus': float(_config.get_decimal("fees.cac_bonus.default")),
    'cac_bonus_range': (
        float(_config.get_decimal("fees.cac_bonus.min")),
        float(_config.get_decimal("fees.cac_bonus.max"))
    ),
    'kavak_total_amount': float(_config.get_decimal("fees.kavak_total.amount")),
    'insurance_amount': float(_config.get_decimal("fees.insurance.amount")),
    'insurance_annual': float(_config.get_decimal("fees.insurance.amount")),
    'gps_installation': float(_config.get_decimal("fees.gps.installation")),
    'gps_installation_fee': float(_config.get_decimal("fees.gps.installation")),
    'gps_monthly': float(_config.get_decimal("fees.gps.monthly")),
    'gps_monthly_fee': float(_config.get_decimal("fees.gps.monthly"))
}

# The maximum CAC (Customer Bonus) we are willing to apply
MAX_CAC_BONUS = float(_config.get_decimal("fees.cac_bonus.max"))

# Payment Delta Tiers to classify the final offer
PAYMENT_DELTA_TIERS = get_payment_tiers()

# IVA Rate - loaded from configuration
IVA_RATE = float(_config.get_decimal("financial.iva_rate"))

# GPS fees - loaded from configuration
GPS_INSTALLATION_FEE = float(_config.get_decimal("fees.gps.installation"))
GPS_MONTHLY_FEE = float(_config.get_decimal("fees.gps.monthly"))

# Insurance amount lookup by risk profile. Placeholder values use the default
# insurance amount for all profiles but allow future customization.
INSURANCE_TABLE = {
    profile: DEFAULT_FEES['insurance_amount']
    for profile in [
        'AAA', 'AA', 'A', 'A1', 'A2', 'B', 'C1', 'C2', 'C3', 'D1', 'D2',
        'D3', 'E1', 'E2', 'E3', 'E4', 'E5', 'F1', 'F2', 'F3', 'F4',
        'B_SB', 'C1_SB', 'C2_SB', 'E5_SB', 'Z'
    ]
}
