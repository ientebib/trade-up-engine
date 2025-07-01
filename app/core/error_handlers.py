"""
Global error handlers for the application
"""
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.middleware.request_id import get_request_id
from app.core.template_utils import static_url
import logging
import os

template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)
templates.env.globals["static_url"] = static_url
logger = logging.getLogger(__name__)


async def not_found_handler(request: Request, exc: HTTPException):
    request_id = get_request_id(request)
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "API endpoint not found",
                "request_id": request_id,
                "path": request.url.path
            },
            headers={"X-Request-ID": request_id}
        )
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "request_id": request_id
        },
        status_code=404
    )


async def internal_error_handler(request: Request, exc: Exception):
    request_id = get_request_id(request)
    error_type = type(exc).__name__
    
    # Log the full error with request ID
    logger.error(f"Internal error for request {request_id}: {error_type}: {exc}")
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
                "error_type": error_type,
                "message": "An unexpected error occurred. Please reference the request ID when reporting this issue."
            },
            headers={"X-Request-ID": request_id}
        )
    return templates.TemplateResponse(
        "500.html",
        {
            "request": request,
            "request_id": request_id,
            "error_type": error_type
        },
        status_code=500
    )