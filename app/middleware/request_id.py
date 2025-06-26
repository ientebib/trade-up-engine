"""
Request ID Middleware
Adds unique request IDs for tracking and debugging
"""
import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.utils.metrics import metrics_collector

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracking"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Add to logging context
        logger.info(f"🆔 Request {request_id}: {request.method} {request.url.path}")
        
        # Track timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log completion
            duration = time.time() - start_time
            logger.info(f"✅ Request {request_id} completed in {duration:.3f}s with status {response.status_code}")
            
            # Track metrics
            metrics_collector.track_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            # Log error with request ID
            duration = time.time() - start_time
            logger.error(f"❌ Request {request_id} failed after {duration:.3f}s: {type(e).__name__}: {e}")
            
            # Track error metrics
            metrics_collector.track_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                duration=duration
            )
            metrics_collector.track_error(
                error_type=type(e).__name__,
                endpoint=request.url.path
            )
            
            # Create error response with request ID
            return Response(
                content=f"Internal Server Error (Request ID: {request_id})",
                status_code=500,
                headers={"X-Request-ID": request_id}
            )


def get_request_id(request: Request) -> str:
    """Get request ID from current request"""
    return getattr(request.state, "request_id", "unknown")


def get_request_id_from_context() -> str:
    """
    Get request ID from context (when request object is not available).
    Returns 'unknown' if no request context is available.
    
    This is used by error handlers and other utilities that don't have
    direct access to the request object.
    """
    # For now, return 'unknown' since we don't have async context vars set up
    # In a future enhancement, we could use contextvars to store the request ID
    return "unknown"