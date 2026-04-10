"""FastAPI application for FW viewer."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routes import router
from .config import CONFIG


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="FW Workflow Viewer",
        description="Visual interface for FW workflow projects",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router)
    
    return app


app = create_app()
