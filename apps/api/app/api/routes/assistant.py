"""Routes assistant de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.assistant_service import (
    AssistantActionConfirmRequest,
    AssistantActionConfirmResponse,
    AssistantActionPreviewRequest,
    AssistantActionPreviewResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantService,
    get_assistant_service,
)
from app.services.auth_service import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
async def query_assistant(
    payload: AssistantQueryRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantQueryResponse:
    """Interroge l'assistant sur les domaines de données Life Pilot."""

    return await assistant_service.query(current_user.id, payload)


@router.post("/action-preview", response_model=AssistantActionPreviewResponse)
async def preview_assistant_action(
    payload: AssistantActionPreviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantActionPreviewResponse:
    """Prévisualise une action sensible sans l'exécuter."""

    return await assistant_service.preview_action(current_user.id, payload)


@router.post("/action-confirm", response_model=AssistantActionConfirmResponse)
async def confirm_assistant_action(
    payload: AssistantActionConfirmRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantActionConfirmResponse:
    """Exécute une action sensible uniquement après confirmation du preview."""

    return await assistant_service.confirm_action(current_user.id, payload)
