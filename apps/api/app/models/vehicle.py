"""Modèles de persistance des véhicules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class VehicleEventType(StrEnum):
    """Types d'événements véhicule suivis par Life Pilot."""

    TECHNICAL_INSPECTION = "technical_inspection"
    MAINTENANCE = "maintenance"
    OIL_CHANGE = "oil_change"
    BRAKES = "brakes"
    TIRES = "tires"
    INSURANCE = "insurance"
    REPAIR = "repair"
    FUEL = "fuel"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Vehicle:
    """Véhicule appartenant à un utilisateur."""

    id: UUID
    user_id: UUID
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


@dataclass(frozen=True, slots=True)
class VehicleEvent:
    """Événement d'historique ou d'échéance d'un véhicule."""

    id: UUID
    vehicle_id: UUID
    event_type: str
    event_date: date
    mileage: int | None
    title: str
    description: str | None
    cost: Decimal | None
    document_id: UUID | None
    next_due_date: date | None
    next_due_mileage: int | None
    created_at: datetime
