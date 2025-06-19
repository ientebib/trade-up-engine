"""
Trade-Up Engine API Routes
Development version with mock data support
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import json
import logging
from pathlib import Path

from core.engine import TradeUpEngine
from core.data_loader_dev import dev_data_loader
from core.config_manager import ConfigManager

# Initialize router
router = APIRouter()

# Initialize components
engine = TradeUpEngine()
data_loader = dev_data_loader
config_manager = ConfigManager()

@router.get("/customers")
async def get_customers():
    """Get all customers"""
    try:
        customers = data_loader.load_customers()
        return {"customers": customers.to_dict(orient='records')}
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
async def generate_offers(customer_id: str):
    """Generate trade-up offers for a customer"""
    try:
        # Load data
        customers = data_loader.load_customers()
        inventory = data_loader.load_inventory()
        
        # Get customer
        customer = customers[customers['customer_id'] == customer_id]
        if customer.empty:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Load current config
        config = config_manager.load_config()
        engine.update_config(config)
        
        # Generate offers
        offers = engine.generate_offers(customer.iloc[0].to_dict(), inventory)
        
        return {
            "customer_id": customer_id,
            "offers": offers.to_dict(orient='records') if not offers.empty else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating offers for customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config():
    """Get current engine configuration"""
    try:
        return {"config": config_manager.load_config()}
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-config")
async def save_config(config: Dict):
    """Save engine configuration"""
    try:
        config_manager.save_config(config)
        engine.update_config(config)
        return {"message": "Configuration saved successfully"}
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory")
async def get_inventory():
    """Get available inventory"""
    try:
        inventory = data_loader.load_inventory()
        return {"inventory": inventory.to_dict(orient='records')}
    except Exception as e:
        logging.error(f"Error loading inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
