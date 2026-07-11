"""Routes contracts de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.contract import ContractCreate, ContractResponse, ContractUpdate
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.contract_service import ContractService, get_contract_service

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractResponse])
async def list_contracts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    contract_service: Annotated[ContractService, Depends(get_contract_service)],
) -> list[ContractResponse]:
    """Liste les contrats et abonnements de l'utilisateur authentifié."""

    return await contract_service.list_contracts(current_user.id)


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    contract_service: Annotated[ContractService, Depends(get_contract_service)],
) -> ContractResponse:
    """Crée un contrat ou abonnement pour l'utilisateur authentifié."""

    return await contract_service.create_contract(current_user.id, payload)


@router.get("/{id}", response_model=ContractResponse)
async def get_contract(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    contract_service: Annotated[ContractService, Depends(get_contract_service)],
) -> ContractResponse:
    """Retourne le détail d'un contrat de l'utilisateur authentifié."""

    return await contract_service.get_contract(current_user.id, id)


@router.patch("/{id}", response_model=ContractResponse)
async def update_contract(
    id: UUID,
    payload: ContractUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    contract_service: Annotated[ContractService, Depends(get_contract_service)],
) -> ContractResponse:
    """Met à jour partiellement un contrat de l'utilisateur authentifié."""

    return await contract_service.update_contract(current_user.id, id, payload)
