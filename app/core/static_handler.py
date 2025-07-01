"""
Robust static file handling for FastAPI
Ensures static files are always available regardless of how the app is started
"""
import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from typing import Optional

logger = logging.getLogger(__name__)


def setup_static_files(app: FastAPI) -> Optional[str]:
    """
    Setup static files with multiple fallback paths
    
    Returns:
        The path where static files were successfully mounted, or None
    """
    # Try multiple possible locations for static files
    possible_paths = [
        # Relative to current file
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static"),
        # Relative to app directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app", "static"),
        # Direct path
        "app/static",
        # Absolute path from project root
        os.path.join(os.getcwd(), "app", "static"),
        # Development path
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "static"),
    ]
    
    # Normalize all paths
    possible_paths = [os.path.normpath(os.path.abspath(p)) for p in possible_paths]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in possible_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    # Try each path
    for static_path in unique_paths:
        if os.path.exists(static_path) and os.path.isdir(static_path):
            try:
                # Check if it has the expected structure
                js_dir = os.path.join(static_path, "js")
                css_dir = os.path.join(static_path, "css")
                
                if os.path.exists(js_dir) or os.path.exists(css_dir):
                    app.mount("/static", StaticFiles(directory=static_path), name="static")
                    logger.info(f"✅ Successfully mounted static files from: {static_path}")
                    
                    # List contents for debugging
                    contents = os.listdir(static_path)
                    logger.info(f"📁 Static directory contents: {contents}")
                    
                    return static_path
            except Exception as e:
                logger.warning(f"⚠️ Failed to mount static files from {static_path}: {e}")
                continue
    
    # If we get here, no valid static directory was found
    logger.error("❌ Could not find valid static directory in any of the expected locations")
    logger.error(f"❌ Searched paths: {unique_paths}")
    
    # Create a minimal static directory as fallback
    fallback_path = os.path.join(os.getcwd(), "app", "static")
    try:
        os.makedirs(fallback_path, exist_ok=True)
        os.makedirs(os.path.join(fallback_path, "js"), exist_ok=True)
        os.makedirs(os.path.join(fallback_path, "css"), exist_ok=True)
        
        # Create empty error-handler.js to prevent 404s
        error_handler_path = os.path.join(fallback_path, "js", "error-handler.js")
        if not os.path.exists(error_handler_path):
            with open(error_handler_path, "w") as f:
                f.write("// Placeholder error handler\nconsole.log('Error handler loaded');")
        
        app.mount("/static", StaticFiles(directory=fallback_path), name="static")
        logger.warning(f"⚠️ Created fallback static directory at: {fallback_path}")
        return fallback_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create fallback static directory: {e}")
        
        # Last resort - mount an in-memory static handler
        try:
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="tradeup_static_")
            os.makedirs(os.path.join(temp_dir, "js"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "css"), exist_ok=True)
            
            app.mount("/static", StaticFiles(directory=temp_dir), name="static")
            logger.warning(f"⚠️ Using temporary static directory at: {temp_dir}")
            return temp_dir
        except Exception as e2:
            logger.error(f"❌ Complete failure to setup static files: {e2}")
            return None


def verify_static_route(app: FastAPI) -> bool:
    """Verify that the static route is properly configured"""
    try:
        # Check if static route exists
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/static":
                logger.info("✅ Static route is registered")
                return True
        
        logger.error("❌ Static route not found in app routes")
        return False
    except Exception as e:
        logger.error(f"❌ Error verifying static route: {e}")
        return False