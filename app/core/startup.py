"""
Application startup events
"""
import logging
from data.loader import data_loader
from . import data

logger = logging.getLogger(__name__)


async def startup_event():
    """Load data on startup"""
    logger.info("🚀 Starting Modern Trade-Up Engine...")
    
    try:
        # Load customer data
        data.customers_df = data_loader.load_customers()
        
        # Load inventory data  
        data.inventory_df = data_loader.load_inventory()
        
        logger.info(f"✅ Loaded {len(data.customers_df)} customers and {len(data.inventory_df)} inventory items")
        
        # Initialize the engine
        from engine.basic_matcher import basic_matcher
        logger.info("🎯 Simple engine initialized and ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        # Continue running with empty DataFrames
        pass