"""Routes dashboard de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.schemas.monthly_summary import MonthlySummaryResponse
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.monthly_summary_service import (
    MonthlySummaryService,
    get_monthly_summary_service,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
async def get_monthly_summary(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    monthly_summary_service: Annotated[
        MonthlySummaryService,
        Depends(get_monthly_summary_service),
    ],
    month: Annotated[
        str,
        Query(pattern=r"^\d{4}-\d{2}$", description="Mois au format YYYY-MM."),
    ],
) -> MonthlySummaryResponse:
    """Retourne la synthèse financière du mois demandé."""

    return await monthly_summary_service.get_monthly_summary(current_user.id, month)
