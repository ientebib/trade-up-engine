"""
Common error handling utilities to reduce code duplication
"""
import logging
from functools import wraps
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.middleware.request_id import get_request_id_from_context
from app.utils.exceptions import (
    TradeUpEngineError,
    CustomerNotFoundError,
    NoViableOffersError,
    DatabaseConnectionError,
    CircuitBreakerOpenError,
    RequestTimeoutError,
    ValidationError as CustomValidationError,
    InvalidOfferParametersError
)

logger = logging.getLogger(__name__)


def handle_api_errors(operation_name: str = "operation", include_customer_id: bool = False):
    """
    Decorator to handle common API error patterns consistently.
    
    Args:
        operation_name: Name of the operation for logging
        include_customer_id: Whether to extract customer_id from request for logging
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_id = get_request_id_from_context()
            
            try:
                return await func(*args, **kwargs)
                
            # Handle custom exceptions first
            except CustomerNotFoundError as e:
                logger.warning(f"Customer not found in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=404, detail=e.to_dict())
                
            except NoViableOffersError as e:
                logger.info(f"No viable offers in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=404, detail=e.to_dict())
                
            except DatabaseConnectionError as e:
                logger.error(f"Database error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=503, detail=e.to_dict())
                
            except CircuitBreakerOpenError as e:
                logger.warning(f"Circuit breaker open in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=503, detail=e.to_dict())
                
            except RequestTimeoutError as e:
                logger.error(f"Timeout in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=504, detail=e.to_dict())
                
            except (CustomValidationError, InvalidOfferParametersError) as e:
                logger.warning(f"Validation error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=400, detail=e.to_dict())
                
            except TradeUpEngineError as e:
                # Catch-all for other custom exceptions
                logger.error(f"Application error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=500, detail=e.to_dict())
                
            # Handle standard exceptions
            except ValueError as e:
                # Business logic errors - usually 404 or 400
                logger.warning(f"Business logic error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=404, detail=str(e))
                
            except RuntimeError as e:
                # Service unavailable errors
                logger.error(f"Runtime error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=503, detail=str(e))
                
            except ConnectionError as e:
                # Database connection errors
                logger.error(f"Database connection error in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=503, detail="Database connection error")
                
            except TimeoutError as e:
                # Request timeout errors
                logger.error(f"Timeout in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=504, detail="Request timeout")
                
            except KeyError as e:
                # Missing required fields
                logger.error(f"Missing required field in {operation_name} (request: {request_id}): {e}")
                raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
                
            except Exception as e:
                # Unexpected errors
                error_type = type(e).__name__
                import traceback
                logger.error(f"Unexpected error in {operation_name} (request: {request_id}): {error_type}: {e}\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Internal error: {error_type}",
                    headers={"X-Request-ID": request_id} if request_id else None
                )
        
        return wrapper
    return decorator


def handle_service_errors(operation_name: str = "service operation"):
    """
    Decorator for service layer error handling.
    Catches and re-raises exceptions with better context.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except (ValueError, RuntimeError, ConnectionError, TimeoutError, KeyError):
                # Re-raise expected exceptions as-is for API layer to handle
                raise
                
            except Exception as e:
                # Wrap unexpected exceptions with context
                error_type = type(e).__name__
                logger.error(f"Unexpected error in {operation_name}: {error_type}: {e}")
                raise RuntimeError(f"Service error in {operation_name}: {error_type}")
        
        return wrapper
    return decorator


class BusinessLogicError(ValueError):
    """Raised when business logic validation fails"""
    pass


class ServiceUnavailableError(RuntimeError):
    """Raised when a required service is unavailable"""
    pass


class DataNotFoundError(ValueError):
    """Raised when requested data is not found"""
    pass


class ConfigurationError(RuntimeError):
    """Raised when configuration is invalid or missing"""
    pass


def log_and_raise_http_error(
    status_code: int,
    detail: str,
    operation: str,
    request_id: Optional[str] = None,
    error: Optional[Exception] = None
) -> None:
    """
    Log an error and raise an HTTPException with consistent format.
    
    Args:
        status_code: HTTP status code
        detail: Error detail for the user
        operation: Operation name for logging
        request_id: Optional request ID
        error: Optional underlying exception
    """
    if error:
        error_type = type(error).__name__
        logger.error(f"Error in {operation} (request: {request_id}): {error_type}: {error}")
    else:
        logger.error(f"Error in {operation} (request: {request_id}): {detail}")
    
    headers = {"X-Request-ID": request_id} if request_id else None
    raise HTTPException(status_code=status_code, detail=detail, headers=headers)


def create_error_response(
    error: Exception,
    operation: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response format.
    
    Args:
        error: The exception that occurred
        operation: Operation name
        request_id: Optional request ID
        
    Returns:
        Standardized error response dict
    """
    error_type = type(error).__name__
    
    if isinstance(error, ValueError):
        status_code = 400
        detail = str(error)
    elif isinstance(error, (RuntimeError, ServiceUnavailableError)):
        status_code = 503
        detail = "Service temporarily unavailable"
    elif isinstance(error, ConnectionError):
        status_code = 503
        detail = "Database connection error"
    elif isinstance(error, TimeoutError):
        status_code = 504
        detail = "Request timeout"
    elif isinstance(error, KeyError):
        status_code = 400
        detail = f"Missing required field: {error}"
    else:
        status_code = 500
        detail = f"Internal error: {error_type}"
    
    return {
        "status_code": status_code,
        "detail": detail,
        "error_type": error_type,
        "operation": operation,
        "request_id": request_id,
        "timestamp": logging.Formatter().formatTime(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ))
    }