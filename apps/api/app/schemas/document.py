"""Schémas Pydantic pour les documents administratifs."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentResponse(BaseModel):
    """Représentation publique d'un document utilisateur."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str | None
    document_type: str
    title: str
    issuer: str | None
    issue_date: date | None
    due_date: date | None
    amount: Decimal | None
    currency: str
    file_path: str
    file_hash: str
    mime_type: str | None
    extracted_text: str | None
    extraction_status: str | None
    confidence_score: Decimal | None
    linked_transaction_id: UUID | None
    source_email_id: UUID | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Résultat d'un téléversement avec indicateur de doublon."""

    document: DocumentResponse
    duplicate: bool = False


class DocumentExtractRequest(BaseModel):
    """Données d'extraction optionnelles fournies par un worker OCR futur."""

    extracted_text: str | None = None
    extraction_status: str = Field(default="pending", max_length=80)
    issuer: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    due_date: date | None = None
    amount: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    confidence_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=5,
        decimal_places=4,
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Normalise le code devise ISO 4217 en majuscules."""

        return value.upper() if value is not None else None


class DocumentTransactionLink(BaseModel):
    """Demande de rattachement d'un document à une transaction."""

    transaction_id: UUID


class DocumentUpdate(BaseModel):
    """Modification manuelle des métadonnées d'un document."""

    provider: str | None = Field(default=None, max_length=255)
    document_type: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    issuer: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    due_date: date | None = None
    amount: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    extraction_status: str | None = Field(default=None, max_length=80)
    confidence_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=5,
        decimal_places=4,
    )
    source_email_id: UUID | None = None
    tags: list[str] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Normalise le code devise ISO 4217 en majuscules."""

        return value.upper() if value is not None else None
