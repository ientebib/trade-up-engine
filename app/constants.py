"""
Application-wide constants to eliminate magic numbers and improve code clarity.
"""

# =============================================================================
# FINANCIAL CONSTANTS
# =============================================================================

# Payment Delta Tiers (for offer categorization)
REFRESH_TIER_MIN = -0.05        # -5% minimum payment change for refresh tier
REFRESH_TIER_MAX = 0.05         # +5% maximum payment change for refresh tier
UPGRADE_TIER_MIN = 0.05         # +5% minimum payment change for upgrade tier  
UPGRADE_TIER_MAX = 0.25         # +25% maximum payment change for upgrade tier
MAX_UPGRADE_TIER_MIN = 0.25     # +25% minimum payment change for max upgrade tier
MAX_UPGRADE_TIER_MAX = 1.0      # +100% maximum payment change for max upgrade tier

# Interest Rate Adjustments by Term
TERM_60_RATE_ADJUSTMENT = 0.01   # 1% additional interest for 60-month terms
TERM_72_RATE_ADJUSTMENT = 0.015  # 1.5% additional interest for 72-month terms

# NPV Calculation Constants
NPV_BASE_MARGIN_DEDUCTION = 2000  # Base amount deducted from margin for NPV

# Default Fee Percentages (fallback values)
DEFAULT_SERVICE_FEE_PCT = 0.04   # 4% service fee percentage
DEFAULT_CXA_PCT = 0.04           # 4% CXA (opening) fee percentage
DEFAULT_CAC_BONUS = 0            # No CAC bonus by default

# Kavak Total Default Amount
KAVAK_TOTAL_DEFAULT_AMOUNT = 25000  # Default Kavak Total amount in MXN

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
MIN_CONNECTIONS = 2                     # Minimum connections in pool
MAX_CONNECTIONS = 10                    # Maximum connections in pool
CONNECTION_TIMEOUT = 30                 # Connection timeout in seconds
DATABASE_QUERY_TIMEOUT = 60             # Query execution timeout in seconds
POOL_RECYCLE_TIME = 3600                # Recycle connections after 1 hour

# =============================================================================
# CACHE MANAGEMENT CONSTANTS
# =============================================================================

# Cache TTL settings
DEFAULT_CACHE_TTL_HOURS = 4.0           # Default cache TTL in hours
INVENTORY_CACHE_TTL_HOURS = 4.0         # Inventory-specific cache TTL
CUSTOMER_CACHE_TTL_HOURS = 0.5          # Customer data cache TTL (30 minutes)

# =============================================================================
# REQUEST TIMEOUT CONSTANTS
# =============================================================================

# Timeout settings for different request types
BULK_REQUEST_TIMEOUT = 60               # Bulk request timeout in seconds
AMORTIZATION_TIMEOUT = 30               # Amortization calculation timeout
HEALTH_CHECK_TIMEOUT = 10               # Health check timeout
OFFER_GENERATION_TIMEOUT = 45           # Single offer generation timeout