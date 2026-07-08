"""Schémas Pydantic pour les transactions financières."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransactionResponse(BaseModel):
    """Représentation publique d'une transaction bancaire."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    external_id_hash: str | None
    booking_date: date
    value_date: date | None
    label_raw: str
    label_clean: str | None
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_type: str | None
    category_id: UUID | None
    subcategory_id: UUID | None
    confidence_score: Decimal | None
    is_recurring: bool
    is_internal_transfer: bool
    linked_document_id: UUID | None
    notes: str | None
    raw_data_json: dict
    created_at: datetime
    updated_at: datetime


class TransactionImportItem(BaseModel):
    """Transaction reçue depuis un import bancaire ou manuel."""

    account_id: UUID
    external_id: str | None = Field(default=None, min_length=1, max_length=500)
    external_id_hash: str | None = Field(default=None, min_length=1, max_length=128)
    booking_date: date
    value_date: date | None = None
    label_raw: str = Field(min_length=1, max_length=500)
    label_clean: str | None = Field(default=None, max_length=500)
    merchant_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    transaction_type: str | None = Field(default=None, max_length=80)
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    confidence_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=5,
        decimal_places=4,
    )
    is_recurring: bool = False
    is_internal_transfer: bool = False
    notes: str | None = None
    raw_data_json: dict = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalise le code devise ISO 4217 en majuscules."""

        return value.upper()

    @model_validator(mode="after")
    def require_external_identifier(self) -> TransactionImportItem:
        """Impose un identifiant externe clair pour une déduplication stable."""

        if self.external_id is None and self.external_id_hash is None:
            raise ValueError("external_id ou external_id_hash est requis.")
        return self


class TransactionImportRequest(BaseModel):
    """Lot de transactions à importer."""

    transactions: list[TransactionImportItem] = Field(min_length=1, max_length=1000)


class TransactionImportResponse(BaseModel):
    """Résultat d'un import avec déduplication."""

    imported: int
    duplicates: int
    transactions: list[TransactionResponse]


class TransactionCategoryPatch(BaseModel):
    """Modification manuelle de la catégorie d'une transaction."""

    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)
    confidence_score: Decimal | None = Field(
        default=Decimal("1"),
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=5,
        decimal_places=4,
    )
    learning_scope: Literal[
        "transaction_only",
        "future_similar",
        "past_and_future_similar",
    ] = "transaction_only"


class TransactionDocumentLink(BaseModel):
    """Demande de rattachement d'un justificatif à une transaction."""

    document_id: UUID
