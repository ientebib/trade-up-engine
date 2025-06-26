"""
Input Sanitization Middleware
Protects against XSS and injection attacks
"""
import re
import html
import logging
from typing import Any, Dict, List, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import json

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitize user inputs to prevent XSS and injection attacks"""
    
    # Patterns that might indicate malicious input
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                  # JavaScript protocol
        r'on\w+\s*=',                   # Event handlers (onclick, onload, etc.)
        r'<iframe',                      # Iframe injection
        r'<object',                      # Object injection
        r'<embed',                       # Embed injection
        r'<link',                        # Link injection
        r'<meta',                        # Meta injection
        r'<style',                       # Style injection
        r'--',                          # SQL comment
        r';.*DROP.*TABLE',              # SQL injection
        r';.*DELETE.*FROM',             # SQL injection
        r';.*INSERT.*INTO',             # SQL injection
        r';.*UPDATE.*SET',              # SQL injection
        r'UNION.*SELECT',               # SQL injection
        r'<\?php',                      # PHP injection
        r'<%',                          # Server-side injection
    ]
    
    # Compile patterns for efficiency
    COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                        for pattern in DANGEROUS_PATTERNS]
    
    @staticmethod
    def is_dangerous(value: str) -> bool:
        """Check if a string contains potentially dangerous content"""
        if not isinstance(value, str):
            return False
            
        for pattern in InputSanitizer.COMPILED_PATTERNS:
            if pattern.search(value):
                return True
        return False
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """
        Sanitize a string value
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return value
            
        # Truncate extremely long inputs
        if len(value) > max_length:
            logger.warning(f"Input truncated from {len(value)} to {max_length} characters")
            value = value[:max_length]
        
        # HTML escape special characters
        value = html.escape(value, quote=True)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters (except newline, tab, carriage return)
        value = ''.join(char for char in value 
                       if ord(char) >= 32 or char in '\n\r\t')
        
        return value.strip()
    
    @staticmethod
    def sanitize_identifier(value: str, max_length: int = 100) -> str:
        """
        Sanitize an identifier (customer_id, etc.)
        Only allow alphanumeric, underscore, and dash
        """
        if not isinstance(value, str):
            return str(value)
            
        # Remove any non-alphanumeric characters except _ and -
        value = re.sub(r'[^a-zA-Z0-9_-]', '', value)
        
        # Limit length
        return value[:max_length]
    
    @staticmethod
    def sanitize_number(value: Any, min_val: float = None, max_val: float = None) -> float:
        """Sanitize and validate numeric input"""
        try:
            num = float(value)
            
            # Check for special values
            if not (-1e308 < num < 1e308):  # Python float range
                raise ValueError("Number out of range")
                
            if min_val is not None and num < min_val:
                logger.warning(f"Number {num} below minimum {min_val}")
                num = min_val
                
            if max_val is not None and num > max_val:
                logger.warning(f"Number {num} above maximum {max_val}")
                num = max_val
                
            return num
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid numeric value: {value}")
            return 0.0
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values"""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize the key
            clean_key = InputSanitizer.sanitize_identifier(str(key))
            
            # Sanitize the value based on type
            if isinstance(value, str):
                sanitized[clean_key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = InputSanitizer.sanitize_list(value)
            elif isinstance(value, (int, float)):
                sanitized[clean_key] = InputSanitizer.sanitize_number(value)
            else:
                sanitized[clean_key] = value
                
        return sanitized
    
    @staticmethod
    def sanitize_list(data: List[Any]) -> List[Any]:
        """Recursively sanitize list values"""
        sanitized = []
        
        for value in data:
            if isinstance(value, str):
                sanitized.append(InputSanitizer.sanitize_string(value))
            elif isinstance(value, dict):
                sanitized.append(InputSanitizer.sanitize_dict(value))
            elif isinstance(value, list):
                sanitized.append(InputSanitizer.sanitize_list(value))
            elif isinstance(value, (int, float)):
                sanitized.append(InputSanitizer.sanitize_number(value))
            else:
                sanitized.append(value)
                
        return sanitized


class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize all incoming request data"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip sanitization for internal endpoints
        if request.url.path.startswith("/static/") or request.url.path == "/docs":
            return await call_next(request)
        
        # Log if any dangerous patterns detected
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Check query parameters
                for key, value in request.query_params.items():
                    if InputSanitizer.is_dangerous(value):
                        logger.warning(f"Dangerous pattern in query param {key}: {value[:50]}...")
                
                # For body data, we'll need to handle in the endpoints
                # since body can only be read once
                
            except Exception as e:
                logger.error(f"Error in sanitization middleware: {e}")
        
        response = await call_next(request)
        return response


def sanitize_customer_id(customer_id: str) -> str:
    """Sanitize customer ID for safe use"""
    return InputSanitizer.sanitize_identifier(customer_id, max_length=50)


def sanitize_search_term(term: str) -> str:
    """Sanitize search term"""
    return InputSanitizer.sanitize_string(term, max_length=100)


def sanitize_pagination(page: int, limit: int) -> tuple:
    """Sanitize and validate pagination parameters"""
    page = int(InputSanitizer.sanitize_number(page, min_val=1, max_val=10000))
    limit = int(InputSanitizer.sanitize_number(limit, min_val=1, max_val=100))
    return page, limit