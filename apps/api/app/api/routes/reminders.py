"""Routes reminders de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.reminder import ReminderCreate, ReminderResponse, ReminderUpdate
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.reminder_service import ReminderService, get_reminder_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reminder_service: Annotated[ReminderService, Depends(get_reminder_service)],
) -> list[ReminderResponse]:
    """Liste les rappels de l'utilisateur authentifié."""

    return await reminder_service.list_reminders(current_user.id)


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reminder_service: Annotated[ReminderService, Depends(get_reminder_service)],
) -> ReminderResponse:
    """Crée un rappel avec échéance, source et canaux de notification."""

    return await reminder_service.create_reminder(current_user.id, payload)


@router.patch("/{id}", response_model=ReminderResponse)
async def update_reminder(
    id: UUID,
    payload: ReminderUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reminder_service: Annotated[ReminderService, Depends(get_reminder_service)],
) -> ReminderResponse:
    """Met à jour partiellement un rappel."""

    return await reminder_service.update_reminder(current_user.id, id, payload)


@router.post("/{id}/complete", response_model=ReminderResponse)
async def complete_reminder(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reminder_service: Annotated[ReminderService, Depends(get_reminder_service)],
) -> ReminderResponse:
    """Marque un rappel comme terminé."""

    return await reminder_service.complete_reminder(current_user.id, id)
