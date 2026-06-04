"""The single FastAPI application (SC5).

One app, one entrypoint. The OpenAPI document FastAPI generates from this app is
the contract of record and the input to SDK generation — it replaces the legacy
openapi/eventrelay.openapi.json once the spine takes over.
"""
from __future__ import annotations

from fastapi import FastAPI

from .api.v1.routes import router as v1_router
from .config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(v1_router)
    return app


app = create_app()
