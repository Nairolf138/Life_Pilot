"""Routes de supervision de l'API."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Indique que le processus API répond."""

    return HealthResponse(status="ok", service="api")
