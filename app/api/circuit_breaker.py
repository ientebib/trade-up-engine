"""
Circuit Breaker Monitoring API
Provides endpoints to monitor and manage circuit breakers
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from data.circuit_breaker_factory import (
    CircuitBreakerFactory,
    get_redshift_breaker,
    get_cache_breaker
)
from data.circuit_breaker import CircuitState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/circuit-breakers", tags=["monitoring"])


@router.get("/status")
async def get_all_circuit_breakers() -> Dict[str, Any]:
    """
    Get status of all circuit breakers in the system.
    
    Returns:
        Dict containing status of each circuit breaker:
        {
            "circuit_breakers": {
                "redshift": {
                    "state": "closed",
                    "failure_count": 0,
                    "last_failure": null,
                    "threshold": 3,
                    "recovery_timeout": 120
                },
                ...
            },
            "summary": {
                "total": 2,
                "closed": 1,
                "open": 0,
                "half_open": 1
            }
        }
    """
    try:
        all_statuses = CircuitBreakerFactory.get_all_statuses()
        
        # Calculate summary
        summary = {
            "total": len(all_statuses),
            "closed": sum(1 for s in all_statuses.values() if s["state"] == "closed"),
            "open": sum(1 for s in all_statuses.values() if s["state"] == "open"),
            "half_open": sum(1 for s in all_statuses.values() if s["state"] == "half_open")
        }
        
        return {
            "circuit_breakers": all_statuses,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{service_name}")
async def get_circuit_breaker_status(service_name: str) -> Dict[str, Any]:
    """
    Get status of a specific circuit breaker.
    
    Args:
        service_name: Name of the service (e.g., 'redshift', 'cache')
        
    Returns:
        Circuit breaker status
    """
    try:
        all_statuses = CircuitBreakerFactory.get_all_statuses()
        
        if service_name not in all_statuses:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker for service '{service_name}' not found"
            )
        
        return {
            "service": service_name,
            "status": all_statuses[service_name]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{service_name}")
async def reset_circuit_breaker(service_name: str) -> Dict[str, str]:
    """
    Manually reset a circuit breaker to closed state.
    
    Args:
        service_name: Name of the service to reset
        
    Returns:
        Success message
    """
    try:
        success = CircuitBreakerFactory.reset_breaker(service_name)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker for service '{service_name}' not found"
            )
        
        logger.info(f"Circuit breaker for '{service_name}' reset by user")
        
        return {
            "message": f"Circuit breaker for '{service_name}' has been reset",
            "service": service_name,
            "new_state": "closed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-all")
async def reset_all_circuit_breakers() -> Dict[str, Any]:
    """
    Reset all circuit breakers to closed state.
    
    Returns:
        Summary of reset operation
    """
    try:
        # Get status before reset
        before_statuses = CircuitBreakerFactory.get_all_statuses()
        open_count = sum(1 for s in before_statuses.values() if s["state"] == "open")
        
        # Reset all
        CircuitBreakerFactory.reset_all()
        
        logger.info(f"All circuit breakers reset by user (was {open_count} open)")
        
        return {
            "message": "All circuit breakers have been reset",
            "breakers_reset": len(before_statuses),
            "previously_open": open_count
        }
    except Exception as e:
        logger.error(f"Failed to reset all circuit breakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def circuit_breaker_health_check() -> Dict[str, Any]:
    """
    Health check for critical circuit breakers.
    
    Returns 200 if all critical breakers are healthy (closed or half-open).
    Returns 503 if any critical breaker is open.
    """
    try:
        # Define critical services
        critical_services = ["redshift", "cache"]
        
        all_statuses = CircuitBreakerFactory.get_all_statuses()
        
        unhealthy = []
        for service in critical_services:
            if service in all_statuses and all_statuses[service]["state"] == "open":
                unhealthy.append(service)
        
        if unhealthy:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "message": "Critical circuit breakers are open",
                    "open_breakers": unhealthy
                }
            )
        
        return {
            "status": "healthy",
            "message": "All critical circuit breakers are operational",
            "critical_services": critical_services,
            "statuses": {
                service: all_statuses.get(service, {"state": "not_found"})
                for service in critical_services
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Circuit breaker health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": f"Health check failed: {str(e)}"
            }
        )