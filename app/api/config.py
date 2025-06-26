"""
Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict
import logging
from app.utils.error_handling import handle_api_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
@handle_api_errors("get configuration")
async def get_config():
    """Get current engine configuration"""
    from app.services.config_service import config_service
    
    # All configuration logic delegated to service layer
    return config_service.get_current_config()


@router.post("/save-config")
@handle_api_errors("save configuration")
async def save_config(config: Dict = Body(...)):
    """Save engine configuration overrides"""
    from app.services.config_service import config_service
    
    # All file I/O logic delegated to service layer
    config_service.save_config(config)
    
    return JSONResponse({
        "status": "success",
        "message": "Configuration saved successfully"
    })