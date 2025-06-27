"""
Tests to ensure middleware order is correct and locked down
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import time
import asyncio

from app.main import app
from app.middleware.timeout import TimeoutMiddleware
from app.middleware.sanitization import SanitizationMiddleware
from app.middleware.request_id import RequestIDMiddleware


class TestMiddlewareOrder:
    """Test that middleware is applied in the correct order"""
    
    def test_middleware_order_is_correct(self):
        """Verify middleware is added in the correct order"""
        # Get middleware stack
        middleware_stack = []
        for middleware in app.user_middleware:
            middleware_stack.append(middleware.cls)
        
        # Expected order (added in reverse, executed in order)
        # TimeoutMiddleware should be innermost (added first, executed last)
        expected_order = [
            RequestIDMiddleware,
            SanitizationMiddleware, 
            TimeoutMiddleware
        ]
        
        assert middleware_stack == expected_order, (
            f"Middleware order is incorrect. "
            f"Expected: {[m.__name__ for m in expected_order]}, "
            f"Got: {[m.__name__ for m in middleware_stack]}"
        )
    
    def test_request_id_is_first(self):
        """Request ID should be added before other middleware runs"""
        client = TestClient(app)
        
        response = client.get("/api/health")
        
        # Request ID should be in response headers
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_sanitization_runs_before_timeout(self):
        """Sanitization should clean input before timeout is applied"""
        client = TestClient(app)
        
        # Send request with potentially malicious input
        response = client.get("/api/customers", params={
            "search": "<script>alert('xss')</script>",
            "limit": "10"
        })
        
        # Request should succeed (not timeout) and be sanitized
        assert response.status_code in [200, 422]  # 422 if sanitized value is invalid
    
    def test_timeout_is_innermost(self):
        """Timeout should wrap the actual request processing"""
        client = TestClient(app)
        
        # Create a slow endpoint for testing
        @app.get("/test/slow")
        async def slow_endpoint():
            await asyncio.sleep(35)  # Longer than 30s timeout
            return {"message": "Should not reach here"}
        
        # This should timeout
        start_time = time.time()
        response = client.get("/test/slow")
        elapsed_time = time.time() - start_time
        
        # Should timeout around 30 seconds
        assert elapsed_time < 35, "Request did not timeout as expected"
        assert response.status_code == 504  # Gateway timeout
    
    def test_middleware_execution_order_with_logging(self):
        """Verify middleware executes in the correct order using logging"""
        execution_order = []
        
        # Patch each middleware to track execution
        with patch.object(RequestIDMiddleware, '__call__', 
                         side_effect=lambda *args, **kwargs: execution_order.append('RequestID') or 
                         RequestIDMiddleware.__call__(*args, **kwargs)):
            with patch.object(SanitizationMiddleware, '__call__',
                             side_effect=lambda *args, **kwargs: execution_order.append('Sanitization') or
                             SanitizationMiddleware.__call__(*args, **kwargs)):
                with patch.object(TimeoutMiddleware, '__call__',
                                 side_effect=lambda *args, **kwargs: execution_order.append('Timeout') or
                                 TimeoutMiddleware.__call__(*args, **kwargs)):
                    
                    client = TestClient(app)
                    response = client.get("/api/health")
        
        # Middleware should execute in this order
        expected_execution = ['RequestID', 'Sanitization', 'Timeout']
        assert execution_order[:3] == expected_execution, (
            f"Middleware executed in wrong order. "
            f"Expected: {expected_execution}, Got: {execution_order[:3]}"
        )
    
    def test_all_middleware_present(self):
        """Ensure all required middleware is present"""
        middleware_classes = [m.cls for m in app.user_middleware]
        
        required_middleware = [
            TimeoutMiddleware,
            SanitizationMiddleware,
            RequestIDMiddleware
        ]
        
        for required in required_middleware:
            assert required in middleware_classes, f"{required.__name__} not found in middleware stack"
    
    def test_no_duplicate_middleware(self):
        """Ensure no middleware is added twice"""
        middleware_classes = [m.cls for m in app.user_middleware]
        
        # Check for duplicates
        seen = set()
        for middleware in middleware_classes:
            assert middleware not in seen, f"{middleware.__name__} added multiple times"
            seen.add(middleware)


class TestMiddlewareIntegration:
    """Test middleware works correctly together"""
    
    def test_request_id_preserved_through_stack(self):
        """Request ID should be preserved through entire middleware stack"""
        client = TestClient(app)
        
        # Make multiple requests
        request_ids = set()
        for _ in range(5):
            response = client.get("/api/health")
            request_id = response.headers.get("X-Request-ID")
            assert request_id is not None
            assert request_id not in request_ids, "Request IDs should be unique"
            request_ids.add(request_id)
    
    def test_sanitization_with_timeout(self):
        """Sanitization should not interfere with timeout"""
        client = TestClient(app)
        
        # Large input that needs sanitization
        large_input = "<script>" * 1000 + "test" + "</script>" * 1000
        
        response = client.get("/api/customers", params={
            "search": large_input,
            "limit": "5"
        })
        
        # Should complete without timeout
        assert response.status_code in [200, 422]
    
    def test_error_handling_through_middleware(self):
        """Errors should propagate correctly through middleware"""
        client = TestClient(app)
        
        # Request non-existent endpoint
        response = client.get("/api/does-not-exist")
        
        # Should get 404, not middleware error
        assert response.status_code == 404
        # Should still have request ID
        assert "X-Request-ID" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])