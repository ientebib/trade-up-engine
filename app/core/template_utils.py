"""
Template utilities and context processors
"""
from fastapi import Request
from typing import Dict, Any


def static_url(filename: str) -> str:
    """
    Generate static file URL without dependency on url_for
    
    Args:
        filename: Path to file within static directory (e.g., 'js/main.js')
        
    Returns:
        Full URL path to static file
    """
    # Ensure filename doesn't start with /
    if filename.startswith('/'):
        filename = filename[1:]
    
    return f"/static/{filename}"


def get_template_context(request: Request) -> Dict[str, Any]:
    """
    Get base context for all templates
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Dictionary with template context variables
    """
    return {
        "request": request,
        "static_url": static_url,
        # Add other global template variables here
    }


class TemplateContextMiddleware:
    """
    Middleware to inject template utilities into all template responses
    """
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add static_url to scope for templates
            scope["static_url"] = static_url
        
        await self.app(scope, receive, send)