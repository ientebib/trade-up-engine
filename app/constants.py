"""
Application-wide constants to eliminate magic numbers and improve code clarity.
"""

# =============================================================================
# FINANCIAL CONSTANTS - MOVED TO CONFIG/SCHEMA.PY
# =============================================================================
# All financial constants have been moved to the centralized configuration system.
# Use the config facade to access these values:
#
# from config.facade import get, get_decimal
#
# Examples:
# - Payment tiers: get('tiers.refresh.min'), get('tiers.refresh.max')
# - Service fees: get_decimal('fees.service.percentage')
# - Kavak Total: get_decimal('fees.kavak_total.amount')
#
# The following imports provide backward compatibility during migration:
from config.facade import get, get_decimal

# Payment Delta Tiers (backward compatibility)
REFRESH_TIER_MIN = float(get_decimal('tiers.refresh.min', -0.05))
REFRESH_TIER_MAX = float(get_decimal('tiers.refresh.max', 0.05))
UPGRADE_TIER_MIN = float(get_decimal('tiers.upgrade.min', 0.05))
UPGRADE_TIER_MAX = float(get_decimal('tiers.upgrade.max', 0.25))
MAX_UPGRADE_TIER_MIN = float(get_decimal('tiers.max_upgrade.min', 0.25))
MAX_UPGRADE_TIER_MAX = float(get_decimal('tiers.max_upgrade.max', 1.0))

# Interest Rate Adjustments by Term
TERM_60_RATE_ADJUSTMENT = float(get_decimal('terms.rate_adjustment_60', 0.01))
TERM_72_RATE_ADJUSTMENT = float(get_decimal('terms.rate_adjustment_72', 0.015))

# NPV Calculation Constants
NPV_BASE_MARGIN_DEDUCTION = float(get_decimal('financial.npv_base_margin_deduction', 2000))

# Default Fee Percentages (backward compatibility)
DEFAULT_SERVICE_FEE_PCT = float(get_decimal('fees.service.percentage', 0.04))
DEFAULT_CXA_PCT = float(get_decimal('fees.cxa.percentage', 0.04))
DEFAULT_CAC_BONUS = float(get_decimal('fees.cac_bonus.default', 0))

# Kavak Total Default Amount
KAVAK_TOTAL_DEFAULT_AMOUNT = float(get_decimal('fees.kavak_total.amount', 25000))

# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

# Pagination Limits
MAX_PAGE_NUMBER = 10000          # Maximum allowed page number for pagination
MAX_ITEMS_PER_PAGE = 100         # Maximum items per page in API responses
DEFAULT_ITEMS_PER_PAGE = 20      # Default items per page

# Bulk Request Limits
MAX_BULK_REQUEST_SIZE = 100      # Maximum customers in a bulk request

# Financial Validation Limits
MAX_CURRENCY_AMOUNT = 100_000_000  # Maximum allowed currency amount (100M MXN)
MIN_CURRENCY_AMOUNT = 0            # Minimum allowed currency amount

# String Length Limits
MAX_SEARCH_TERM_LENGTH = 100     # Maximum length for search terms
MAX_CUSTOMER_ID_LENGTH = 50      # Maximum length for customer IDs

# =============================================================================
# BUSINESS LOGIC CONSTANTS
# =============================================================================

# Risk Profile Constants
DEFAULT_RISK_PROFILE_INDEX = 25  # Fallback index for unmapped risk profiles
MAX_RISK_PROFILE_INDEX = 25      # Maximum risk profile index

# Data Quality Constants
MIN_VALID_CAR_PRICE = 50000      # Minimum valid car price (50k MXN)
MAX_VALID_CAR_PRICE = 2_000_000  # Maximum valid car price (2M MXN)
MIN_VALID_MONTHLY_PAYMENT = 1000 # Minimum valid monthly payment
MAX_VALID_MONTHLY_PAYMENT = 50000 # Maximum valid monthly payment

# Term Options
VALID_LOAN_TERMS = [12, 24, 36, 48, 60, 72]  # Valid loan term options in months
DEFAULT_LOAN_TERM = 48                        # Default loan term

# =============================================================================
# SYSTEM CONSTANTS
# =============================================================================

# Timeout Values (in seconds)
DEFAULT_REQUEST_TIMEOUT = 30     # Default request timeout
DB_CONNECTION_TIMEOUT = 5        # Database connection timeout
BULK_PROCESSING_TIMEOUT = 300    # Bulk processing timeout (5 minutes)

# Thread Pool Limits
DEFAULT_MAX_WORKERS = 14         # Default max workers for thread pool
MIN_WORKERS = 1                  # Minimum workers
MAX_WORKERS = 32                 # Maximum workers

# Cache Constants
DEFAULT_CACHE_TTL = 300          # Default cache TTL (5 minutes)
MAX_CACHE_SIZE = 1000            # Maximum cache entries

# =============================================================================
# DISPLAY CONSTANTS
# =============================================================================

# Number Formatting
CURRENCY_PRECISION = 2           # Decimal places for currency display
PERCENTAGE_PRECISION = 4         # Decimal places for percentage display
INTEREST_RATE_PRECISION = 6      # Decimal places for interest rates

# Status Messages
SUCCESS_STATUS = "success"
ERROR_STATUS = "error"
PENDING_STATUS = "pending"
IN_PROGRESS_STATUS = "in_progress"

# =============================================================================
# HTTP STATUS CONSTANTS
# =============================================================================

# Common HTTP Status Codes (for consistency)
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_TIMEOUT = 504

# =============================================================================
# ENUM-LIKE CONSTANTS
# =============================================================================

class OfferTiers:
    """Offer tier classification constants"""
    REFRESH = "refresh"
    UPGRADE = "upgrade"
    MAX_UPGRADE = "max_upgrade"

class RiskProfiles:
    """Risk profile constants"""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    A1 = "A1"
    A2 = "A2"
    B = "B"
    # Add more as needed

class DataTypes:
    """Data type validation constants"""
    INVENTORY = "inventory"
    CUSTOMERS = "customers"
    OFFERS = "offers"

class LogLevels:
    """Logging level constants"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# =============================================================================
# DATABASE CONNECTION POOL CONSTANTS
# =============================================================================

# Connection pool settings for Redshift
MIN_CONNECTIONS = int(get('database.pool.min_connections', 2))
MAX_CONNECTIONS = int(get('database.pool.max_connections', 10))
CONNECTION_TIMEOUT = int(get('database.pool.connection_timeout', 120))
DATABASE_QUERY_TIMEOUT = int(get('database.pool.query_timeout', 300))
POOL_RECYCLE_TIME = int(get('database.pool.recycle_time', 3600))

# =============================================================================
# CACHE MANAGEMENT CONSTANTS
# =============================================================================

# Cache TTL settings (backward compatibility)
DEFAULT_CACHE_TTL_HOURS = float(get('cache.default_ttl_hours', 4.0))
INVENTORY_CACHE_TTL_HOURS = float(get('cache.inventory_ttl_hours', 4.0))
CUSTOMER_CACHE_TTL_HOURS = float(get('cache.customer_ttl_hours', 0.5))

# =============================================================================
# REQUEST TIMEOUT CONSTANTS
# =============================================================================

# Timeout settings for different request types
BULK_REQUEST_TIMEOUT = 60               # Bulk request timeout in seconds
AMORTIZATION_TIMEOUT = 30               # Amortization calculation timeout
HEALTH_CHECK_TIMEOUT = 10               # Health check timeout
OFFER_GENERATION_TIMEOUT = 45           # Single offer generation timeout