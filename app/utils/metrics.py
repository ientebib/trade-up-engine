"""
Metrics and monitoring utilities for the Trade-Up Engine
"""
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and tracks application metrics"""
    
    def __init__(self):
        self.metrics = {
            "requests": {
                "total": 0,
                "by_endpoint": {},
                "by_status": {},
                "response_times": []
            },
            "offers": {
                "generated": 0,
                "by_tier": {"refresh": 0, "upgrade": 0, "max_upgrade": 0},
                "generation_times": [],
                "npv_values": []
            },
            "database": {
                "queries": 0,
                "connection_pool_hits": 0,
                "connection_pool_misses": 0,
                "query_times": []
            },
            "cache": {
                "hits": 0,
                "misses": 0,
                "invalidations": 0,
                "by_key": {}
            },
            "errors": {
                "total": 0,
                "by_type": {},
                "by_endpoint": {}
            },
            "system": {
                "start_time": datetime.now().isoformat(),
                "uptime_seconds": 0
            }
        }
        self.start_time = time.time()
    
    def track_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Track HTTP request metrics"""
        self.metrics["requests"]["total"] += 1
        
        # Track by endpoint
        key = f"{method} {endpoint}"
        if key not in self.metrics["requests"]["by_endpoint"]:
            self.metrics["requests"]["by_endpoint"][key] = 0
        self.metrics["requests"]["by_endpoint"][key] += 1
        
        # Track by status
        status_key = f"{status_code // 100}xx"
        if status_key not in self.metrics["requests"]["by_status"]:
            self.metrics["requests"]["by_status"][status_key] = 0
        self.metrics["requests"]["by_status"][status_key] += 1
        
        # Track response time (keep last 1000)
        self.metrics["requests"]["response_times"].append(duration)
        if len(self.metrics["requests"]["response_times"]) > 1000:
            self.metrics["requests"]["response_times"].pop(0)
    
    def track_offer_generation(self, tier: str, count: int, duration: float, total_npv: float = 0):
        """Track offer generation metrics"""
        self.metrics["offers"]["generated"] += count
        self.metrics["offers"]["by_tier"][tier] += count
        
        # Track generation time
        self.metrics["offers"]["generation_times"].append(duration)
        if len(self.metrics["offers"]["generation_times"]) > 1000:
            self.metrics["offers"]["generation_times"].pop(0)
        
        # Track NPV if provided
        if total_npv > 0:
            self.metrics["offers"]["npv_values"].append(total_npv)
            if len(self.metrics["offers"]["npv_values"]) > 1000:
                self.metrics["offers"]["npv_values"].pop(0)
    
    def track_database_query(self, query_type: str, duration: float):
        """Track database query metrics"""
        self.metrics["database"]["queries"] += 1
        self.metrics["database"]["query_times"].append(duration)
        if len(self.metrics["database"]["query_times"]) > 1000:
            self.metrics["database"]["query_times"].pop(0)
    
    def track_cache_hit(self, key: str):
        """Track cache hit"""
        self.metrics["cache"]["hits"] += 1
        if key not in self.metrics["cache"]["by_key"]:
            self.metrics["cache"]["by_key"][key] = {"hits": 0, "misses": 0}
        self.metrics["cache"]["by_key"][key]["hits"] += 1
    
    def track_cache_miss(self, key: str):
        """Track cache miss"""
        self.metrics["cache"]["misses"] += 1
        if key not in self.metrics["cache"]["by_key"]:
            self.metrics["cache"]["by_key"][key] = {"hits": 0, "misses": 0}
        self.metrics["cache"]["by_key"][key]["misses"] += 1
    
    def track_cache_invalidation(self, pattern: str):
        """Track cache invalidation"""
        self.metrics["cache"]["invalidations"] += 1
    
    def track_connection_pool_hit(self):
        """Track connection pool hit"""
        self.metrics["database"]["connection_pool_hits"] += 1
    
    def track_connection_pool_miss(self):
        """Track connection pool miss"""
        self.metrics["database"]["connection_pool_misses"] += 1
    
    def track_error(self, error_type: str, endpoint: Optional[str] = None):
        """Track error occurrence"""
        self.metrics["errors"]["total"] += 1
        
        # Track by error type
        if error_type not in self.metrics["errors"]["by_type"]:
            self.metrics["errors"]["by_type"][error_type] = 0
        self.metrics["errors"]["by_type"][error_type] += 1
        
        # Track by endpoint if provided
        if endpoint:
            if endpoint not in self.metrics["errors"]["by_endpoint"]:
                self.metrics["errors"]["by_endpoint"][endpoint] = 0
            self.metrics["errors"]["by_endpoint"][endpoint] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics with calculated statistics"""
        # Update uptime
        self.metrics["system"]["uptime_seconds"] = int(time.time() - self.start_time)
        
        # Calculate statistics
        stats = {
            "requests": {
                **self.metrics["requests"],
                "avg_response_time": self._calculate_avg(self.metrics["requests"]["response_times"]),
                "p95_response_time": self._calculate_percentile(self.metrics["requests"]["response_times"], 95),
                "p99_response_time": self._calculate_percentile(self.metrics["requests"]["response_times"], 99)
            },
            "offers": {
                **self.metrics["offers"],
                "avg_generation_time": self._calculate_avg(self.metrics["offers"]["generation_times"]),
                "avg_npv": self._calculate_avg(self.metrics["offers"]["npv_values"])
            },
            "database": {
                **self.metrics["database"],
                "avg_query_time": self._calculate_avg(self.metrics["database"]["query_times"]),
                "connection_pool_hit_rate": self._calculate_hit_rate(
                    self.metrics["database"]["connection_pool_hits"],
                    self.metrics["database"]["connection_pool_misses"]
                )
            },
            "cache": {
                **self.metrics["cache"],
                "hit_rate": self._calculate_hit_rate(
                    self.metrics["cache"]["hits"],
                    self.metrics["cache"]["misses"]
                )
            },
            "errors": self.metrics["errors"],
            "system": self.metrics["system"]
        }
        
        return stats
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        """Export metrics to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"metrics_{timestamp}.json"
        
        metrics = self.get_metrics()
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"📊 Metrics exported to {filepath}")
        return filepath
    
    def _calculate_avg(self, values: list) -> float:
        """Calculate average of values"""
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    def _calculate_percentile(self, values: list, percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Decorators for automatic metric tracking
def track_execution_time(metric_type: str):
    """Decorator to track function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if metric_type == "database":
                    metrics_collector.track_database_query(func.__name__, duration)
                elif metric_type == "offer_generation":
                    # Extract tier from result if available
                    tier = kwargs.get("tier", "unknown")
                    count = len(result) if isinstance(result, list) else 1
                    metrics_collector.track_offer_generation(tier, count, duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.track_error(type(e).__name__, func.__name__)
                raise
        return wrapper
    return decorator


def track_cache_access(key_prefix: str):
    """Decorator to track cache hits/misses"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{args[0] if args else 'default'}"
            result = func(*args, **kwargs)
            
            # Track hit or miss based on result
            if result is not None:
                metrics_collector.track_cache_hit(cache_key)
            else:
                metrics_collector.track_cache_miss(cache_key)
            
            return result
        return wrapper
    return decorator


class PerformanceMonitor:
    """Context manager for monitoring performance of code blocks"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            logger.error(f"❌ {self.operation_name} failed after {duration:.2f}s: {exc_val}")
            metrics_collector.track_error(exc_type.__name__, self.operation_name)
        else:
            logger.info(f"✅ {self.operation_name} completed in {duration:.2f}s")
        
        return False  # Don't suppress exceptions


# Health check metrics
def get_health_metrics() -> Dict[str, Any]:
    """Get health check metrics for monitoring"""
    metrics = metrics_collector.get_metrics()
    
    # Calculate health score (0-100)
    health_score = 100
    
    # Deduct points for errors
    error_rate = metrics["errors"]["total"] / max(metrics["requests"]["total"], 1)
    if error_rate > 0.05:  # More than 5% errors
        health_score -= 30
    elif error_rate > 0.01:  # More than 1% errors
        health_score -= 10
    
    # Deduct points for slow response times
    avg_response_time = metrics["requests"]["avg_response_time"]
    if avg_response_time > 5.0:  # More than 5 seconds average
        health_score -= 20
    elif avg_response_time > 2.0:  # More than 2 seconds average
        health_score -= 10
    
    # Deduct points for low cache hit rate
    cache_hit_rate = metrics["cache"]["hit_rate"]
    if cache_hit_rate < 50:  # Less than 50% hit rate
        health_score -= 10
    
    return {
        "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "unhealthy",
        "health_score": health_score,
        "uptime_seconds": metrics["system"]["uptime_seconds"],
        "request_count": metrics["requests"]["total"],
        "error_rate": error_rate,
        "avg_response_time": avg_response_time,
        "cache_hit_rate": cache_hit_rate,
        "details": metrics
    }