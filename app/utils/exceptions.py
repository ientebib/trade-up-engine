"""
Custom exception hierarchy for Trade-Up Engine
Provides specific error types for better error handling and debugging
"""
from typing import Optional, Dict, Any


class TradeUpEngineError(Exception):
    """Base exception for all Trade-Up Engine errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


# Data-related exceptions
class DataError(TradeUpEngineError):
    """Base class for data-related errors"""
    pass


class CustomerNotFoundError(DataError):
    """Raised when a customer ID is not found"""
    
    def __init__(self, customer_id: str):
        super().__init__(
            f"Customer not found: {customer_id}",
            error_code="CUSTOMER_NOT_FOUND",
            details={"customer_id": customer_id}
        )


class InventoryNotFoundError(DataError):
    """Raised when inventory item is not found"""
    
    def __init__(self, car_id: str):
        super().__init__(
            f"Car not found in inventory: {car_id}",
            error_code="CAR_NOT_FOUND",
            details={"car_id": car_id}
        )


class DataLoadError(DataError):
    """Raised when data cannot be loaded from source"""
    
    def __init__(self, source: str, reason: str):
        super().__init__(
            f"Failed to load data from {source}: {reason}",
            error_code="DATA_LOAD_ERROR",
            details={"source": source, "reason": reason}
        )


# Database-related exceptions
class DatabaseError(TradeUpEngineError):
    """Base class for database-related errors"""
    pass


class ConnectionPoolExhaustedError(DatabaseError):
    """Raised when connection pool is exhausted"""
    
    def __init__(self, max_connections: int):
        super().__init__(
            f"Connection pool exhausted (max: {max_connections})",
            error_code="CONNECTION_POOL_EXHAUSTED",
            details={"max_connections": max_connections}
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Database connection failed: {reason}",
            error_code="DATABASE_CONNECTION_FAILED",
            details={"reason": reason}
        )


class CircuitBreakerOpenError(DatabaseError):
    """Raised when circuit breaker is open"""
    
    def __init__(self, service: str, recovery_time: int):
        super().__init__(
            f"Service {service} is temporarily unavailable. Try again in {recovery_time} seconds.",
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service, "recovery_time": recovery_time}
        )


# Business logic exceptions
class BusinessLogicError(TradeUpEngineError):
    """Base class for business logic errors"""
    pass


class NoViableOffersError(BusinessLogicError):
    """Raised when no viable offers can be generated"""
    
    def __init__(self, customer_id: str, reason: str):
        super().__init__(
            f"No viable offers for customer {customer_id}: {reason}",
            error_code="NO_VIABLE_OFFERS",
            details={"customer_id": customer_id, "reason": reason}
        )


class InvalidOfferParametersError(BusinessLogicError):
    """Raised when offer parameters are invalid"""
    
    def __init__(self, parameter: str, value: Any, reason: str):
        super().__init__(
            f"Invalid offer parameter {parameter}={value}: {reason}",
            error_code="INVALID_OFFER_PARAMETERS",
            details={"parameter": parameter, "value": value, "reason": reason}
        )


class CalculationError(BusinessLogicError):
    """Raised when financial calculations fail"""
    
    def __init__(self, calculation_type: str, reason: str):
        super().__init__(
            f"Calculation failed for {calculation_type}: {reason}",
            error_code="CALCULATION_ERROR",
            details={"calculation_type": calculation_type, "reason": reason}
        )


# Configuration exceptions
class ConfigurationError(TradeUpEngineError):
    """Base class for configuration errors"""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""
    
    def __init__(self, config_key: str):
        super().__init__(
            f"Required configuration missing: {config_key}",
            error_code="MISSING_CONFIGURATION",
            details={"config_key": config_key}
        )


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration value is invalid"""
    
    def __init__(self, config_key: str, value: Any, reason: str):
        super().__init__(
            f"Invalid configuration {config_key}={value}: {reason}",
            error_code="INVALID_CONFIGURATION",
            details={"config_key": config_key, "value": value, "reason": reason}
        )


# Cache exceptions
class CacheError(TradeUpEngineError):
    """Base class for cache-related errors"""
    pass


class CacheInvalidationError(CacheError):
    """Raised when cache invalidation fails"""
    
    def __init__(self, pattern: str, reason: str):
        super().__init__(
            f"Failed to invalidate cache pattern {pattern}: {reason}",
            error_code="CACHE_INVALIDATION_ERROR",
            details={"pattern": pattern, "reason": reason}
        )


# Request processing exceptions
class RequestError(TradeUpEngineError):
    """Base class for request processing errors"""
    pass


class RequestTimeoutError(RequestError):
    """Raised when request times out"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            f"Request timeout: {operation} took longer than {timeout_seconds} seconds",
            error_code="REQUEST_TIMEOUT",
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


class BulkRequestLimitError(RequestError):
    """Raised when bulk request exceeds limits"""
    
    def __init__(self, requested: int, limit: int):
        super().__init__(
            f"Bulk request exceeds limit: requested {requested}, limit {limit}",
            error_code="BULK_REQUEST_LIMIT_EXCEEDED",
            details={"requested": requested, "limit": limit}
        )


class ConcurrentRequestLimitError(RequestError):
    """Raised when concurrent request limit is reached"""
    
    def __init__(self, limit: int):
        super().__init__(
            f"Concurrent request limit reached: {limit}",
            error_code="CONCURRENT_REQUEST_LIMIT",
            details={"limit": limit}
        )


# Validation exceptions
class ValidationError(TradeUpEngineError):
    """Base class for validation errors"""
    pass


class InputValidationError(ValidationError):
    """Raised when input validation fails"""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Invalid input for {field}: {reason}",
            error_code="INPUT_VALIDATION_ERROR",
            details={"field": field, "value": str(value), "reason": reason}
        )


class DataIntegrityError(ValidationError):
    """Raised when data integrity checks fail"""
    
    def __init__(self, entity: str, reason: str):
        super().__init__(
            f"Data integrity error for {entity}: {reason}",
            error_code="DATA_INTEGRITY_ERROR",
            details={"entity": entity, "reason": reason}
        )


# Helper function to convert standard exceptions
def wrap_exception(e: Exception) -> TradeUpEngineError:
    """
    Wrap standard exceptions in custom exception types
    
    Args:
        e: Standard exception
        
    Returns:
        Appropriate TradeUpEngineError subclass
    """
    error_mapping = {
        # Database errors
        "OperationalError": DatabaseConnectionError,
        "InterfaceError": DatabaseConnectionError,
        "ProgrammingError": DatabaseError,
        
        # Value errors
        "ValueError": InvalidOfferParametersError,
        "TypeError": InvalidOfferParametersError,
        
        # Key errors
        "KeyError": MissingConfigurationError,
        
        # Timeout errors
        "TimeoutError": RequestTimeoutError,
        
        # Connection errors
        "ConnectionError": DatabaseConnectionError,
        "ConnectionRefusedError": DatabaseConnectionError,
        "ConnectionResetError": DatabaseConnectionError,
    }
    
    error_class = error_mapping.get(type(e).__name__, TradeUpEngineError)
    
    # Create appropriate exception
    if error_class == InvalidOfferParametersError:
        return error_class("unknown", None, str(e))
    elif error_class == MissingConfigurationError:
        return error_class(str(e))
    elif error_class == RequestTimeoutError:
        return error_class("unknown", 0)
    else:
        return error_class(str(e))