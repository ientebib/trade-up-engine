from __future__ import annotations

from typing import Literal, Callable, Optional
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.logging_config import setup_logging

setup_logging(logging.INFO)

def create_app(
    mode: Literal["prod", "dev"] = "prod",
    *,
    lifespan: Optional[Callable] = None,
    static_dir: str = "app/static",
    templates_dir: str = "app/templates",
) -> FastAPI:
    """Application factory returning a configured :class:`FastAPI` instance."""

    if mode == "dev":
        title = "Trade-Up Engine - Development"
        description = "Development version optimized for virtual agents"
        version = "1.0.0-dev"
        from core.data_loader_dev import dev_data_loader as loader
    else:
        title = "Kavak Trade-Up Engine"
        description = "API and Web Dashboard for generating vehicle upgrade offers."
        version = "1.0.0"
        from core.data_loader import data_loader as loader

    app = FastAPI(title=title, description=description, version=version, lifespan=lifespan)

    # Static files and templates used by both modes
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    templates = Jinja2Templates(directory=templates_dir)
    app.state.templates = templates

    # Store the selected data loader for use elsewhere
    app.state.data_loader = loader

    if mode == "dev":
        # Development API routes
        from app.api.routes import router as api_router
        app.include_router(api_router, prefix="/api")

    return app
