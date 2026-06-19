"""The single FastAPI application (SC5).

One app, one entrypoint. The OpenAPI document FastAPI generates from this app is
the contract of record and the input to SDK generation — it replaces the legacy
openapi/eventrelay.openapi.json once the spine takes over.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.routes import router as v1_router
from .config import get_settings


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application for the service.
    
    Configures application metadata from settings, applies CORS middleware permitting frontend cross-origin requests, and registers the v1 API router.
    
    Returns:
        A configured FastAPI application instance with title/version from settings, CORS middleware, and the v1 router included.
    """
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    
    # SC7: Configure CORS to allow the frontend to make cross-origin requests.
    # The frontend (apps/web) is served from a different origin than the backend.
    # In development, both are on localhost but with different ports.
    # In production, the frontend and backend have distinct domains.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins; the API contract is public.
        allow_credentials=False,
        allow_methods=["GET", "POST"],  # Only the methods used by the SC7 contract.
        allow_headers=["Content-Type"],
    )
    
    app.include_router(v1_router)
    return app


app = create_app()
