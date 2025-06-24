import pandas as pd

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
# Updated with actual Kavak values
DEFAULT_FEES = {
    'service_fee_pct': 0.04,        # 4% of new car value (BASE VALUE)
    'cxa_pct': 0.04,                # 4% of the new car price (Comisión por Apertura - Opening Fee)
    'cac_bonus': 0,                 # Customer bonus (starts at 0, can go up to MAX_CAC_BONUS)
    'kavak_total_amount': 25000.0,  # Fixed 25,000 MXN every two years
    'insurance_amount': 10999.0,    # Fixed 10,999 MXN (financed over 12 months)
    'gps_installation_fee': 750.0,  # Upfront GPS installation cost (FIXED)
    'gps_monthly_fee': 350.0        # Recurring GPS monitoring fee
}

# The maximum CAC (Customer Bonus) we are willing to apply
MAX_CAC_BONUS = 5000.0 # Example: 5,000 MXN

# Payment Delta Tiers to classify the final offer
PAYMENT_DELTA_TIERS = {
    'Refresh': (-0.05, 0.05),
    'Upgrade': (0.0501, 0.25),
    'Max Upgrade': (0.2501, 1.00) # Cap at 100% increase
}

IVA_RATE = 0.16 # 16% IVA tax

# GPS installation fee applied upfront (subject to IVA)
GPS_INSTALLATION_FEE = 750.0

# Fixed monthly GPS monitoring fee (before IVA)
GPS_MONTHLY_FEE = 350.0

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
