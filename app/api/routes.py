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
from core.schemas import EngineSettings

# Initialize router
router = APIRouter()

# Initialize components
engine = TradeUpEngine()
data_loader = dev_data_loader
config_manager = ConfigManager()

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
        return customers.to_dict(orient='records')
    except Exception as e:
        logging.error(f"Error loading customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customer/{customer_id}")
async def get_customer(customer_id: str):
    """Get specific customer details"""
    try:
        customers = data_loader.load_customers()
        customer = customers[customers['customer_id'] == customer_id]
        if customer.empty:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"customer": customer.iloc[0].to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error loading customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-offers")
async def generate_offers(request: OfferRequest) -> Dict:
    """Generate all possible Trade-Up offers for a single customer - Production API Compatible"""
    try:
        # Convert request to DataFrames
        inventory_df = data_loader.load_inventory()
        customer_dict = request.customer_data.dict()
        
        # Load current config and merge with request config
        config = config_manager.load_config()
        config_dict = {**config.dict(), **request.engine_config.dict()}
        
        # Update engine with current config
        engine.update_config(config_dict)
        
        # Generate offers
        offers_df = engine.generate_offers(customer_dict, inventory_df)
        
        if offers_df.empty:
            return {"message": "No valid offers found for this customer.", "offers": {}}
        
        # Group offers by tier (matching production format)
        offers_by_tier = {}
        if 'tier' in offers_df.columns:
            for tier, group in offers_df.groupby('tier'):
                offers_by_tier[tier] = group.to_dict(orient='records')
        else:
            # Fallback: put all offers in a single group
            offers_by_tier['All'] = offers_df.to_dict(orient='records')
        
        return {
            "message": f"Successfully generated {len(offers_df)} offers.",
            "offers": offers_by_tier
        }
        
    except Exception as e:
        logging.error(f"Error generating offers: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@router.post("/amortization-table")
async def amortization_table(offer: Dict):
    """Return full amortization table for a given offer"""
    try:
        # Mock amortization table for development
        table = []
        loan_amount = offer.get('loan_amount', 100000)
        monthly_payment = offer.get('monthly_payment', 5000)
        term_months = offer.get('term_months', 24)
        
        balance = loan_amount
        for month in range(1, term_months + 1):
            interest = balance * 0.01  # 1% monthly for demo
            principal = monthly_payment - interest
            balance = max(0, balance - principal)
            
            table.append({
                'month': month,
                'payment': monthly_payment,
                'principal': principal,
                'interest': interest,
                'balance': balance
            })
            
            if balance <= 0:
                break
                
        return {"table": table}
    except Exception as e:
        logging.error(f"Error generating amortization table: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate amortization table: {str(e)}")

@router.get("/config")
async def get_config():
    """Get current engine configuration"""
    try:
        return {"config": config_manager.load_config()}
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config-status")
async def get_config_status():
    """Returns the current engine configuration status"""
    try:
        config = config_manager.load_config()
        config_dict = config.dict()

        return {
            "has_custom_config": config_dict.get("use_custom_params", False) or config_dict.get("use_range_optimization", False),
            "mode": (
                "Range Optimization" if config_dict.get("use_range_optimization")
                else ("Custom Parameters" if config_dict.get("use_custom_params")
                      else "Default Hierarchical")
            ),
            "last_updated": config_dict.get("last_updated", "Never"),
            "latest_results": None  # Mock for development
        }
    except Exception as e:
        logging.error(f"Error getting config status: {e}")
        return {
            "has_custom_config": False,
            "mode": "Default Hierarchical", 
            "last_updated": "Never",
            "latest_results": None
        }

@router.post("/save-config")
async def save_config(config: EngineSettings):
    """Save engine configuration"""
    try:
        config.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

        config_manager.save_config(config)
        engine.update_config(config.dict())
        
        return {
            "message": "Configuration saved successfully",
            "config": config_dict
        }
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving configuration: {str(e)}")

@router.post("/scenario-analysis")
async def run_scenario_analysis(config: EngineSettings):
    """Run scenario analysis - Development version with mock results"""
    try:
        start_time = time.time()
        
        # Save configuration first
        config.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        config_manager.save_config(config)
        config_dict = config.dict()
        
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
            with open(results_file, 'w') as f:
                json.dump(mock_results, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not save scenario results: {e}")
            
        return mock_results
        
    except Exception as e:
        logging.error(f"Error in scenario analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {str(e)}")

@router.get("/inventory")
async def get_inventory():
    """Get available inventory"""
    try:
        inventory = data_loader.load_inventory()
        return inventory.to_dict(orient='records')
    except Exception as e:
        logging.error(f"Error loading inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
