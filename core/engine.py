import pandas as pd
import numpy_financial as npf
from abc import ABC, abstractmethod
import logging
from scipy.optimize import differential_evolution
from core.logging_config import setup_logging
from .calculator import calculate_final_npv
from .config import (
    get_hardcoded_financial_parameters,
    TERM_SEARCH_ORDER,
    get_term_search_order,
    DEFAULT_FEES,
    MAX_CAC_BONUS,
    PAYMENT_DELTA_TIERS,
    IVA_RATE,
    GPS_INSTALLATION_FEE,
    INSURANCE_TABLE,
    GPS_MONTHLY_FEE,
)

# Load config tables on import
INTEREST_RATE_TABLE, DOWN_PAYMENT_TABLE = get_hardcoded_financial_parameters()

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


class SearchStrategy(ABC):
    """Abstract base class for offer search strategies."""

    @staticmethod
    def _payment_delta_tiers(engine_config):
        if "payment_delta_tiers" in engine_config:
            custom_tiers = engine_config["payment_delta_tiers"]
            tiers = {
                "Refresh": tuple(
                    custom_tiers.get("refresh", PAYMENT_DELTA_TIERS["Refresh"])
                ),
                "Upgrade": tuple(
                    custom_tiers.get("upgrade", PAYMENT_DELTA_TIERS["Upgrade"])
                ),
                "Max Upgrade": tuple(
                    custom_tiers.get(
                        "max_upgrade", PAYMENT_DELTA_TIERS["Max Upgrade"]
                    )
                ),
            }
            logger.info(f"🎯 Using custom payment tiers: {tiers}")
            return tiers
        return PAYMENT_DELTA_TIERS

    def run(self, customer, inventory, interest_rate, engine_config):
        try:
            current_payment = customer["current_monthly_payment"]
        except KeyError as e:
            logger.error(f"Error: Missing key in customer data - {e}")
            return pd.DataFrame()

        tiers = self._payment_delta_tiers(engine_config)
        return self._execute(
            customer,
            inventory,
            interest_rate,
            engine_config,
            current_payment,
            tiers,
        )

    @abstractmethod
    def _execute(
        self,
        customer,
        inventory,
        interest_rate,
        engine_config,
        current_monthly_payment,
        payment_delta_tiers,
    ):
        """Run the search strategy."""
        raise NotImplementedError


class HierarchicalSearchStrategy(SearchStrategy):
    def _execute(
        self,
        customer,
        inventory,
        interest_rate,
        engine_config,
        current_monthly_payment,
        payment_delta_tiers,
    ):
        return _run_default_hierarchical_search(
            customer,
            inventory,
            interest_rate,
            engine_config,
            current_monthly_payment,
            payment_delta_tiers,
        )


class CustomParameterSearchStrategy(SearchStrategy):
    def _execute(
        self,
        customer,
        inventory,
        interest_rate,
        engine_config,
        current_monthly_payment,
        payment_delta_tiers,
    ):
        return _run_custom_parameter_search(
            customer,
            inventory,
            interest_rate,
            engine_config,
            current_monthly_payment,
            payment_delta_tiers,
        )


class RangeOptimizationSearchStrategy(SearchStrategy):
    def _execute(
        self,
        customer,
        inventory,
        interest_rate,
        engine_config,
        current_monthly_payment,
        payment_delta_tiers,
    ):
        return _run_range_optimization_search(
            customer,
            inventory,
            interest_rate,
            engine_config,
            current_monthly_payment,
            payment_delta_tiers,
        )


class TradeUpEngine:
    def __init__(self, config=None):
        self.config = config or {}

    def generate_offers(self, customer: dict, inventory: pd.DataFrame):
        """Main entry point for offer generation."""
        try:
            interest_rate = INTEREST_RATE_TABLE.loc[customer["risk_profile_name"]]
        except KeyError as e:
            logger.error(f"Error: Missing key in customer data or invalid risk profile - {e}")
            return pd.DataFrame()

        if self.config.get("use_range_optimization", False):
            strategy = RangeOptimizationSearchStrategy()
        elif self.config.get("use_custom_params", False):
            strategy = CustomParameterSearchStrategy()
        else:
            strategy = HierarchicalSearchStrategy()

        return strategy.run(customer, inventory, interest_rate, self.config)

    def update_config(self, new_config: dict):
        """Update engine configuration."""
        self.config.update(new_config)

    @property
    def current_config(self):
        """Get current engine configuration."""
        return self.config.copy()


def run_engine_for_customer(
    customer: dict, inventory: pd.DataFrame, engine_config: dict
):
    """
    Main orchestrator function. Generates all possible offers for a single customer.
    Supports: default hierarchical search, custom parameter mode, and range-based optimization.
    """
    logger.info(f"--- Running engine for customer: {customer.get('customer_id')} ---")

    try:
        interest_rate = INTEREST_RATE_TABLE.loc[customer["risk_profile_name"]]
    except KeyError as e:
        logger.error(f"Error: Missing key in customer data or invalid risk profile - {e}")
        return pd.DataFrame()

    if engine_config.get("use_range_optimization", False):
        strategy = RangeOptimizationSearchStrategy()
    elif engine_config.get("use_custom_params", False):
        strategy = CustomParameterSearchStrategy()
    else:
        strategy = HierarchicalSearchStrategy()

    return strategy.run(customer, inventory, interest_rate, engine_config)


def _run_default_hierarchical_search(
    customer,
    inventory,
    interest_rate,
    engine_config,
    current_monthly_payment,
    payment_delta_tiers,
):
    """Search for offers using the fixed concession hierarchy described in the
    business rules.

    Parameters
    ----------
    customer : dict
        Customer data used to determine affordability and risk profile.
    inventory : pandas.DataFrame
        List of cars to evaluate as potential upgrades.
    interest_rate : float
        Base annual rate derived from ``INTEREST_RATE_TABLE``.
    engine_config : dict
        Current engine settings controlling fees and thresholds.
    current_monthly_payment : float
        Customer's existing monthly loan payment.
    payment_delta_tiers : dict
        Mapping of tier names to allowed payment delta ranges.

    Returns
    -------
    pandas.DataFrame
        Ranked offers for the customer or an empty frame if none pass the
        checks.

    Notes
    -----
    The function implements the two-phased hierarchy outlined in
    ``docs/project-charter.md`` section 4.2. Phase 1 keeps all fees at their
    maximum. Phase 2 gradually removes service fee, adds CAC bonus and finally
    reduces CXA, filtering each step by Net Present Value (NPV).
    """

    # Extract NPV threshold for filtering
    min_npv_threshold = engine_config.get("min_npv_threshold", 5000.0)
    term_order = get_term_search_order(engine_config.get("term_priority", "standard"))

    # --- PHASE 1: Search with NO Subsidy (Max Profit) ---
    logger.info("PHASE 1: Searching for offers with MAX PROFIT...")
    phase_1_fees = DEFAULT_FEES.copy()
    phase_1_fees["cac_bonus"] = 0  # Ensure no bonus in phase 1
    if not engine_config.get("include_kavak_total", True):
        phase_1_fees["kavak_total_amount"] = 0

    logger.info(
        f"   Using fees: Service={phase_1_fees['service_fee_pct']*100}%, CXA={phase_1_fees['cxa_pct']*100}%, CAC={phase_1_fees['cac_bonus']}"
    )

    phase_1_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        phase_1_fees,
        min_npv_threshold,
        payment_delta_tiers,
        term_order,
    )

    if phase_1_offers:
        logger.info(f"PHASE 1 COMPLETE: Found {len(phase_1_offers)} offers. Stopping search.")
        return _finalize_offers_dataframe(
            phase_1_offers, current_monthly_payment, payment_delta_tiers
        )

    # --- PHASE 2: Search WITH Subsidy (Concession) - EXHAUSTIVE ---
    logger.info("PHASE 2: No offers found in Phase 1. Running EXHAUSTIVE subsidy search...")

    # Level 1: Service Fee = 0
    logger.info("Phase 2 - Level 1: Reducing Service Fee to 0...")
    fees_level_1 = DEFAULT_FEES.copy()
    fees_level_1["service_fee_pct"] = 0
    fees_level_1["cac_bonus"] = 0
    if not engine_config.get("include_kavak_total", True):
        fees_level_1["kavak_total_amount"] = 0
    level_1_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        fees_level_1,
        min_npv_threshold,
        payment_delta_tiers,
        term_order,
    )
    if level_1_offers:
        logger.info(f"Level 1 COMPLETE: Found {len(level_1_offers)} offers. Stopping search.")
        return _finalize_offers_dataframe(
            level_1_offers, current_monthly_payment, payment_delta_tiers
        )

    # Level 2: Service Fee = 0 AND CAC Bonus applied
    logger.info("Phase 2 - Level 2: Adding CAC Bonus...")
    fees_level_2 = fees_level_1.copy()
    fees_level_2["cac_bonus"] = MAX_CAC_BONUS
    level_2_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        fees_level_2,
        min_npv_threshold,
        payment_delta_tiers,
        term_order,
    )
    if level_2_offers:
        logger.info(f"Level 2 COMPLETE: Found {len(level_2_offers)} offers. Stopping search.")
        return _finalize_offers_dataframe(
            level_2_offers, current_monthly_payment, payment_delta_tiers
        )

    # Level 3: All previous subsidies AND CXA = 0
    logger.info("Phase 2 - Level 3: Reducing CXA to 0...")
    fees_level_3 = fees_level_2.copy()
    fees_level_3["cxa_pct"] = 0
    level_3_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        fees_level_3,
        min_npv_threshold,
        payment_delta_tiers,
        term_order,
    )
    if level_3_offers:
        logger.info(f"Level 3 COMPLETE: Found {len(level_3_offers)} offers. Stopping search.")
        return _finalize_offers_dataframe(
            level_3_offers, current_monthly_payment, payment_delta_tiers
        )

    logger.info("PHASE 2 COMPLETE: No valid offers found in any subsidy level.")
    logger.info(f"NPV filtering applied: Min {min_npv_threshold:,.0f} MXN")

    return pd.DataFrame()


def _run_range_optimization_search(
    customer,
    inventory,
    interest_rate,
    engine_config,
    current_monthly_payment,
    payment_delta_tiers,
):
    """Evaluate fee combinations within configured ranges.

    Parameters
    ----------
    customer : dict
        Customer record for which offers will be generated.
    inventory : pandas.DataFrame
        Inventory of vehicles to test.
    interest_rate : float
        Base annual interest rate based on risk profile.
    engine_config : dict
        Engine settings defining range bounds and steps.
    current_monthly_payment : float
        Customer's current payment used to compute payment deltas.
    payment_delta_tiers : dict
        Mapping of tier names to allowed payment delta ranges.

    Returns
    -------
    pandas.DataFrame
        DataFrame of ranked offers meeting the NPV threshold.

    Notes
    -----
    The search iterates over ``service_fee_pct``, ``cxa_pct`` and ``cac_bonus``
    values using the ranges from ``engine_config``. For each combination the
    engine calculates offers and filters them by NPV.  Early stopping parameters
    limit the number of combinations tested, as described in
    ``docs/range_optimization.md``.
    """
    search_method = engine_config.get("range_search_method", "exhaustive").lower()
    if search_method == "smart":
        return _run_smart_range_search(
            customer,
            inventory,
            interest_rate,
            engine_config,
            current_monthly_payment,
            payment_delta_tiers,
        )

    import itertools

    all_offers = []

    # Extract parameter ranges from config (with defaults)
    service_fee_range = engine_config.get("service_fee_range", (0.0, 5.0))
    cxa_range = engine_config.get("cxa_range", (0.0, 4.0))
    cac_bonus_range = engine_config.get("cac_bonus_range", (0, 10000))

    # Extract granularity settings (basis point precision)
    service_fee_step = engine_config.get("service_fee_step", 0.01)  # 1 basis point
    cxa_step = engine_config.get("cxa_step", 0.01)  # 1 basis point
    cac_bonus_step = engine_config.get("cac_bonus_step", 100)  # 100 MXN steps

    # Extract NPV filtering threshold
    min_npv_threshold = engine_config.get("min_npv_threshold", 5000.0)
    term_order = get_term_search_order(engine_config.get("term_priority", "standard"))

    # EARLY STOPPING: Add max combinations limit
    max_combinations_to_test = engine_config.get(
        "max_combinations_to_test", 1000
    )  # Default: test max 1000 combinations
    early_stop_on_offers = engine_config.get(
        "early_stop_on_offers", 100
    )  # Stop if we find 100 valid offers

    # Validate ranges
    _validate_range(service_fee_range, service_fee_step, "service_fee_range")
    _validate_range(cxa_range, cxa_step, "cxa_range")
    _validate_range(cac_bonus_range, cac_bonus_step, "cac_bonus_range")

    # Generate parameter combinations
    service_fee_values = [
        round(x, 4)
        for x in _generate_range(
            service_fee_range[0], service_fee_range[1], service_fee_step
        )
    ]
    cxa_values = [
        round(x, 4) for x in _generate_range(cxa_range[0], cxa_range[1], cxa_step)
    ]
    cac_bonus_values = list(
        range(int(cac_bonus_range[0]), int(cac_bonus_range[1]) + 1, int(cac_bonus_step))
    )

    logger.info(f"🎯 Parameter ranges:")
    logger.info(
        f"   Service Fee: {len(service_fee_values)} values from {service_fee_range[0]}% to {service_fee_range[1]}%"
    )
    logger.info(f"   CXA: {len(cxa_values)} values from {cxa_range[0]}% to {cxa_range[1]}%")
    logger.info(
        f"   CAC Bonus: {len(cac_bonus_values)} values from {cac_bonus_range[0]} to {cac_bonus_range[1]} MXN"
    )
    logger.info(f"   Min NPV Threshold: {min_npv_threshold:,.0f} MXN")

    total_combinations = (
        len(service_fee_values) * len(cxa_values) * len(cac_bonus_values)
    )
    logger.info(f"   Total parameter combinations: {total_combinations:,}")
    logger.info(
        f"   ⚡ EARLY STOPPING: Will test max {max_combinations_to_test} combinations or until {early_stop_on_offers} offers found"
    )

    # Use provided payment delta tiers
    tiers = payment_delta_tiers

    # Search through all parameter combinations
    valid_offers_count = 0
    combinations_tested = 0

    # EARLY STOPPING: Create parameter iterator for controlled iteration
    param_iterator = itertools.product(service_fee_values, cxa_values, cac_bonus_values)

    for service_fee_pct, cxa_pct, cac_bonus in param_iterator:
        combinations_tested += 1

        # Build fee configuration for this combination
        fees_config = {
            "service_fee_pct": service_fee_pct / 100,  # Convert percentage to decimal
            "cxa_pct": cxa_pct / 100,  # Convert percentage to decimal
            "cac_bonus": cac_bonus,
            "kavak_total_amount": (
                DEFAULT_FEES["kavak_total_amount"]
                if engine_config.get("include_kavak_total", True)
                else 0
            ),
            "insurance_amount": engine_config.get(
                "insurance_amount", DEFAULT_FEES["insurance_amount"]
            ),
            "gps_installation_fee": engine_config.get(
                "gps_installation_fee", DEFAULT_FEES["gps_installation_fee"]
            ),
            "gps_monthly_fee": engine_config.get(
                "gps_monthly_fee", DEFAULT_FEES["gps_monthly_fee"]
            ),
        }

        # Run search phase with this parameter combination
        combo_offers = _run_search_phase_with_npv_filter(
            customer,
            inventory,
            interest_rate,
            fees_config,
            min_npv_threshold,
            tiers,
            term_order,
        )

        for offer in combo_offers:
            # Add parameter metadata to each offer
            offer["parameter_combination"] = {
                "service_fee_pct": service_fee_pct,
                "cxa_pct": cxa_pct,
                "cac_bonus": cac_bonus,
            }
            valid_offers_count += 1

        all_offers.extend(combo_offers)

        # EARLY STOPPING CONDITIONS
        if combinations_tested >= max_combinations_to_test:
            logger.info(
                f"   ⚡ Early stopping: Reached max combinations limit ({max_combinations_to_test})"
            )
            break

        if valid_offers_count >= early_stop_on_offers:
            logger.info(
                f"   ⚡ Early stopping: Found enough offers ({valid_offers_count} >= {early_stop_on_offers})"
            )
            break

    logger.info(f"🎯 RANGE OPTIMIZATION COMPLETE:")
    logger.info(f"   Combinations tested: {combinations_tested}/{total_combinations}")
    logger.info(f"   Valid offers found: {valid_offers_count:,}")
    logger.info(f"   NPV filtering applied: Min {min_npv_threshold:,.0f} MXN")

    if all_offers:
        # Remove duplicates and rank by NPV within tiers
        return _finalize_optimized_offers_dataframe(
            all_offers, current_monthly_payment, engine_config, tiers
        )

    return pd.DataFrame()


def _run_smart_range_search(
    customer,
    inventory,
    interest_rate,
    engine_config,
    current_monthly_payment,
    payment_delta_tiers,
):
    """Use differential evolution to find near-optimal fee parameters."""
    bounds = [
        tuple(engine_config.get("service_fee_range", (0.0, 5.0))),
        tuple(engine_config.get("cxa_range", (0.0, 4.0))),
        tuple(engine_config.get("cac_bonus_range", (0.0, 10000.0))),
    ]

    min_npv_threshold = engine_config.get("min_npv_threshold", 5000.0)
    term_order = get_term_search_order(engine_config.get("term_priority", "standard"))
    max_iter = engine_config.get("smart_max_iter", 30)

    tiers = payment_delta_tiers

    def objective(params):
        service_fee_pct, cxa_pct, cac_bonus = params
        fees_config = {
            "service_fee_pct": service_fee_pct / 100,
            "cxa_pct": cxa_pct / 100,
            "cac_bonus": cac_bonus,
            "kavak_total_amount": (
                DEFAULT_FEES["kavak_total_amount"]
                if engine_config.get("include_kavak_total", True)
                else 0
            ),
            "insurance_amount": engine_config.get(
                "insurance_amount", DEFAULT_FEES["insurance_amount"]
            ),
            "gps_installation_fee": engine_config.get(
                "gps_installation_fee", DEFAULT_FEES["gps_installation_fee"]
            ),
            "gps_monthly_fee": engine_config.get(
                "gps_monthly_fee", DEFAULT_FEES["gps_monthly_fee"]
            ),
        }

        offers = _run_search_phase_with_npv_filter(
            customer,
            inventory,
            interest_rate,
            fees_config,
            min_npv_threshold,
            tiers,
            term_order,
        )

        if not offers:
            # Return large penalty when no valid offers found
            return 1e9
        best_npv = max(o["npv"] for o in offers)
        return -best_npv

    result = differential_evolution(objective, bounds, maxiter=max_iter, polish=True)
    best_service, best_cxa, best_cac = result.x

    # Round to configured step sizes
    step_s = engine_config.get("service_fee_step", 0.01)
    step_cxa = engine_config.get("cxa_step", 0.01)
    step_cac = engine_config.get("cac_bonus_step", 100)

    import numpy as np
    best_service = np.round(best_service / step_s) * step_s
    best_cxa = np.round(best_cxa / step_cxa) * step_cxa
    best_cac = int(np.round(best_cac / step_cac) * step_cac)

    fees_config = {
        "service_fee_pct": best_service / 100,
        "cxa_pct": best_cxa / 100,
        "cac_bonus": best_cac,
        "kavak_total_amount": (
            DEFAULT_FEES["kavak_total_amount"]
            if engine_config.get("include_kavak_total", True)
            else 0
        ),
        "insurance_amount": engine_config.get(
            "insurance_amount", DEFAULT_FEES["insurance_amount"]
        ),
        "gps_installation_fee": engine_config.get(
            "gps_installation_fee", DEFAULT_FEES["gps_installation_fee"]
        ),
        "gps_monthly_fee": engine_config.get(
            "gps_monthly_fee", DEFAULT_FEES["gps_monthly_fee"]
        ),
    }

    final_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        fees_config,
        min_npv_threshold,
        tiers,
        term_order,
    )

    for offer in final_offers:
        offer["parameter_combination"] = {
            "service_fee_pct": best_service,
            "cxa_pct": best_cxa,
            "cac_bonus": best_cac,
        }

    logger.info(
        f"⚡ SMART SEARCH found best parameters: Service {best_service}%, CXA {best_cxa}% CAC {best_cac}"
    )

    if final_offers:
        return _finalize_optimized_offers_dataframe(
            final_offers, current_monthly_payment, engine_config, tiers
        )

    return pd.DataFrame()


def _run_custom_parameter_search(
    customer,
    inventory,
    interest_rate,
    engine_config,
    current_monthly_payment,
    payment_delta_tiers,
):
    """Custom parameter mode using user-defined fee structure."""
    all_offers = []

    # Build custom fee structure from engine_config
    custom_fees = {
        "service_fee_pct": engine_config.get(
            "service_fee_pct", DEFAULT_FEES["service_fee_pct"]
        ),
        "cxa_pct": engine_config.get("cxa_pct", DEFAULT_FEES["cxa_pct"]),
        "cac_bonus": engine_config.get("cac_bonus", DEFAULT_FEES["cac_bonus"]),
        "kavak_total_amount": (
            DEFAULT_FEES["kavak_total_amount"]
            if engine_config.get("include_kavak_total", True)
            else 0
        ),
            "insurance_amount": engine_config.get(
                "insurance_amount", DEFAULT_FEES["insurance_amount"]
            ),
            "gps_installation_fee": engine_config.get(
                "gps_installation_fee", DEFAULT_FEES["gps_installation_fee"]
            ),
            "gps_monthly_fee": engine_config.get(
                "gps_monthly_fee", DEFAULT_FEES["gps_monthly_fee"]
            ),
        }

    logger.info(f"🔧 Using custom fees: {custom_fees}")

    tiers = payment_delta_tiers

    # Extract NPV threshold for filtering
    min_npv_threshold = engine_config.get("min_npv_threshold", 5000.0)
    term_order = get_term_search_order(engine_config.get("term_priority", "standard"))

    # Run single search phase with custom parameters and NPV filtering
    custom_offers = _run_search_phase_with_npv_filter(
        customer,
        inventory,
        interest_rate,
        custom_fees,
        min_npv_threshold,
        tiers,
        term_order,
    )
    all_offers.extend(custom_offers)

    logger.info(
        f"🔧 CUSTOM SEARCH COMPLETE: Found {len(all_offers)} offers with custom parameters."
    )

    if all_offers:
        return _finalize_offers_dataframe(all_offers, current_monthly_payment, tiers)

    return pd.DataFrame()


def _run_search_phase(
    customer, inventory, interest_rate, fees_config, payment_delta_tiers, term_order
):
    """Helper function to run the search for a given fee configuration."""
    found_offers = []
    for car_index, car in inventory.iterrows():
        for term in term_order:
            offer = _generate_single_offer(
                customer, car, term, interest_rate, fees_config, payment_delta_tiers
            )
            if offer:
                found_offers.append(offer)
    return found_offers


def _generate_single_offer(
    customer,
    car,
    term,
    interest_rate,
    fees_config,
    payment_delta_tiers,
):
    """Return a single valid offer if all business rules are satisfied.

    Parameters
    ----------
    customer : dict
        Customer information including ``vehicle_equity`` and current payment.
    car : pandas.Series
        Inventory row describing the potential upgrade vehicle.
    term : int
        Loan term in months.
    interest_rate : float
        Base annual interest rate for the customer's risk profile.
    fees_config : dict
        Dictionary of fee parameters such as ``service_fee_pct`` and ``cxa_pct``.
    payment_delta_tiers : dict
        Mapping of tier names to accepted payment delta ranges.

    Returns
    -------
    Optional[dict]
        Offer data structured for ranking or ``None`` if any rule fails.

    Notes
    -----
    Effective equity is computed as
    ``vehicle_equity + CAC_bonus - CXA_amount - GPS_install_fee`` and must meet
    the minimum down-payment requirement from ``DOWN_PAYMENT_TABLE``. The loan
    amount is ``sales_price - effective_equity`` and the payment is calculated
    with :func:`_calculate_manual_payment`.  For a full description of the
    underlying rules see ``docs/project-charter.md`` section 4.
    """
    # 1. Hard Filter: Price must exceed current car price
    if car["sales_price"] <= customer["current_car_price"]:
        return None

    # 2. Resolve fees that are deducted from equity but not financed
    cxa_pct = fees_config.get("cxa_pct", 0)
    cac_bonus = fees_config.get("cac_bonus", 0)
    gps_install_with_iva = (
        fees_config.get("gps_installation_fee", GPS_INSTALLATION_FEE) * IVA_RATE
    )
    gps_monthly_with_iva = (
        fees_config.get("gps_monthly_fee", GPS_MONTHLY_FEE) * IVA_RATE
    )

    # 3. CXA is calculated on the new car price and paid upfront
    cxa_amount = car["sales_price"] * cxa_pct

    # 4. Determine effective equity available for down payment
    starting_equity = customer["vehicle_equity"]
    effective_equity = starting_equity + cac_bonus - cxa_amount - gps_install_with_iva

    # 5. Loan amount needed after applying effective equity
    loan_amount_needed = car["sales_price"] - effective_equity

    if loan_amount_needed <= 0:
        return None

    # 6. Other component amounts
    service_fee_amt = car["sales_price"] * fees_config.get("service_fee_pct", 0)
    kavak_total_amt = fees_config.get("kavak_total_amount", 0)
    insurance_amt = fees_config.get(
        "insurance_amount",
        INSURANCE_TABLE.get(
            customer["risk_profile_name"], DEFAULT_FEES["insurance_amount"]
        ),
    )

    # 7. Total financed amount (main loan + financed fees)
    total_financed = (
        loan_amount_needed + service_fee_amt + kavak_total_amt + insurance_amt
    )

    # 7. Down payment check using effective equity
    required_dp_pct = DOWN_PAYMENT_TABLE.loc[customer["risk_profile_index"], term]
    if effective_equity < car["sales_price"] * required_dp_pct:
        return None

    # 9. Determine interest rate with term premium
    final_rate = interest_rate
    if term == 60:
        final_rate += 0.01
    elif term == 72:
        final_rate += 0.015

    # 10. Manual monthly payment calculation
    actual_monthly_payment = _calculate_manual_payment(
        loan_amount_needed,
        final_rate,
        term,
        service_fee_amt,
        kavak_total_amt,
        insurance_amt,
        gps_monthly_with_iva,
    )

    # 11. Validate payment delta
    payment_delta = (actual_monthly_payment / customer["current_monthly_payment"]) - 1
    valid_tier = False
    for tier, (min_d, max_d) in payment_delta_tiers.items():
        if min_d <= payment_delta <= max_d:
            valid_tier = True
            break

    if not valid_tier:
        return None  # Payment delta is outside acceptable ranges

    # SUCCESS! Build the final offer dictionary
    offer_data = {
        "car_id": car["car_id"],
        "car_model": car["model"],
        "new_car_price": car["sales_price"],
        "term": term,
        "monthly_payment": actual_monthly_payment,
        "payment_delta": payment_delta,
        "loan_amount": total_financed,
        "effective_equity": effective_equity,
        "cxa_amount": cxa_amount,
        "service_fee_amount": service_fee_amt,
        "kavak_total_amount": kavak_total_amt,
        "insurance_amount": insurance_amt,
        "gps_install_fee": gps_install_with_iva,
        "gps_monthly_fee": gps_monthly_with_iva,
        "npv": calculate_final_npv(total_financed, final_rate, term),
        "fees_applied": fees_config,
        "interest_rate": final_rate,
    }
    return offer_data

def _calculate_manual_payment(
    loan_amount: float,
    interest_rate: float,
    term: int,
    service_fee_amt: float,
    kavak_total_amt: float,
    insurance_amt: float,
    gps_monthly_fee: float,
):
    """Manual monthly payment calculation following the MVP specification."""
    # Per business rules ("Kavak Method") the capital portion is calculated
    # using the interest rate with IVA baked in while the interest portion
    # itself is computed using the base rate and then taxed.  This produces the
    # same total payment as a PMT using ``interest_rate * IVA_RATE`` but keeps
    # the IVA accounting explicit.
    monthly_rate_interest = interest_rate / 12
    monthly_rate_principal = (interest_rate * IVA_RATE) / 12

    # Component 1: Main loan amount
    principal_main = abs(npf.ppmt(monthly_rate_principal, 1, term, -loan_amount))
    interest_main = (
        abs(npf.ipmt(monthly_rate_interest, 1, term, -loan_amount)) * IVA_RATE
    )

    # Component 2: Financed service fee
    principal_sf = abs(npf.ppmt(monthly_rate_principal, 1, term, -service_fee_amt))
    interest_sf = (
        abs(npf.ipmt(monthly_rate_interest, 1, term, -service_fee_amt)) * IVA_RATE
    )

    # Component 3: Financed Kavak Total
    principal_kt = abs(npf.ppmt(monthly_rate_principal, 1, term, -kavak_total_amt))
    interest_kt = (
        abs(npf.ipmt(monthly_rate_interest, 1, term, -kavak_total_amt)) * IVA_RATE
    )

    # Component 4: Insurance financed over 12 months
    principal_ins = abs(npf.ppmt(monthly_rate_principal, 1, 12, -insurance_amt))
    interest_ins = (
        abs(npf.ipmt(monthly_rate_interest, 1, 12, -insurance_amt)) * IVA_RATE
    )

    total_payment = (
        principal_main
        + interest_main
        + principal_sf
        + interest_sf
        + principal_kt
        + interest_kt
        + principal_ins
        + interest_ins
        + gps_monthly_fee
    )

    return total_payment


def _generate_range(start, end, step):
    """Generate a range of values with specified step size, handling floating point precision."""
    import numpy as np

    return np.arange(start, end + step, step)


def _validate_range(range_tuple, step, name):
    """Validate range inputs before optimization."""
    start, end = range_tuple
    if step <= 0:
        raise ValueError(f"{name} step must be positive")
    if end < start:
        raise ValueError(f"{name} bounds must be in ascending order")


def _run_search_phase_with_npv_filter(
    customer,
    inventory,
    interest_rate,
    fees_config,
    min_npv_threshold,
    payment_delta_tiers,
    term_order,
):
    """Helper function to run search with NPV filtering applied."""
    found_offers = []
    for car_index, car in inventory.iterrows():
        for term in term_order:
            offer = _generate_single_offer(
                customer, car, term, interest_rate, fees_config, payment_delta_tiers
            )
            if offer and offer["npv"] >= min_npv_threshold:  # Apply NPV filter
                found_offers.append(offer)
    return found_offers


def _finalize_optimized_offers_dataframe(
    offers_list, current_monthly_payment, engine_config, payment_delta_tiers
):
    """
    Advanced finalization for range optimization with NPV-based ranking within tiers.
    """
    if not offers_list:
        return pd.DataFrame()

    df = pd.DataFrame(offers_list)
    df["payment_delta"] = (df["monthly_payment"] / current_monthly_payment) - 1

    def assign_tier(delta):
        for tier, (min_d, max_d) in payment_delta_tiers.items():
            if min_d <= delta <= max_d:
                return tier
        return "N/A"

    df["tier"] = df["payment_delta"].apply(assign_tier)
    # Filter out any offers that might have fallen out of bounds after precise calculation
    df = df[df["tier"] != "N/A"]

    # Remove duplicates: keep the offer with highest NPV for each car/term combination
    df = df.sort_values("npv", ascending=False).drop_duplicates(
        subset=["car_id", "term"], keep="first"
    )

    # Rank offers within each tier by NPV (descending)
    df["npv_rank_within_tier"] = df.groupby("tier")["npv"].rank(
        method="dense", ascending=False
    )

    # Limit offers per tier if specified
    max_offers_per_tier = engine_config.get(
        "max_offers_per_tier", 50
    )  # Default: top 50 per tier
    df = df.groupby("tier").head(max_offers_per_tier).reset_index(drop=True)

    # Sort by tier preference (Refresh > Upgrade > Max Upgrade) then by NPV within tier
    tier_order = {"Refresh": 1, "Upgrade": 2, "Max Upgrade": 3}
    df["tier_priority"] = df["tier"].map(tier_order)
    df = df.sort_values(["tier_priority", "npv"], ascending=[True, False])

    return df


def _finalize_offers_dataframe(
    offers_list, current_monthly_payment, payment_delta_tiers
):
    """Helper to convert list of offer dicts to a final DataFrame with tiers."""
    if not offers_list:
        return pd.DataFrame()

    # This is the key fix: ensure all columns are preserved when creating the DataFrame
    df = pd.DataFrame.from_records(offers_list)
    
    # Calculate payment_delta and assign tiers
    df["payment_delta"] = (df["monthly_payment"] / current_monthly_payment) - 1

    def assign_tier(delta):
        for tier, (min_d, max_d) in payment_delta_tiers.items():
            if min_d <= delta <= max_d:
                return tier
        return "N/A"

    df["tier"] = df["payment_delta"].apply(assign_tier)
    
    # Filter out any offers that might have fallen out of bounds after precise calculation
    df = df[df["tier"] != "N/A"]
    
    # Ensure all original columns are present
    return df
