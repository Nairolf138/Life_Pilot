"""Modèles de persistance des dossiers fiscaux annuels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TaxYearFileStatus(StrEnum):
    """Statuts possibles d'un dossier fiscal annuel."""

    DRAFT = "draft"
    INCOMPLETE = "incomplete"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"


@dataclass(frozen=True, slots=True)
class TaxYearFile:
    """Dossier fiscal annuel préparé pour un utilisateur."""

    id: UUID
    user_id: UUID
    tax_year: int
    income_year: int
    status: str
    summary_markdown: str | None
    checklist_json: list[dict] | dict | None
    known_amounts_json: dict
    manual_prefilled_data_json: dict
    created_at: datetime
    updated_at: datetime
