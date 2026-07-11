"""Modèle de persistance des contrats et abonnements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ContractType(StrEnum):
    """Types de contrats suivis par Life Pilot."""

    CAR_INSURANCE = "car_insurance"
    HOME_INSURANCE = "home_insurance"
    PHONE = "phone"
    INTERNET = "internet"
    ELECTRICITY = "electricity"
    STREAMING = "streaming"
    SOFTWARE = "software"
    TELEPEAGE = "telepeage"
    BANK_SERVICE = "bank_service"
    OTHER = "other"


class ContractPaymentFrequency(StrEnum):
    """Fréquences de paiement possibles pour un contrat."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ONE_TIME = "one_time"
    OTHER = "other"


class ContractStatus(StrEnum):
    """Statuts métier d'un contrat."""

    ACTIVE = "active"
    TERMINATED = "terminated"
    TO_REVIEW = "to_review"


@dataclass(frozen=True, slots=True)
class Contract:
    """Contrat ou abonnement appartenant à un utilisateur."""

    id: UUID
    user_id: UUID
    provider: str
    contract_type: str
    name: str
    reference: str | None
    start_date: date | None
    end_date: date | None
    renewal_date: date | None
    notice_period_days: int | None
    monthly_cost: Decimal | None
    yearly_cost: Decimal | None
    payment_frequency: str | None
    status: str
    document_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
