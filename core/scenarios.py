import time
from typing import Dict
import logging
from core.logging_config import setup_logging

import pandas as pd
from pandas import DataFrame
from fastapi import HTTPException

from .engine import run_engine_for_customer
from .config_manager import save_engine_config, save_scenario_results

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


def run_scenario_analysis(config: Dict, customers_df: DataFrame, inventory_df: DataFrame) -> Dict:
    """Run scenario analysis using the provided configuration and datasets."""
    try:
        start_time = time.time()

        # Save configuration
        config_dict = dict(config)
        save_engine_config(config_dict)

        # Initialize metrics
        total_customers = len(customers_df) if not customers_df.empty else 0
        total_offers = 0
        total_npv = 0
        offers_by_tier = {"Refresh": 0, "Upgrade": 0, "Max Upgrade": 0}
        processing_errors = 0

        # Baseline config for reference (not currently used)
        baseline_config = {
            "use_custom_params": False,
            "use_range_optimization": False,
            "include_kavak_total": True,
            "min_npv_threshold": 5000.0,
        }

        logger.info(f"🎯 Starting REAL scenario analysis with {total_customers} customers...")
        logger.info(f"Configuration: {config_dict}")

        # Sample customers for analysis
        sample_size = min(100, total_customers)
        if total_customers > sample_size:
            customer_sample = customers_df.sample(sample_size, random_state=42)
            logger.info(f"📊 Processing sample of {sample_size} customers for analysis...")
        else:
            customer_sample = customers_df

        # Run engine for each customer
        for _, customer in customer_sample.iterrows():
            try:
                customer_dict = customer.to_dict()

                offers_df = run_engine_for_customer(customer_dict, inventory_df, config_dict)

                if not offers_df.empty:
                    total_offers += len(offers_df)
                    total_npv += offers_df["npv"].sum()

                    for tier in offers_df["tier"].unique():
                        offers_by_tier[tier] += len(offers_df[offers_df["tier"] == tier])

            except Exception as e:
                logger.warning(f"⚠️ Error processing customer {customer.get('customer_id', 'unknown')}: {e}")
                processing_errors += 1

        processed_customers = sample_size - processing_errors
        avg_offers_per_customer = total_offers / processed_customers if processed_customers > 0 else 0
        avg_npv_per_offer = total_npv / total_offers if total_offers > 0 else 0

        extrapolated_total_offers = int(avg_offers_per_customer * total_customers)
        extrapolated_total_npv = int(avg_npv_per_offer * extrapolated_total_offers)

        execution_time = time.time() - start_time

        results = {
            "scenario_config": config_dict,
            "execution_details": {
                "sample_size": sample_size,
                "total_customers": total_customers,
                "processed_customers": processed_customers,
                "processing_errors": processing_errors,
                "execution_time_seconds": round(execution_time, 2),
            },
            "actual_metrics": {
                "total_offers": extrapolated_total_offers,
                "average_npv_per_offer": int(avg_npv_per_offer),
                "total_portfolio_npv": extrapolated_total_npv,
                "offers_per_customer": round(avg_offers_per_customer, 1),
                "tier_distribution": offers_by_tier,
            },
            "mode_info": {
                "mode": (
                    "Range Optimization"
                    if config_dict.get("use_range_optimization")
                    else (
                        "Custom Parameters" if config_dict.get("use_custom_params") else "Default Hierarchical"
                    )
                ),
                "parameter_combinations": 0,
            },
        }

        if config_dict.get("use_range_optimization"):
            service_fee_count = (
                int((config_dict["service_fee_range"][1] - config_dict["service_fee_range"][0]) / config_dict["service_fee_step"]) + 1
            )
            cxa_count = int((config_dict["cxa_range"][1] - config_dict["cxa_range"][0]) / config_dict["cxa_step"]) + 1
            cac_count = int((config_dict["cac_bonus_range"][1] - config_dict["cac_bonus_range"][0]) / config_dict["cac_bonus_step"]) + 1
            results["mode_info"]["parameter_combinations"] = service_fee_count * cxa_count * cac_count

        save_scenario_results(results)
        return results

    except Exception as e:
        logger.error(f"❌ Scenario analysis failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {str(e)}")
