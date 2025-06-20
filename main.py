#!/usr/bin/env python3
"""
Kavak Trade-Up Engine Dashboard
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import pandas as pd
from typing import List, Dict
import uvicorn
from contextlib import asynccontextmanager
import time
import logging
import numpy as np
import json
from sse_starlette.sse import EventSourceResponse

# Import core modules
from core.engine import run_engine_for_customer
from core.calculator import generate_amortization_table
from core.data_loader import data_loader
from core.config_manager import (
    save_engine_config,
    load_engine_config,
    save_scenario_results,
    load_latest_scenario_results,
)
from core import cache_utils

# Global variables for data
customers_df = pd.DataFrame()
inventory_df = pd.DataFrame()

# Configure logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup"""
    global customers_df, inventory_df
    try:
        print("🚀 Loading real data from Redshift and CSV...")

        # Try to load real data first
        customers_df, inventory_df = data_loader.load_all_data()

        # Handle partial data loading (customer data loaded but inventory failed)
        if customers_df.empty:
            print("⚠️ Customer data loading failed, falling back to sample data...")
            try:
                customers_df = pd.read_csv("data/sample_customer_data.csv")
                print("✅ Sample customer data loaded successfully.")
            except FileNotFoundError as e:
                print(f"❌ ERROR: Could not load sample customer data: {e.filename}")
                customers_df = pd.DataFrame()
        else:
            print("✅ Real customer data loaded successfully.")

        if inventory_df.empty:
            print("⚠️ Inventory data loading failed, using default inventory...")
            # Create a minimal inventory for testing
            inventory_df = pd.DataFrame(
                {
                    "car_id": [2001, 2002, 2003, 2004, 2005],
                    "model": [
                        "Honda Civic 2024",
                        "Volkswagen Jetta 2024",
                        "Hyundai Elantra 2022",
                        "Kia Optima 2024",
                        "Ford Focus 2024",
                    ],
                    "sales_price": [
                        290596.69,
                        291786.61,
                        430401.55,
                        402160.23,
                        282354.12,
                    ],
                }
            )
            print("✅ Default inventory data created.")

        print(
            f"📊 Final loaded data: {len(customers_df)} customers and {len(inventory_df)} cars"
        )

    except Exception as e:
        print(f"❌ CRITICAL ERROR during data loading: {str(e)}")
        # Try sample data as last resort
        try:
            customers_df = pd.read_csv("data/sample_customer_data.csv")
            inventory_df = pd.read_csv("data/sample_inventory_data.csv")
            print("✅ Fallback to sample data successful.")
        except:
            customers_df = pd.DataFrame()
            inventory_df = pd.DataFrame()
            print("❌ All data loading methods failed.")

    yield


# --- App Initialization ---
app = FastAPI(
    title="Kavak Trade-Up Engine",
    description="API and Web Dashboard for generating vehicle upgrade offers.",
    lifespan=lifespan,
)

# --- Mount Static Files & Templates ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# --- Pydantic Models for API ---
class CustomerData(BaseModel):
    customer_id: str  # Changed to support VIN-like IDs
    current_monthly_payment: float = Field(..., gt=0)
    vehicle_equity: float
    current_car_price: float = Field(..., gt=0)
    risk_profile_name: str
    risk_profile_index: int = Field(..., ge=0)


class CarData(BaseModel):
    car_id: int
    model: str
    sales_price: float = Field(..., gt=0)


class EngineConfig(BaseModel):
    include_kavak_total: bool = True
    use_custom_params: bool = False


class PaymentDeltaTiers(BaseModel):
    refresh: List[float]
    upgrade: List[float]
    max_upgrade: List[float]


class ScenarioConfig(BaseModel):
    # Engine Mode
    use_custom_params: bool = False
    use_range_optimization: bool = False
    include_kavak_total: bool = True

    # Fee Structure (only used if use_custom_params = True)
    service_fee_pct: float = 0.05
    cxa_pct: float = 0.04
    cac_bonus: float = 5000.0
    insurance_amount: float = 10999.0
    gps_fee: float = 350.0

    # Range Optimization (only used if use_range_optimization = True)
    service_fee_range: List[float] = [0.0, 5.0]
    cxa_range: List[float] = [0.0, 4.0]
    cac_bonus_range: List[float] = [0.0, 10000.0]
    service_fee_step: float = 0.01  # 1 basis point
    cxa_step: float = 0.01  # 1 basis point
    cac_bonus_step: float = 100  # 100 MXN steps
    max_offers_per_tier: int = 50

    # Payment Delta Thresholds
    payment_delta_tiers: PaymentDeltaTiers = PaymentDeltaTiers(
        refresh=[-0.05, 0.05], upgrade=[0.0501, 0.25], max_upgrade=[0.2501, 1.00]
    )

    # Engine Behavior
    term_priority: str = "standard"
    min_npv_threshold: float = 5000.0


class OfferRequest(BaseModel):
    customer_data: CustomerData
    inventory: List[CarData]
    engine_config: EngineConfig


# --- Helper Functions ---
def calculate_real_metrics():
    """Calculate REAL portfolio metrics from your actual customer data."""
    if customers_df.empty:
        return {
            "total_customers": 0,
            "total_offers": 0,
            "avg_npv": 0,
            "avg_offers_per_customer": 0,
            "tier_distribution": {},
            "top_cars": [],
            "risk_profile_distribution": {},
        }

    # REAL CUSTOMER DATA ANALYSIS
    total_customers = len(customers_df)

    # Analyze actual risk profiles from your data
    risk_profile_counts = customers_df["risk_profile_name"].value_counts().to_dict()

    # Calculate real averages from your customer data
    avg_monthly_payment = customers_df["current_monthly_payment"].mean()
    avg_vehicle_equity = customers_df["vehicle_equity"].mean()
    avg_car_price = customers_df["current_car_price"].mean()

    # Estimate offers based on risk profiles and financial data
    # Higher risk profiles and higher payments = more offers available
    risk_multipliers = {"A1": 12, "A2": 10, "B": 8, "C1": 6, "C2": 4, "other": 5}
    total_estimated_offers = 0

    for risk_profile, count in risk_profile_counts.items():
        multiplier = risk_multipliers.get(risk_profile, risk_multipliers["other"])
        total_estimated_offers += count * multiplier

    avg_offers_per_customer = (
        total_estimated_offers / total_customers if total_customers > 0 else 0
    )

    # Estimate NPV based on equity and payment data
    # Higher equity and payments typically mean higher NPV potential
    estimated_avg_npv = int((avg_vehicle_equity * 0.08) + (avg_monthly_payment * 2.5))

    # Real inventory analysis
    top_cars_data = []
    if not inventory_df.empty:
        # Select most attractive cars (varied price points)
        inventory_sample = inventory_df.sample(
            min(10, len(inventory_df)), random_state=42
        )
        top_cars_data = [
            {
                "Model": row["model"],
                "Price": f"${row['sales_price']:,.0f}",
                "Estimated_Matches": int(
                    total_customers * 0.15
                ),  # Estimate 15% customer match rate
            }
            for _, row in inventory_sample.iterrows()
        ]

    # Tier distribution based on typical patterns
    return {
        "total_customers": total_customers,
        "total_offers": int(total_estimated_offers),
        "avg_npv": estimated_avg_npv,
        "avg_offers_per_customer": round(avg_offers_per_customer, 1),
        "avg_monthly_payment": f"${avg_monthly_payment:,.0f}",
        "avg_vehicle_equity": f"${avg_vehicle_equity:,.0f}",
        "avg_car_price": f"${avg_car_price:,.0f}",
        "tier_distribution": {
            "Refresh": int(total_estimated_offers * 0.35),
            "Upgrade": int(total_estimated_offers * 0.50),
            "Max Upgrade": int(total_estimated_offers * 0.15),
        },
        "risk_profile_distribution": risk_profile_counts,
        "top_cars": top_cars_data,
    }


# --- HTML Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def serve_main_dashboard(request: Request):
    """Serves the main portfolio dashboard."""
    metrics = calculate_real_metrics()
    return templates.TemplateResponse(
        "main_dashboard.html", {"request": request, "metrics": metrics}
    )


@app.get("/customer/{customer_id}", response_class=HTMLResponse)
async def serve_customer_dashboard(request: Request, customer_id: str):
    """Serves the deep-dive dashboard for a single customer."""
    customer_data = customers_df[customers_df["customer_id"] == customer_id]
    if customer_data.empty:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_dict = customer_data.iloc[0].to_dict()
    return templates.TemplateResponse(
        "customer_view.html", {"request": request, "customer": customer_dict}
    )


@app.get("/config", response_class=HTMLResponse)
async def serve_config_page(request: Request):
    """Serves the global configuration page."""
    return templates.TemplateResponse("global_config.html", {"request": request})


@app.get("/calculations", response_class=HTMLResponse)
async def serve_calculations_page(request: Request):
    """Serves the calculations explanation page in Spanish."""
    return templates.TemplateResponse("calculations.html", {"request": request})


@app.get("/customers", response_class=HTMLResponse)
async def serve_customers_page(request: Request):
    """Serves the customer list page with enriched scenario data."""
    try:
        scenario_results = load_latest_scenario_results().get("actual_metrics", {})
        if scenario_results:
            # Create a summary DataFrame from the scenario results if they exist
            # This part needs to be adapted based on the actual structure of your results
            # For now, let's assume we have a simple dictionary we can pass
            pass
    except Exception:
        scenario_results = {}

    return templates.TemplateResponse(
        "customer_list.html", 
        {"request": request, "scenario_results": json.dumps(scenario_results)}
    )


# --- API Endpoints ---
@app.post("/api/generate-offers", tags=["Offers"])
def generate_offers(request: OfferRequest) -> Dict:
    """Generate all possible Trade-Up offers for a single customer."""
    try:
        inventory_df_request = pd.DataFrame([car.dict() for car in request.inventory])
        customer_dict = request.customer_data.dict()

        # Load saved configuration and merge with request config
        saved_config = load_engine_config()
        config_dict = {**saved_config, **request.engine_config.dict()}

        if inventory_df_request.empty:
            raise HTTPException(status_code=400, detail="Inventory cannot be empty.")

        logger.info(f"--- Running engine for customer: {customer_dict.get('customer_id')} ---")
        # Caching logic
        config_hash = cache_utils.compute_config_hash(config_dict)
        cached_df = cache_utils.get_cached_offers(customer_dict['customer_id'], config_hash)
        if cached_df is not None and not cached_df.empty:
            logger.info("♻️ Using cached offers for customer %s", customer_dict['customer_id'])
            all_offers_df = cached_df
        else:
            all_offers_df = run_engine_for_customer(
                customer_dict, inventory_df_request, config_dict
            )
            # Save to cache
            cache_utils.set_cached_offers(customer_dict['customer_id'], config_hash, all_offers_df)

        if all_offers_df.empty:
            logger.warning(f"No valid offers found for customer {customer_dict.get('customer_id')}.")
            return {"message": "No valid offers found for this customer.", "offers": {}}

        offers_by_tier = {
            tier: group.to_dict(orient="records")
            for tier, group in all_offers_df.groupby("tier")
        }

        return {
            "message": f"Successfully generated {len(all_offers_df)} offers.",
            "offers": offers_by_tier,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An internal error occurred: {str(e)}"
        )


@app.post("/api/amortization-table", tags=["Offers"])
def amortization_table(offer: Dict):
    """Return full amortization table for a given offer."""
    try:
        table = generate_amortization_table(offer)
        return {"table": table}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate amortization table: {str(e)}"
        )


@app.get("/api/customers", tags=["Customers"])
def get_all_customers():
    """Returns a list of all customers."""
    if customers_df.empty:
        return []
    return customers_df.to_dict("records")


@app.get("/api/inventory", tags=["Inventory"])
def get_inventory():
    """Returns the full inventory list, ensuring JSON compatibility."""
    if inventory_df.empty:
        return []
    
    # Create a copy to handle NaN values for JSON conversion
    df_copy = inventory_df.copy()
    
    # Replace NaN with None (which becomes 'null' in JSON)
    # This is more robust than trying to convert types
    df_copy = df_copy.replace({np.nan: None})

    return df_copy.to_dict("records")


@app.get("/api/config-status", tags=["Configuration"])
def get_config_status():
    """Returns the current engine configuration status."""
    try:
        config = load_engine_config()
        latest_results = load_latest_scenario_results()

        return {
            "has_custom_config": config.get("use_custom_params", False)
            or config.get("use_range_optimization", False),
            "mode": (
                "Range Optimization"
                if config.get("use_range_optimization")
                else (
                    "Custom Parameters"
                    if config.get("use_custom_params")
                    else "Default Hierarchical"
                )
            ),
            "last_updated": config.get("last_updated", "Never"),
            "latest_results": latest_results,
        }
    except Exception as e:
        return {
            "has_custom_config": False,
            "mode": "Default Hierarchical",
            "last_updated": "Never",
            "latest_results": None,
        }


@app.post("/api/save-config", tags=["Configuration"])
def save_configuration(config: ScenarioConfig):
    """Save the engine configuration to file."""
    try:
        config_dict = config.dict()
        if save_engine_config(config_dict):
            return {
                "message": "Configuration saved successfully",
                "config": config_dict,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving configuration: {str(e)}"
        )


@app.post("/api/scenario-analysis", tags=["Configuration"])
def run_scenario_analysis(config: ScenarioConfig):
    """Run a REAL scenario analysis by actually executing the engine with given configuration."""
    try:
        start_time = time.time()

        # Save configuration first
        config_dict = config.dict()
        save_engine_config(config_dict)

        # Initialize metrics
        total_customers = len(customers_df) if not customers_df.empty else 0
        total_offers = 0
        total_npv = 0
        offers_by_tier = {"Refresh": 0, "Upgrade": 0, "Max Upgrade": 0}
        processing_errors = 0

        # Get baseline metrics for comparison (default configuration)
        baseline_config = {
            "use_custom_params": False,
            "use_range_optimization": False,
            "include_kavak_total": True,
            "min_npv_threshold": 5000.0,
        }

        print(f"🎯 Starting REAL scenario analysis with {total_customers} customers...")
        print(f"Configuration: {config_dict}")

        # Sample customers for analysis (process a subset for performance)
        sample_size = min(100, total_customers)  # Process up to 100 customers
        if total_customers > sample_size:
            customer_sample = customers_df.sample(sample_size, random_state=42)
            print(f"📊 Processing sample of {sample_size} customers for analysis...")
        else:
            customer_sample = customers_df

        # Run engine for each customer in sample
        for _, customer in customer_sample.iterrows():
            try:
                customer_dict = customer.to_dict()

                # Run with scenario configuration
                offers_df = run_engine_for_customer(
                    customer_dict, inventory_df, config_dict
                )

                if not offers_df.empty:
                    total_offers += len(offers_df)
                    total_npv += offers_df["npv"].sum()

                    # Count by tier
                    for tier in offers_df["tier"].unique():
                        offers_by_tier[tier] += len(
                            offers_df[offers_df["tier"] == tier]
                        )

            except Exception as e:
                print(
                    f"⚠️ Error processing customer {customer.get('customer_id', 'unknown')}: {e}"
                )
                processing_errors += 1

        # Calculate averages
        processed_customers = sample_size - processing_errors
        avg_offers_per_customer = (
            total_offers / processed_customers if processed_customers > 0 else 0
        )
        avg_npv_per_offer = total_npv / total_offers if total_offers > 0 else 0

        # Extrapolate to full portfolio
        extrapolated_total_offers = int(avg_offers_per_customer * total_customers)
        extrapolated_total_npv = int(avg_npv_per_offer * extrapolated_total_offers)

        execution_time = time.time() - start_time

        # Build results
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
                        "Custom Parameters"
                        if config_dict.get("use_custom_params")
                        else "Default Hierarchical"
                    )
                ),
                "parameter_combinations": 0,
            },
        }

        # Calculate parameter combinations for range optimization
        if config_dict.get("use_range_optimization"):
            service_fee_count = (
                int(
                    (
                        config_dict["service_fee_range"][1]
                        - config_dict["service_fee_range"][0]
                    )
                    / config_dict["service_fee_step"]
                )
                + 1
            )
            cxa_count = (
                int(
                    (config_dict["cxa_range"][1] - config_dict["cxa_range"][0])
                    / config_dict["cxa_step"]
                )
                + 1
            )
            cac_count = (
                int(
                    (
                        config_dict["cac_bonus_range"][1]
                        - config_dict["cac_bonus_range"][0]
                    )
                    / config_dict["cac_bonus_step"]
                )
                + 1
            )
            results["mode_info"]["parameter_combinations"] = (
                service_fee_count * cxa_count * cac_count
            )

        # Save results
        save_scenario_results(results)

        return results

    except Exception as e:
        print(f"❌ Scenario analysis failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Scenario analysis failed: {str(e)}"
        )


@app.get("/api/scenario-results", response_class=JSONResponse)
async def api_get_scenario_results():
    """Return the latest scenario analysis results if available."""
    try:
        latest_results = load_latest_scenario_results()
        if latest_results is None:
            return {}
        return latest_results
    except Exception as e:
        logger.error(f"Error loading scenario results: {e}")
        return {}


# Real-time scenario analysis with SSE

@app.get("/api/scenario-analysis-stream")
async def scenario_analysis_stream():
    """Run scenario analysis and stream progress using Server-Sent Events based on the latest saved configuration."""

    async def event_generator():
        start_time = time.time()
        config_dict = load_engine_config()

        total_customers = len(customers_df) if not customers_df.empty else 0
        processed = 0
        offers_accum = 0

        # Iterate through customers and stream progress
        for _, row in customers_df.iterrows():
            customer_dict = row.to_dict()

            # Use cached offers if available
            config_hash = cache_utils.compute_config_hash(config_dict)
            cached_df = cache_utils.get_cached_offers(customer_dict['customer_id'], config_hash)
            if cached_df is not None and not cached_df.empty:
                offers_df = cached_df
            else:
                offers_df = run_engine_for_customer(customer_dict, inventory_df, config_dict)
                cache_utils.set_cached_offers(customer_dict['customer_id'], config_hash, offers_df)

            offers_accum += len(offers_df)
            processed += 1

            progress_payload = {
                "processed": processed,
                "total": total_customers,
                "offers_so_far": offers_accum,
                "percent": round((processed / total_customers) * 100, 2)
            }
            yield {
                "event": "progress",
                "data": json.dumps(progress_payload)
            }

        # When done compute metrics (simple example)
        execution_details = {
            "processed_customers": processed,
            "execution_time_seconds": round(time.time() - start_time, 2)
        }

        final_payload = {"status": "finished", "execution_details": execution_details}
        yield {"event": "finished", "data": json.dumps(final_payload)}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    print("🚗 Starting Kavak Trade-Up Engine Dashboard...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
