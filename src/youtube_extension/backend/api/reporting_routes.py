import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.integration.looker_embedded import LookerEmbeddedService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reporting", tags=["Reporting & Dashboards"])

class DashboardEmbedRequest(BaseModel):
    dashboard_id: str
    tenant_id: str
    user_id: str
    user_email: str

class DashboardEmbedResponse(BaseModel):
    embed_url: str

def get_looker_service() -> LookerEmbeddedService:
    return LookerEmbeddedService()

@router.post("/embed/dashboard", response_model=DashboardEmbedResponse)
async def generate_dashboard_url(
    request: DashboardEmbedRequest,
    looker_service: LookerEmbeddedService = Depends(get_looker_service)
):
    """
    Generate a secure, signed SSO embed URL for Looker (Google equivalent to QuickSight).
    Enforces Multi-Tenant Row-Level Security (RLS) by passing the tenant_id.
    """
    try:
        url = looker_service.get_tenant_dashboard_url(
            dashboard_id=request.dashboard_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            user_email=request.user_email
        )
        return DashboardEmbedResponse(embed_url=url)
    except Exception as e:
        logger.error(f"Failed to generate dashboard embed URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dashboards")
async def list_available_dashboards(tenant_id: str = Query(...)):
    """
    Mock endpoint: List dashboards a specific tenant has access to.
    In a real implementation, this would query the Looker API or a local database mapping.
    """
    return {
        "tenant_id": tenant_id,
        "dashboards": [
            {"id": "events_overview", "name": "Event Processing Overview"},
            {"id": "video_analytics", "name": "Video Analysis Metrics"},
            {"id": "cost_usage", "name": "API Cost & Usage"}
        ]
    }
