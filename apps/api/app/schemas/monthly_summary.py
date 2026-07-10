"""Schémas Pydantic pour la synthèse mensuelle du dashboard."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MonthlyCategorySummaryResponse(BaseModel):
    """Dépenses agrégées pour une catégorie."""

    model_config = ConfigDict(from_attributes=True)

    category_id: UUID | None
    category_name: str
    amount: Decimal
    transaction_count: int


class MonthlyTransactionAttentionResponse(BaseModel):
    """Transaction nécessitant une vérification."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_date: date
    label: str
    amount: Decimal
    category_name: str | None
    confidence_score: Decimal | None
    linked_document_id: UUID | None


class MonthlySummaryResponse(BaseModel):
    """Réponse publique de la synthèse mensuelle."""

    model_config = ConfigDict(from_attributes=True)

    month: str
    period_start: date
    period_end: date
    income: Decimal
    expenses: Decimal
    estimated_savings: Decimal
    estimated_remaining: Decimal
    expenses_by_category: list[MonthlyCategorySummaryResponse]
    top_categories: list[MonthlyCategorySummaryResponse]
    uncategorized_transactions: list[MonthlyTransactionAttentionResponse]
    low_confidence_transactions: list[MonthlyTransactionAttentionResponse]
    transactions_without_document: list[MonthlyTransactionAttentionResponse]
    financial_unmatched_documents_count: int
    transactions_without_document_count: int
    transactions_without_document_amount: Decimal
