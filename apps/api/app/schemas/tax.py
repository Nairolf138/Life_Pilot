"""Schémas Pydantic pour l'assistant fiscal."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tax_year_file import TaxYearFileStatus


class TaxYearFileBase(BaseModel):
    """Champs communs d'un dossier fiscal annuel."""

    tax_year: int = Field(ge=1900)
    income_year: int = Field(ge=1900)
    status: TaxYearFileStatus = TaxYearFileStatus.DRAFT
    summary_markdown: str | None = None
    checklist_json: list[dict[str, Any]] = Field(default_factory=list)
    known_amounts_json: dict[str, Any] = Field(default_factory=dict)
    manual_prefilled_data_json: dict[str, Any] = Field(default_factory=dict)


class TaxYearFileCreate(TaxYearFileBase):
    """Données nécessaires à la création d'un dossier fiscal."""


class TaxYearFileUpdate(BaseModel):
    """Modification partielle d'un dossier fiscal."""

    tax_year: int | None = Field(default=None, ge=1900)
    income_year: int | None = Field(default=None, ge=1900)
    status: TaxYearFileStatus | None = None
    summary_markdown: str | None = None
    checklist_json: list[dict[str, Any]] | None = None
    known_amounts_json: dict[str, Any] | None = None
    manual_prefilled_data_json: dict[str, Any] | None = None

    @model_validator(mode="after")
    def ensure_at_least_one_field(self) -> TaxYearFileUpdate:
        """Refuse les mises à jour sans champ explicite."""

        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être renseigné.")
        return self


class TaxYearFileResponse(BaseModel):
    """Représentation publique d'un dossier fiscal annuel."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tax_year: int
    income_year: int
    status: TaxYearFileStatus
    summary_markdown: str | None
    checklist_json: list[dict[str, Any]] | dict[str, Any] | None
    known_amounts_json: dict[str, Any]
    manual_prefilled_data_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
