import pandas as pd
import numpy_financial as npf
from .calculator import calculate_final_npv, solve_for_max_loan
from .config import (
    get_hardcoded_financial_parameters,
    TERM_SEARCH_ORDER,
    DEFAULT_FEES,
    MAX_CAC_BONUS,
    PAYMENT_DELTA_TIERS
)

# Load config tables on import
INTEREST_RATE_TABLE, DOWN_PAYMENT_TABLE = get_hardcoded_financial_parameters()

class TradeUpEngine:
    def __init__(self, config=None):
        self.config = config or {}
        
    def generate_offers(self, customer: dict, inventory: pd.DataFrame):
        """Main entry point for offer generation."""
        return run_engine_for_customer(customer, inventory, self.config)
        
    def update_config(self, new_config: dict):
        """Update engine configuration."""
        self.config.update(new_config)
        
    @property
    def current_config(self):
        """Get current engine configuration."""
        return self.config.copy()

def run_engine_for_customer(customer: dict, inventory: pd.DataFrame, engine_config: dict):
    """
    Main orchestrator function. Generates all possible offers for a single customer.
    Supports: default hierarchical search, custom parameter mode, and range-based optimization.
    """
    print(f"--- Running engine for customer: {customer.get('customer_id')} ---")
    
    try:
        current_monthly_payment = customer['current_monthly_payment']
        # Engine is responsible for interest rate lookup from risk profile
        interest_rate = INTEREST_RATE_TABLE.loc[customer['risk_profile_name']]
    except KeyError as e:
        print(f"Error: Missing key in customer data or invalid risk profile - {e}")
        return pd.DataFrame()

    # Check engine mode
    use_custom_params = engine_config.get('use_custom_params', False)
    use_range_optimization = engine_config.get('use_range_optimization', False)
    
    if use_range_optimization:
        print("🎯 RANGE OPTIMIZATION MODE: Using parameter ranges with NPV filtering...")
        return _run_range_optimization_search(customer, inventory, interest_rate, engine_config, current_monthly_payment)
    elif use_custom_params:
        print("🔧 CUSTOM PARAMETER MODE: Using user-defined configuration...")
        return _run_custom_parameter_search(customer, inventory, interest_rate, engine_config, current_monthly_payment)
    else:
        print("⚙️ DEFAULT MODE: Using hierarchical subsidy search...")
        return _run_default_hierarchical_search(customer, inventory, interest_rate, engine_config, current_monthly_payment)

def _run_default_hierarchical_search(customer, inventory, interest_rate, engine_config, current_monthly_payment):
    """Original hierarchical search with hardcoded subsidy levers and NPV filtering."""
    all_offers = []
    
    # Extract NPV threshold for filtering
    min_npv_threshold = engine_config.get('min_npv_threshold', 5000.0)
    
    # --- PHASE 1: Search with NO Subsidy (Max Profit) ---
    print("PHASE 1: Searching for offers with MAX PROFIT...")
    phase_1_fees = DEFAULT_FEES.copy()
    phase_1_fees['cac_bonus'] = 0  # Ensure no bonus in phase 1
    if not engine_config.get('include_kavak_total', True):
        phase_1_fees['kavak_total_amount'] = 0
    
    print(f"   Using fees: Service={phase_1_fees['service_fee_pct']*100}%, CXA={phase_1_fees['cxa_pct']*100}%, CAC={phase_1_fees['cac_bonus']}")
    
    # Run the ENTIRE Phase 1 search across all terms and cars with NPV filtering
    phase_1_offers = _run_search_phase_with_npv_filter(customer, inventory, interest_rate, phase_1_fees, min_npv_threshold)
    all_offers.extend(phase_1_offers)

    # If Phase 1 found any offers, STOP and return results
    if phase_1_offers:
        print(f"PHASE 1 COMPLETE: Found {len(phase_1_offers)} offers. Stopping search.")
        return _finalize_offers_dataframe(all_offers, current_monthly_payment)

    # --- PHASE 2: Search WITH Subsidy (Concession) - EXHAUSTIVE ---
    print("PHASE 2: No offers found in Phase 1. Running EXHAUSTIVE subsidy search...")
    
    # Level 1: Service Fee = 0
    print("Phase 2 - Level 1: Reducing Service Fee to 0...")
    fees_level_1 = DEFAULT_FEES.copy()
    fees_level_1['service_fee_pct'] = 0
    fees_level_1['cac_bonus'] = 0  # No CAC bonus yet
    if not engine_config.get('include_kavak_total', True):
        fees_level_1['kavak_total_amount'] = 0
    level_1_offers = _run_search_phase_with_npv_filter(customer, inventory, interest_rate, fees_level_1, min_npv_threshold)
    all_offers.extend(level_1_offers)
    
    # Level 2: Service Fee = 0 AND CAC Bonus applied
    print("Phase 2 - Level 2: Adding CAC Bonus...")
    fees_level_2 = fees_level_1.copy()
    fees_level_2['cac_bonus'] = MAX_CAC_BONUS
    level_2_offers = _run_search_phase_with_npv_filter(customer, inventory, interest_rate, fees_level_2, min_npv_threshold)
    all_offers.extend(level_2_offers)
    
    # Level 3: All previous subsidies AND CXA = 0
    print("Phase 2 - Level 3: Reducing CXA to 0...")
    fees_level_3 = fees_level_2.copy()
    fees_level_3['cxa_pct'] = 0
    level_3_offers = _run_search_phase_with_npv_filter(customer, inventory, interest_rate, fees_level_3, min_npv_threshold)
    all_offers.extend(level_3_offers)
    
    print(f"PHASE 2 COMPLETE: Found {len(all_offers)} total offers across all subsidy levels.")
    print(f"NPV filtering applied: Min {min_npv_threshold:,.0f} MXN")
    
    # Remove duplicate offers (same car might be viable at multiple subsidy levels)
    if all_offers:
        offers_df = pd.DataFrame(all_offers)
        offers_df.drop_duplicates(subset=['car_id', 'term'], inplace=True)
        return _finalize_offers_dataframe(offers_df.to_dict(orient='records'), current_monthly_payment)
        
    return pd.DataFrame()

def _run_range_optimization_search(customer, inventory, interest_rate, engine_config, current_monthly_payment):
    """
    Range-based optimization search with extreme granularity and NPV filtering.
    Generates all parameter combinations within specified ranges for maximum flexibility.
    """
    import itertools
    
    all_offers = []
    
    # Extract parameter ranges from config (with defaults)
    service_fee_range = engine_config.get('service_fee_range', (0.0, 5.0))
    cxa_range = engine_config.get('cxa_range', (0.0, 4.0))
    cac_bonus_range = engine_config.get('cac_bonus_range', (0, 10000))
    
    # Extract granularity settings (basis point precision)
    service_fee_step = engine_config.get('service_fee_step', 0.01)  # 1 basis point
    cxa_step = engine_config.get('cxa_step', 0.01)  # 1 basis point
    cac_bonus_step = engine_config.get('cac_bonus_step', 100)  # 100 MXN steps
    
    # Extract NPV filtering threshold
    min_npv_threshold = engine_config.get('min_npv_threshold', 5000.0)
    
    # EARLY STOPPING: Add max combinations limit
    max_combinations_to_test = engine_config.get('max_combinations_to_test', 1000)  # Default: test max 1000 combinations
    early_stop_on_offers = engine_config.get('early_stop_on_offers', 100)  # Stop if we find 100 valid offers
    
    # Generate parameter combinations
    service_fee_values = [round(x, 4) for x in _generate_range(service_fee_range[0], service_fee_range[1], service_fee_step)]
    cxa_values = [round(x, 4) for x in _generate_range(cxa_range[0], cxa_range[1], cxa_step)]
    cac_bonus_values = list(range(int(cac_bonus_range[0]), int(cac_bonus_range[1]) + 1, int(cac_bonus_step)))
    
    print(f"🎯 Parameter ranges:")
    print(f"   Service Fee: {len(service_fee_values)} values from {service_fee_range[0]}% to {service_fee_range[1]}%")
    print(f"   CXA: {len(cxa_values)} values from {cxa_range[0]}% to {cxa_range[1]}%")
    print(f"   CAC Bonus: {len(cac_bonus_values)} values from {cac_bonus_range[0]} to {cac_bonus_range[1]} MXN")
    print(f"   Min NPV Threshold: {min_npv_threshold:,.0f} MXN")
    
    total_combinations = len(service_fee_values) * len(cxa_values) * len(cac_bonus_values)
    print(f"   Total parameter combinations: {total_combinations:,}")
    print(f"   ⚡ EARLY STOPPING: Will test max {max_combinations_to_test} combinations or until {early_stop_on_offers} offers found")
    
    # Override payment delta tiers if provided
    global PAYMENT_DELTA_TIERS
    original_tiers = PAYMENT_DELTA_TIERS.copy()
    
    if 'payment_delta_tiers' in engine_config:
        custom_tiers = engine_config['payment_delta_tiers']
        PAYMENT_DELTA_TIERS = {
            'Refresh': tuple(custom_tiers.get('refresh', original_tiers['Refresh'])),
            'Upgrade': tuple(custom_tiers.get('upgrade', original_tiers['Upgrade'])),
            'Max Upgrade': tuple(custom_tiers.get('max_upgrade', original_tiers['Max Upgrade']))
        }
        print(f"🎯 Using custom payment tiers: {PAYMENT_DELTA_TIERS}")
    
    # Search through all parameter combinations
    valid_offers_count = 0
    npv_filtered_count = 0
    combinations_tested = 0
    
    # EARLY STOPPING: Create parameter iterator for controlled iteration
    param_iterator = itertools.product(service_fee_values, cxa_values, cac_bonus_values)
    
    for service_fee_pct, cxa_pct, cac_bonus in param_iterator:
        combinations_tested += 1
        
        # Build fee configuration for this combination
        fees_config = {
            'service_fee_pct': service_fee_pct / 100,  # Convert percentage to decimal
            'cxa_pct': cxa_pct / 100,  # Convert percentage to decimal
            'cac_bonus': cac_bonus,
            'kavak_total_amount': DEFAULT_FEES['kavak_total_amount'] if engine_config.get('include_kavak_total', True) else 0,
            'insurance_amount': engine_config.get('insurance_amount', DEFAULT_FEES['insurance_amount']),
            'fixed_fee': engine_config.get('gps_fee', DEFAULT_FEES['fixed_fee'])
        }
        
        # Run search phase with this parameter combination
        combo_offers = _run_search_phase_with_npv_filter(
            customer, inventory, interest_rate, fees_config, min_npv_threshold
        )
        
        for offer in combo_offers:
            # Add parameter metadata to each offer
            offer['parameter_combination'] = {
                'service_fee_pct': service_fee_pct,
                'cxa_pct': cxa_pct,
                'cac_bonus': cac_bonus
            }
            valid_offers_count += 1
        
        all_offers.extend(combo_offers)
        
        # EARLY STOPPING CONDITIONS
        if combinations_tested >= max_combinations_to_test:
            print(f"   ⚡ Early stopping: Reached max combinations limit ({max_combinations_to_test})")
            break
            
        if valid_offers_count >= early_stop_on_offers:
            print(f"   ⚡ Early stopping: Found enough offers ({valid_offers_count} >= {early_stop_on_offers})")
            break
    
    # Restore original tiers
    PAYMENT_DELTA_TIERS = original_tiers
    
    print(f"🎯 RANGE OPTIMIZATION COMPLETE:")
    print(f"   Combinations tested: {combinations_tested}/{total_combinations}")
    print(f"   Valid offers found: {valid_offers_count:,}")
    print(f"   NPV filtering applied: Min {min_npv_threshold:,.0f} MXN")
    
    if all_offers:
        # Remove duplicates and rank by NPV within tiers
        return _finalize_optimized_offers_dataframe(all_offers, current_monthly_payment, engine_config)
    
    return pd.DataFrame()

def _run_custom_parameter_search(customer, inventory, interest_rate, engine_config, current_monthly_payment):
    """Custom parameter mode using user-defined fee structure."""
    all_offers = []
    
    # Build custom fee structure from engine_config
    custom_fees = {
        'service_fee_pct': engine_config.get('service_fee_pct', DEFAULT_FEES['service_fee_pct']),
        'cxa_pct': engine_config.get('cxa_pct', DEFAULT_FEES['cxa_pct']),
        'cac_bonus': engine_config.get('cac_bonus', DEFAULT_FEES['cac_bonus']),
        'kavak_total_amount': DEFAULT_FEES['kavak_total_amount'] if engine_config.get('include_kavak_total', True) else 0,
        'insurance_amount': engine_config.get('insurance_amount', DEFAULT_FEES['insurance_amount']),
        'fixed_fee': engine_config.get('gps_fee', DEFAULT_FEES['fixed_fee'])
    }
    
    print(f"🔧 Using custom fees: {custom_fees}")
    
    # Override payment delta tiers if provided
    global PAYMENT_DELTA_TIERS
    original_tiers = PAYMENT_DELTA_TIERS.copy()
    
    if 'payment_delta_tiers' in engine_config:
        custom_tiers = engine_config['payment_delta_tiers']
        PAYMENT_DELTA_TIERS = {
            'Refresh': tuple(custom_tiers.get('refresh', original_tiers['Refresh'])),
            'Upgrade': tuple(custom_tiers.get('upgrade', original_tiers['Upgrade'])),
            'Max Upgrade': tuple(custom_tiers.get('max_upgrade', original_tiers['Max Upgrade']))
        }
        print(f"🎯 Using custom payment tiers: {PAYMENT_DELTA_TIERS}")
    
    # Extract NPV threshold for filtering
    min_npv_threshold = engine_config.get('min_npv_threshold', 5000.0)
    
    # Run single search phase with custom parameters and NPV filtering
    custom_offers = _run_search_phase_with_npv_filter(customer, inventory, interest_rate, custom_fees, min_npv_threshold)
    all_offers.extend(custom_offers)
    
    # Restore original tiers
    PAYMENT_DELTA_TIERS = original_tiers
    
    print(f"🔧 CUSTOM SEARCH COMPLETE: Found {len(all_offers)} offers with custom parameters.")
    
    if all_offers:
        return _finalize_offers_dataframe(all_offers, current_monthly_payment)
    
    return pd.DataFrame()


def _run_search_phase(customer, inventory, interest_rate, fees_config):
    """Helper function to run the search for a given fee configuration."""
    found_offers = []
    for car_index, car in inventory.iterrows():
        for term in TERM_SEARCH_ORDER:
            offer = _generate_single_offer(customer, car, term, interest_rate, fees_config)
            if offer:
                found_offers.append(offer)
    return found_offers


def _generate_single_offer(customer, car, term, interest_rate, fees_config):
    """
    Rigorous calculation for a single car/term/fee combination using bottom-up validation.
    FIXED: CXA calculated correctly as percentage of loan amount using algebraic solution.
    """
    # 1. Hard Filter: Price must be higher
    if car['sales_price'] <= customer['current_car_price']:
        return None

    # 2. Solve circular dependency algebraically
    # The Problem: 
    #   loan_amount = car_price - effective_equity
    #   effective_equity = vehicle_equity + cac_bonus - cxa_amount  
    #   cxa_amount = loan_amount * cxa_pct
    #
    # The Solution:
    #   loan_amount = (car_price - vehicle_equity - cac_bonus) / (1 - cxa_pct)
    
    cxa_pct = fees_config.get('cxa_pct', 0)
    cac_bonus = fees_config.get('cac_bonus', 0)
    
    # Calculate loan amount using algebraic solution
    denominator = 1 - cxa_pct
    if denominator <= 0:
        return None  # Invalid: CXA percentage >= 100%
    
    loan_amount_needed = (car['sales_price'] - customer['vehicle_equity'] - cac_bonus) / denominator
    
    if loan_amount_needed <= 0:
        return None

    # 3. Now calculate CXA amount correctly (percentage of loan amount)
    cxa_amount = loan_amount_needed * cxa_pct
    
    # 4. Calculate effective equity for validation
    effective_equity = customer['vehicle_equity'] + cac_bonus - cxa_amount

    # 5. Down Payment Check
    required_dp_pct = DOWN_PAYMENT_TABLE.loc[customer['risk_profile_index'], term]
    if effective_equity < car['sales_price'] * required_dp_pct:
        return None

    # 6. Calculate the actual monthly payment for this specific loan amount - BOTTOM-UP
    actual_monthly_payment = _calculate_forward_payment(loan_amount_needed, interest_rate, term, fees_config, car['sales_price'])
    
    # 7. Validate if this payment falls within any valid Payment Delta tier - DIRECT VALIDATION
    payment_delta = (actual_monthly_payment / customer['current_monthly_payment']) - 1
    valid_tier = False
    for tier, (min_d, max_d) in PAYMENT_DELTA_TIERS.items():
        if min_d <= payment_delta <= max_d:
            valid_tier = True
            break
    
    if not valid_tier:
        return None  # Payment delta is outside acceptable ranges
    
    # 8. SUCCESS! Build the final offer dictionary
    offer_data = {
        'car_id': car['car_id'],
        'car_model': car['model'],
        'new_car_price': car['sales_price'],
        'term': term,
        'monthly_payment': actual_monthly_payment,
        'payment_delta': payment_delta,
        'loan_amount': loan_amount_needed,
        'effective_equity': effective_equity,
        'cxa_amount': cxa_amount,
        'npv': calculate_final_npv(loan_amount_needed, interest_rate, term),
        'fees_applied': fees_config,
        'interest_rate': interest_rate
    }
    return offer_data

def _calculate_forward_payment(loan_amount, interest_rate, term, fees_config, car_price):
    """
    A precise forward payment calculator that matches the solver's logic.
    """
    tasa_mensual_sin_iva = interest_rate / 12
    tasa_mensual_con_iva = tasa_mensual_sin_iva * 1.16
    
    # Calculate financed amounts
    valor_kt = fees_config.get('kavak_total_amount', 0)
    valor_seguro = fees_config.get('insurance_amount', 0)
    valor_service_fee = car_price * fees_config.get('service_fee_pct', 0)
    
    # We sum up the individual PMT of each financed component
    total_payment = npf.pmt(tasa_mensual_con_iva, term, -loan_amount)
    
    # Service fee financed over the full loan term
    if valor_service_fee > 0:
        total_payment += npf.pmt(tasa_mensual_con_iva, term, -valor_service_fee)
    
    # Kavak Total financed over the full loan term
    if valor_kt > 0:
        total_payment += npf.pmt(tasa_mensual_con_iva, term, -valor_kt)
    
    # Insurance financed over 12 months
    if valor_seguro > 0:
        total_payment += npf.pmt(tasa_mensual_con_iva, 12, -valor_seguro)
        
    # Fixed fee (GPS) with IVA, spread over term
    total_payment += (fees_config.get('fixed_fee', 0) * 1.16) / term

    return total_payment

def _generate_range(start, end, step):
    """Generate a range of values with specified step size, handling floating point precision."""
    import numpy as np
    return np.arange(start, end + step, step)

def _run_search_phase_with_npv_filter(customer, inventory, interest_rate, fees_config, min_npv_threshold):
    """Helper function to run search with NPV filtering applied."""
    found_offers = []
    for car_index, car in inventory.iterrows():
        for term in TERM_SEARCH_ORDER:
            offer = _generate_single_offer(customer, car, term, interest_rate, fees_config)
            if offer and offer['npv'] >= min_npv_threshold:  # Apply NPV filter
                found_offers.append(offer)
    return found_offers

def _finalize_optimized_offers_dataframe(offers_list, current_monthly_payment, engine_config):
    """
    Advanced finalization for range optimization with NPV-based ranking within tiers.
    """
    if not offers_list:
        return pd.DataFrame()

    df = pd.DataFrame(offers_list)
    df['payment_delta'] = (df['monthly_payment'] / current_monthly_payment) - 1

    def assign_tier(delta):
        for tier, (min_d, max_d) in PAYMENT_DELTA_TIERS.items():
            if min_d <= delta <= max_d:
                return tier
        return 'N/A'
        
    df['tier'] = df['payment_delta'].apply(assign_tier)
    # Filter out any offers that might have fallen out of bounds after precise calculation
    df = df[df['tier'] != 'N/A']
    
    # Remove duplicates: keep the offer with highest NPV for each car/term combination
    df = df.sort_values('npv', ascending=False).drop_duplicates(subset=['car_id', 'term'], keep='first')
    
    # Rank offers within each tier by NPV (descending)
    df['npv_rank_within_tier'] = df.groupby('tier')['npv'].rank(method='dense', ascending=False)
    
    # Limit offers per tier if specified
    max_offers_per_tier = engine_config.get('max_offers_per_tier', 50)  # Default: top 50 per tier
    df = df.groupby('tier').head(max_offers_per_tier).reset_index(drop=True)
    
    # Sort by tier preference (Refresh > Upgrade > Max Upgrade) then by NPV within tier
    tier_order = {'Refresh': 1, 'Upgrade': 2, 'Max Upgrade': 3}
    df['tier_priority'] = df['tier'].map(tier_order)
    df = df.sort_values(['tier_priority', 'npv'], ascending=[True, False])
    
    return df

def _finalize_offers_dataframe(offers_list, current_monthly_payment):
    """Helper to convert list of offer dicts to a final DataFrame with tiers."""
    if not offers_list:
        return pd.DataFrame()

    df = pd.DataFrame(offers_list)
    df['payment_delta'] = (df['monthly_payment'] / current_monthly_payment) - 1

    def assign_tier(delta):
        for tier, (min_d, max_d) in PAYMENT_DELTA_TIERS.items():
            if min_d <= delta <= max_d:
                return tier
        return 'N/A'
        
    df['tier'] = df['payment_delta'].apply(assign_tier)
    # Filter out any offers that might have fallen out of bounds after precise calculation
    df = df[df['tier'] != 'N/A']
    return df
