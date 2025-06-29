"""
Custom exceptions for the Trade-Up Engine application
"""


class BaseAPIException(Exception):
    """Base exception for all API errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class CustomerNotFoundError(BaseAPIException):
    """Raised when a customer is not found"""
    def __init__(self, customer_id: str):
        super().__init__(f"Customer {customer_id} not found", 404)


class DatabaseError(BaseAPIException):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message, 503)


class ValidationError(BaseAPIException):
    """Raised when input validation fails"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class CacheError(BaseAPIException):
    """Raised when cache operations fail"""
    def __init__(self, message: str = "Cache error occurred"):
        super().__init__(message, 500)


class InventoryNotFoundError(BaseAPIException):
    """Raised when inventory item is not found"""
    def __init__(self, car_id: str):
        super().__init__(f"Car {car_id} not found in inventory", 404)


class CalculationError(BaseAPIException):
    """Raised when calculations fail"""
    def __init__(self, message: str = "Calculation error occurred"):
        super().__init__(message, 500)


class ConfigurationError(BaseAPIException):
    """Raised when configuration is invalid"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429)