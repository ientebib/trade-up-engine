"""
Trade-Up Engine API Routes
Development version with mock data support - Updated to match production API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
from pydantic import BaseModel, Field
import json
import logging
import time
from pathlib import Path

from core.engine import TradeUpEngine
from core.data_loader_dev import dev_data_loader
from core.config_manager import ConfigManager
from core.settings import EngineSettings

# Initialize router
router = APIRouter()

# Initialize components
engine = TradeUpEngine()
data_loader = dev_data_loader
config_manager = ConfigManager()
logger = logging.getLogger(__name__)

# --- Pydantic Models (matching production) ---
class CustomerData(BaseModel):
    customer_id: str
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
    gps_installation_fee: float = 750.0
    gps_monthly_fee: float = 350.0

    # Range Optimization (only used if use_range_optimization = True)
    service_fee_range: List[float] = [0.0, 5.0]
    cxa_range: List[float] = [0.0, 4.0]
    cac_bonus_range: List[float] = [0.0, 10000.0]
    service_fee_step: float = 0.01
    cxa_step: float = 0.01
    cac_bonus_step: float = 100
    max_offers_per_tier: int = 50
    max_combinations_to_test: int = 1000
    early_stop_on_offers: int = 100

    # Payment Delta Thresholds
    payment_delta_tiers: PaymentDeltaTiers = PaymentDeltaTiers(
        refresh=[-0.05, 0.05],
        upgrade=[0.0501, 0.25],
        max_upgrade=[0.2501, 1.00],
    )

    # Engine Behavior
    term_priority: str = "standard"
    min_npv_threshold: float = 5000.0

class OfferRequest(BaseModel):
    customer_data: CustomerData
    inventory: List[CarData]
    engine_config: EngineConfig

# --- API Endpoints ---
@router.get("/customers")
async def get_customers():
    """Get all customers"""
    try:
        customers = data_loader.load_customers()
        return customers.to_dict(orient="records")
    except FileNotFoundError:
        logger.exception("Customer data file not found")
        raise HTTPException(status_code=500, detail="Customer data file not found")
    except PermissionError:
        logger.exception("Permission denied reading customer data file")
        raise HTTPException(status_code=500, detail="Customer data file not readable")
    except OSError as e:
        logger.exception(f"OS error while loading customers: {e}")
        raise HTTPException(status_code=500, detail="Failed to load customer data")
    except Exception as e:
        logger.exception(f"Error loading customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customer/{customer_id}")
async def get_customer(customer_id: str):
    """Get specific customer details"""
    try:
        customers = data_loader.load_customers()
        customer = customers[customers["customer_id"] == customer_id]
        if customer.empty:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"customer": customer.iloc[0].to_dict()}
    except HTTPException:
        raise
    except FileNotFoundError:
        logger.exception("Customer data file not found")
        raise HTTPException(status_code=500, detail="Customer data file not found")
    except PermissionError:
        logger.exception("Permission denied reading customer data file")
        raise HTTPException(status_code=500, detail="Customer data file not readable")
    except OSError as e:
        logger.exception(f"OS error while loading customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load customer data")
    except Exception as e:
        logger.exception(f"Error loading customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-offers")
async def generate_offers(request: OfferRequest) -> Dict:
    """Generate all possible Trade-Up offers for a single customer - Production API Compatible"""
    try:
        logger.info(f"🎯 Starting offer generation for customer: {request.customer_data.customer_id}")
        
        # Convert request to DataFrames
        try:
            inventory_df = data_loader.load_inventory()
            if inventory_df.empty:
                logger.warning("⚠️ Inventory is empty - this may cause offer generation to fail")
        except Exception as e:
            logger.error(f"❌ Failed to load inventory: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load inventory data: {str(e)}")
        
        customer_dict = request.customer_data.dict()
        
        # Load current config and merge with request config
        try:
            settings: EngineSettings = config_manager.load_config()
            config_dict = {**settings.model_dump(), **request.engine_config.dict()}
        except Exception as e:
            logger.error(f"❌ Failed to load engine config: {e}")
            # Use default config as fallback
            config_dict = request.engine_config.dict()
        
        # Update engine with current config
        try:
            engine.update_config(config_dict)
        except Exception as e:
            logger.warning(f"⚠️ Failed to update engine config: {e}")
        
        # Generate offers
        try:
            logger.info(f"🔄 Generating offers with {len(inventory_df)} inventory items")
            offers_df = engine.generate_offers(customer_dict, inventory_df)
        except Exception as e:
            logger.error(f"❌ Offer generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Offer generation failed: {str(e)}")
        
        if offers_df.empty:
            logger.warning(f"⚠️ No valid offers found for customer {customer_dict.get('customer_id')}")
            return {"message": "No valid offers found for this customer.", "offers": {}}
        
        # Group offers by tier (matching production format)
        offers_by_tier = {}
        if 'tier' in offers_df.columns:
            for tier, group in offers_df.groupby('tier'):
                offers_by_tier[tier] = group.to_dict(orient='records')
        else:
            # Fallback: put all offers in a single group
            offers_by_tier['All'] = offers_df.to_dict(orient='records')
        
        logger.info(f"✅ Successfully generated {len(offers_df)} offers across {len(offers_by_tier)} tiers")
        return {
            "message": f"Successfully generated {len(offers_df)} offers.",
            "offers": offers_by_tier
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as ve:
        logger.exception(f"Invalid parameters: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(ve)}")
    except FileNotFoundError as e:
        logger.exception("Required data file not found")
        raise HTTPException(status_code=500, detail=f"Required data file not found: {str(e)}")
    except PermissionError as e:
        logger.exception("Permission denied accessing data files")
        raise HTTPException(status_code=500, detail=f"Permission denied: {str(e)}")
    except OSError as e:
        logger.exception(f"File system error during offer generation: {e}")
        if e.errno == 5:  # Input/output error
            raise HTTPException(status_code=500, detail="File system I/O error - please check file permissions and disk space")
        else:
            raise HTTPException(status_code=500, detail=f"File system error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error during offer generation: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@router.post("/amortization-table")
async def amortization_table(offer: Dict):
    """Return full amortization table for a given offer"""
    try:
        # Extract data from the offer with proper field mapping
        loan_amount = offer.get('loan_amount', 0)
        monthly_payment = offer.get('monthly_payment', 0)
        # Try both 'term' and 'term_months' for backwards compatibility
        term_months = offer.get('term', offer.get('term_months', 24))
        interest_rate = offer.get('interest_rate', 0.12) / 12  # Convert annual to monthly
        
        logger.info(f"Generating amortization table - Loan: ${loan_amount:,.2f}, Payment: ${monthly_payment:,.2f}, Term: {term_months} months")
        
        if loan_amount <= 0 or monthly_payment <= 0 or term_months <= 0:
            logger.warning(f"Invalid amortization parameters: loan_amount={loan_amount}, monthly_payment={monthly_payment}, term_months={term_months}")
            return {"table": [], "error": "Invalid loan parameters"}
        
        table = []
        balance = loan_amount
        
        for month in range(1, term_months + 1):
            # Calculate interest on remaining balance
            interest_payment = balance * interest_rate
            # Principal is the remainder of the payment
            principal_payment = monthly_payment - interest_payment
            
            # Ensure we don't go negative
            if principal_payment > balance:
                principal_payment = balance
                actual_payment = balance + interest_payment
            else:
                actual_payment = monthly_payment
            
            # Update balance
            balance = max(0, balance - principal_payment)
            
            table.append({
                'month': month,
                'beginning_balance': balance + principal_payment,
                'payment': actual_payment,
                'principal': principal_payment,
                'interest': interest_payment,
                'ending_balance': balance
            })
            
            # Stop if balance reaches zero
            if balance <= 0:
                break
                
        logger.info(f"Generated amortization table with {len(table)} rows")
        return {"table": table}
        
    except Exception as e:
        logger.exception(f"Error generating amortization table: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate amortization table: {str(e)}")

@router.get("/config")
async def get_config():
    """Get current engine configuration"""
    try:
        settings: EngineSettings = config_manager.load_config()
        return {"config": settings.model_dump()}
    except Exception as e:
        logger.exception(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config-status")
async def get_config_status():
    """Returns the current engine configuration status"""
    try:
        settings: EngineSettings = config_manager.load_config()
        config = settings.model_dump()
        
        return {
            "has_custom_config": config.get("use_custom_params", False) or config.get("use_range_optimization", False),
            "mode": (
                "Range Optimization" if config.get("use_range_optimization")
                else ("Custom Parameters" if config.get("use_custom_params") 
                      else "Default Hierarchical")
            ),
            "last_updated": config.get("last_updated", "Never"),
            "latest_results": None  # Mock for development
        }
    except Exception as e:
        logger.exception(f"Error getting config status: {e}")
        return {
            "has_custom_config": False,
            "mode": "Default Hierarchical",
            "last_updated": "Never",
            "latest_results": None
        }

@router.post("/save-config")
async def save_config(config: ScenarioConfig):
    """Save engine configuration"""
    try:
        config_dict = config.dict()
        config_dict["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if not config_manager.save_config(config_dict):
            raise HTTPException(status_code=500, detail="Configuration file not writable")
        engine.update_config(config_dict)

        return {
            "message": "Configuration saved successfully",
            "config": config_dict
        }
    except HTTPException:
        raise
    except FileNotFoundError:
        logger.exception("Configuration file not found")
        raise HTTPException(status_code=500, detail="Configuration file not found")
    except PermissionError:
        logger.exception("Permission denied writing configuration file")
        raise HTTPException(status_code=500, detail="Configuration file not writable")
    except OSError as e:
        logger.exception(f"OS error while saving configuration: {e}")
        raise HTTPException(status_code=500, detail="Configuration file not writable")
    except Exception as e:
        logger.exception(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving configuration: {str(e)}")

@router.post("/scenario-analysis")
async def run_scenario_analysis(config: ScenarioConfig):
    """Development helper that returns mocked scenario analysis results.

    Parameters
    ----------
    config : ScenarioConfig
        Configuration payload provided by the client.
    """
    try:
        start_time = time.time()
        
        # Save configuration first
        config_dict = config.dict()
        config_dict["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if not config_manager.save_config(config_dict):
            raise HTTPException(status_code=500, detail="Configuration file not writable")
        
        # Load customer data for metrics
        customers_df = data_loader.load_customers()
        total_customers = len(customers_df) if not customers_df.empty else 0
        
        # Mock scenario analysis results for development
        execution_time = time.time() - start_time
        
        # Generate realistic mock results
        import random
        random.seed(42)  # Consistent results
        
        mock_results = {
            "scenario_config": config_dict,
            "execution_details": {
                "sample_size": min(50, total_customers),
                "total_customers": total_customers,
                "processed_customers": min(50, total_customers),  
                "processing_errors": 0,
                "execution_time_seconds": round(execution_time + random.uniform(2, 8), 2)
            },
            "actual_metrics": {
                "total_offers": random.randint(500, 2000),
                "average_npv_per_offer": random.randint(8000, 15000),
                "total_portfolio_npv": random.randint(5000000, 20000000),
                "offers_per_customer": round(random.uniform(2.5, 4.5), 1),
                "tier_distribution": {
                    "Refresh": random.randint(100, 300),
                    "Upgrade": random.randint(200, 500), 
                    "Max Upgrade": random.randint(50, 200)
                }
            },
            "mode_info": {
                "mode": (
                    "Range Optimization" if config_dict.get("use_range_optimization")
                    else ("Custom Parameters" if config_dict.get("use_custom_params")
                          else "Default Hierarchical")
                ),
                "parameter_combinations": random.randint(50, 500) if config_dict.get("use_range_optimization") else 0
            }
        }
        
        # Save mock results
        try:
            results_file = Path("scenario_results.json")
            with open(results_file, "w") as f:
                json.dump(mock_results, f, indent=2)
        except FileNotFoundError:
            logger.exception("Scenario results file not found")
            raise HTTPException(status_code=500, detail="Scenario results file not writable")
        except PermissionError:
            logger.exception("Permission denied writing scenario results file")
            raise HTTPException(status_code=500, detail="Scenario results file not writable")
        except OSError as e:
            logger.exception(f"OS error while saving scenario results: {e}")
            raise HTTPException(status_code=500, detail="Scenario results file not writable")
        except Exception as e:
            logger.exception(f"Could not save scenario results: {e}")
            raise HTTPException(status_code=500, detail="Scenario results file not writable")
            
        return mock_results
        
    except Exception as e:
        logger.exception(f"Error in scenario analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {str(e)}")

@router.get("/inventory")
async def get_inventory():
    """Get available inventory"""
    try:
        inventory = data_loader.load_inventory()
        return inventory.to_dict(orient="records")
    except FileNotFoundError:
        logger.exception("Inventory data file not found")
        raise HTTPException(status_code=500, detail="Inventory data file not found")
    except PermissionError:
        logger.exception("Permission denied reading inventory data file")
        raise HTTPException(status_code=500, detail="Inventory data file not readable")
    except OSError as e:
        logger.exception(f"OS error while loading inventory: {e}")
        raise HTTPException(status_code=500, detail="Failed to load inventory")
    except Exception as e:
        logger.exception(f"Error loading inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
