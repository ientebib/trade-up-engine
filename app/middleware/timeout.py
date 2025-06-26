"""
Request Timeout Middleware
Enforces timeout on long-running requests
"""
import asyncio
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.middleware.request_id import get_request_id
from app.constants import (
    DEFAULT_REQUEST_TIMEOUT,
    BULK_REQUEST_TIMEOUT,
    AMORTIZATION_TIMEOUT,
    HEALTH_CHECK_TIMEOUT
)

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce timeout on requests to prevent resource exhaustion"""
    
    def __init__(self, app, timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID if available
        request_id = get_request_id(request)
        
        # Different timeouts for different endpoints
        path = request.url.path
        timeout = self.timeout_seconds
        
        # Longer timeout for bulk operations
        if "/bulk" in path:
            timeout = BULK_REQUEST_TIMEOUT
        elif "/amortization" in path:
            timeout = AMORTIZATION_TIMEOUT
        elif "/health" in path:
            timeout = HEALTH_CHECK_TIMEOUT
        
        try:
            # Create task with timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timed out after {timeout}s: {request.method} {path}")
            
            # Return appropriate error response
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=504,
                    content={
                        "detail": "Request timeout",
                        "request_id": request_id,
                        "timeout_seconds": timeout,
                        "message": f"The request exceeded the {timeout} second timeout limit"
                    },
                    headers={"X-Request-ID": request_id}
                )
            else:
                # For web pages, return a simple timeout page
                return Response(
                    content=f"<h1>Request Timeout</h1><p>Request ID: {request_id}</p>",
                    status_code=504,
                    headers={"Content-Type": "text/html", "X-Request-ID": request_id}
                )