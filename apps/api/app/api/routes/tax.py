"""Routes tax de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.tax import (
    TaxChecklistExport,
    TaxYearFileCreate,
    TaxYearFileResponse,
    TaxYearFileUpdate,
)
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.tax_assistant_service import (
    TaxAssistantService,
    get_tax_assistant_service,
)

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/year-files", response_model=list[TaxYearFileResponse])
async def list_tax_year_files(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> list[TaxYearFileResponse]:
    """Liste les dossiers fiscaux de l'utilisateur authentifié."""

    return await tax_service.list_tax_year_files(current_user.id)


@router.post(
    "/year-files",
    response_model=TaxYearFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tax_year_file(
    payload: TaxYearFileCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> TaxYearFileResponse:
    """Crée un dossier fiscal pour l'utilisateur authentifié."""

    return await tax_service.create_tax_year_file(current_user.id, payload)


@router.get("/year-files/{id}", response_model=TaxYearFileResponse)
async def get_tax_year_file(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> TaxYearFileResponse:
    """Retourne le détail d'un dossier fiscal de l'utilisateur authentifié."""

    return await tax_service.get_tax_year_file(current_user.id, id)


@router.patch("/year-files/{id}", response_model=TaxYearFileResponse)
async def update_tax_year_file(
    id: UUID,
    payload: TaxYearFileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> TaxYearFileResponse:
    """Met à jour partiellement un dossier fiscal de l'utilisateur authentifié."""

    return await tax_service.update_tax_year_file(current_user.id, id, payload)


@router.post("/year-files/{id}/checklist", response_model=TaxYearFileResponse)
async def refresh_tax_checklist(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> TaxYearFileResponse:
    """Régénère la checklist fiscale JSON et Markdown du dossier."""

    return await tax_service.refresh_checklist(current_user.id, id)


@router.get("/year-files/{id}/checklist/markdown", response_model=TaxChecklistExport)
async def export_tax_checklist_markdown(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    tax_service: Annotated[TaxAssistantService, Depends(get_tax_assistant_service)],
) -> TaxChecklistExport:
    """Exporte la checklist fiscale en Markdown, avec extension PDF prévue."""

    return await tax_service.export_checklist_markdown(current_user.id, id)
