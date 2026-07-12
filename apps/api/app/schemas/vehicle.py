"""Schémas Pydantic pour les véhicules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.vehicle import VehicleEventType


class VehicleBase(BaseModel):
    """Champs communs de création et de modification d'un véhicule."""

    brand: str = Field(min_length=1, max_length=255)
    model: str = Field(min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=255)
    registration_masked: str | None = Field(default=None, max_length=255)
    vin_hash: str | None = Field(default=None, max_length=255)
    first_registration_date: date | None = None
    mileage_current: int | None = Field(default=None, ge=0)
    mileage_updated_at: datetime | None = None
    technical_inspection_due_date: date | None = None
    insurance_contract_id: UUID | None = None
    maintenance_notes: str | None = None


class VehicleCreate(VehicleBase):
    """Données nécessaires à la création d'un véhicule."""


class VehicleUpdate(BaseModel):
    """Modification partielle d'un véhicule."""

    brand: str | None = Field(default=None, min_length=1, max_length=255)
    model: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=255)
    registration_masked: str | None = Field(default=None, max_length=255)
    vin_hash: str | None = Field(default=None, max_length=255)
    first_registration_date: date | None = None
    mileage_current: int | None = Field(default=None, ge=0)
    mileage_updated_at: datetime | None = None
    technical_inspection_due_date: date | None = None
    insurance_contract_id: UUID | None = None
    maintenance_notes: str | None = None


class VehicleEventCreate(BaseModel):
    """Données nécessaires à l'ajout d'un événement véhicule."""

    event_type: VehicleEventType
    event_date: date
    mileage: int | None = Field(default=None, ge=0)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    cost: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    document_id: UUID | None = None
    next_due_date: date | None = None
    next_due_mileage: int | None = Field(default=None, ge=0)


class VehicleEventResponse(BaseModel):
    """Représentation publique d'un événement véhicule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    event_type: VehicleEventType
    event_date: date
    mileage: int | None
    title: str
    description: str | None
    cost: Decimal | None
    document_id: UUID | None
    next_due_date: date | None
    next_due_mileage: int | None
    created_at: datetime


class VehicleResponse(BaseModel):
    """Représentation publique d'un véhicule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand: str
    model: str
    version: str | None
    registration_masked: str | None
    vin_hash: str | None
    first_registration_date: date | None
    mileage_current: int | None
    mileage_updated_at: datetime | None
    technical_inspection_due_date: date | None
    insurance_contract_id: UUID | None
    maintenance_notes: str | None
    created_at: datetime
    updated_at: datetime
