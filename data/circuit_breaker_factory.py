"""
Circuit Breaker Factory for per-service instances
Prevents one service failure from affecting others
"""
import logging
from typing import Dict, Optional
from threading import Lock

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class CircuitBreakerFactory:
    """
    Factory for creating and managing circuit breakers per service.
    
    This prevents cross-contamination where one failing service
    causes circuit breakers for other services to open.
    """
    
    _instances: Dict[str, CircuitBreaker] = {}
    _lock = Lock()
    
    @classmethod
    def get_breaker(cls,
                    service_name: str,
                    failure_threshold: int = 5,
                    recovery_timeout: int = 60,
                    expected_exception: type = Exception) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a specific service.
        
        Args:
            service_name: Unique identifier for the service
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
            
        Returns:
            CircuitBreaker instance for the service
        """
        with cls._lock:
            if service_name not in cls._instances:
                logger.info(f"Creating new circuit breaker for service: {service_name}")
                cls._instances[service_name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception
                )
            return cls._instances[service_name]
    
    @classmethod
    def get_all_statuses(cls) -> Dict[str, dict]:
        """Get status of all circuit breakers"""
        with cls._lock:
            return {
                service: breaker.get_status()
                for service, breaker in cls._instances.items()
            }
    
    @classmethod
    def reset_breaker(cls, service_name: str) -> bool:
        """
        Reset a specific circuit breaker.
        
        Args:
            service_name: Service to reset
            
        Returns:
            True if reset, False if service not found
        """
        with cls._lock:
            if service_name in cls._instances:
                cls._instances[service_name].reset()
                logger.info(f"Reset circuit breaker for service: {service_name}")
                return True
            return False
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers"""
        with cls._lock:
            for service_name, breaker in cls._instances.items():
                breaker.reset()
            logger.info(f"Reset all {len(cls._instances)} circuit breakers")
    
    @classmethod
    def remove_breaker(cls, service_name: str) -> bool:
        """
        Remove a circuit breaker (for testing or cleanup).
        
        Args:
            service_name: Service to remove
            
        Returns:
            True if removed, False if not found
        """
        with cls._lock:
            if service_name in cls._instances:
                del cls._instances[service_name]
                logger.info(f"Removed circuit breaker for service: {service_name}")
                return True
            return False


# Convenience functions for common services
def get_redshift_breaker() -> CircuitBreaker:
    """Get circuit breaker for Redshift connections"""
    return CircuitBreakerFactory.get_breaker(
        "redshift",
        failure_threshold=3,  # More sensitive for DB
        recovery_timeout=120  # Longer recovery for DB
    )


def get_api_breaker(api_name: str) -> CircuitBreaker:
    """Get circuit breaker for external API calls"""
    return CircuitBreakerFactory.get_breaker(
        f"api_{api_name}",
        failure_threshold=5,
        recovery_timeout=60
    )


def get_cache_breaker() -> CircuitBreaker:
    """Get circuit breaker for cache operations"""
    return CircuitBreakerFactory.get_breaker(
        "cache",
        failure_threshold=10,  # More tolerant for cache
        recovery_timeout=30   # Quick recovery for cache
    )


# Export commonly used items
__all__ = [
    'CircuitBreakerFactory',
    'get_redshift_breaker',
    'get_api_breaker', 
    'get_cache_breaker',
    'CircuitBreakerOpenError'
]