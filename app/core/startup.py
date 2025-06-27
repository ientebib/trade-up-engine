"""
Application startup events
"""
import logging
from data import database
from data.cache_manager import cache_manager

logger = logging.getLogger(__name__)


async def startup_event():
    """Initialize application - test connections only"""
    logger.info("🚀 Starting Modern Trade-Up Engine...")
    
    # Configure decimal precision for financial calculations
    logger.info("💰 Configuring decimal precision...")
    from engine.decimal_config import configure_decimal_context
    configure_decimal_context()
    
    # Initialize configuration system
    logger.info("🔧 Initializing configuration system...")
    from config.facade import reload as reload_config, validate as validate_config
    reload_config()
    
    # Validate configuration
    errors = validate_config()
    if errors:
        logger.warning(f"⚠️ Configuration validation warnings: {errors}")
    
    # Test database connections
    db_status = database.test_database_connection()
    
    # Check customer data
    if not db_status["customers"]["connected"]:
        logger.error("❌ CRITICAL: Cannot connect to customer data!")
        raise RuntimeError("Customer data unavailable")
    
    # Check Redshift connection (warning only - not critical)
    if not db_status["inventory"]["connected"]:
        logger.warning("⚠️ WARNING: Cannot connect to Redshift!")
        logger.warning("⚠️ Inventory data will not be available until connection is restored.")
        logger.warning(f"⚠️ Error: {db_status['inventory'].get('error', 'Unknown')}")
    
    logger.info(f"✅ Database connections verified:")
    logger.info(f"   - Customers: {db_status['customers']['count']} records")
    logger.info(f"   - Inventory: {db_status['inventory']['count']} cars")
    
    # Log cache status
    cache_status = cache_manager.get_status()
    logger.info(f"🗄️ Cache: {'Enabled' if cache_status['enabled'] else 'Disabled'} (TTL: {cache_status['default_ttl_hours']}h)")
    
    # Initialize the engine
    from engine.basic_matcher import basic_matcher
    
    # Initialize bulk request queue
    from app.services.bulk_queue import get_bulk_queue
    queue = get_bulk_queue()
    await queue.start()
    logger.info("📋 Bulk request queue initialized")
    
    logger.info("🎯 Engine initialized - ready for requests!")