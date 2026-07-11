"""Schémas Pydantic pour les contrats et abonnements."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.contract import (
    ContractPaymentFrequency,
    ContractStatus,
    ContractType,
)


class ContractBase(BaseModel):
    """Champs communs de création et de modification d'un contrat."""

    provider: str = Field(min_length=1, max_length=255)
    contract_type: ContractType
    name: str = Field(min_length=1, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    notice_period_days: int | None = Field(default=None, ge=0)
    monthly_cost: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    yearly_cost: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    payment_frequency: ContractPaymentFrequency | None = None
    status: ContractStatus = ContractStatus.ACTIVE
    document_id: UUID | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> ContractBase:
        """Vérifie la cohérence des dates si elles sont fournies."""

        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date doit être postérieure ou égale à start_date.")
        return self


class ContractCreate(ContractBase):
    """Données nécessaires à la création d'un contrat."""


class ContractUpdate(BaseModel):
    """Modification partielle d'un contrat."""

    provider: str | None = Field(default=None, min_length=1, max_length=255)
    contract_type: ContractType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    notice_period_days: int | None = Field(default=None, ge=0)
    monthly_cost: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    yearly_cost: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    payment_frequency: ContractPaymentFrequency | None = None
    status: ContractStatus | None = None
    document_id: UUID | None = None
    notes: str | None = None


class ContractResponse(BaseModel):
    """Représentation publique d'un contrat ou abonnement."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    contract_type: ContractType
    name: str
    reference: str | None
    start_date: date | None
    end_date: date | None
    renewal_date: date | None
    notice_period_days: int | None
    monthly_cost: Decimal | None
    yearly_cost: Decimal | None
    payment_frequency: ContractPaymentFrequency | None
    status: ContractStatus
    document_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
