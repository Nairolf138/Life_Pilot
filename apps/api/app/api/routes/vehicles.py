"""Routes vehicles de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.vehicle import (
    VehicleCreate,
    VehicleEventCreate,
    VehicleEventResponse,
    VehicleResponse,
    VehicleUpdate,
)
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.vehicle_service import VehicleService, get_vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> list[VehicleResponse]:
    """Liste les véhicules de l'utilisateur authentifié."""

    return await vehicle_service.list_vehicles(current_user.id)


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleResponse:
    """Crée un véhicule pour l'utilisateur authentifié."""

    return await vehicle_service.create_vehicle(current_user.id, payload)


@router.get("/{id}", response_model=VehicleResponse)
async def get_vehicle(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleResponse:
    """Retourne le détail d'un véhicule de l'utilisateur authentifié."""

    return await vehicle_service.get_vehicle(current_user.id, id)


@router.patch("/{id}", response_model=VehicleResponse)
async def update_vehicle(
    id: UUID,
    payload: VehicleUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleResponse:
    """Met à jour partiellement un véhicule de l'utilisateur authentifié."""

    return await vehicle_service.update_vehicle(current_user.id, id, payload)


@router.post(
    "/{id}/events",
    response_model=VehicleEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vehicle_event(
    id: UUID,
    payload: VehicleEventCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    vehicle_service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleEventResponse:
    """Ajoute un événement à un véhicule de l'utilisateur authentifié."""

    return await vehicle_service.create_vehicle_event(current_user.id, id, payload)
