"""Routes accounts de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.account import AccountResponse, AccountUpdate, ManualAccountCreate
from app.services.account_service import AccountService, get_account_service
from app.services.auth_service import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> list[AccountResponse]:
    """Liste les comptes actifs de l'utilisateur authentifié."""

    return await account_service.list_active_accounts(current_user.id)


@router.get("/{id}", response_model=AccountResponse)
async def get_account(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Retourne le détail d'un compte de l'utilisateur authentifié."""

    return await account_service.get_account(current_user.id, id)


@router.post(
    "/manual",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_account(
    payload: ManualAccountCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Crée un compte manuel pour l'utilisateur authentifié."""

    return await account_service.create_manual_account(current_user.id, payload)


@router.patch("/{id}", response_model=AccountResponse)
async def update_account(
    id: UUID,
    payload: AccountUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Met à jour un compte de l'utilisateur authentifié."""

    return await account_service.update_account(current_user.id, id, payload)
