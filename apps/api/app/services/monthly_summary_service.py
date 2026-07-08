"""Service de synthèse mensuelle du dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.transaction_service import UNCERTAIN_CATEGORY_THRESHOLD


@dataclass(frozen=True, slots=True)
class MonthlyCategorySummary:
    """Agrégat de dépenses pour une catégorie."""

    category_id: UUID | None
    category_name: str
    amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class MonthlyTransactionAttention:
    """Transaction à afficher comme point d'attention."""

    id: UUID
    booking_date: date
    label: str
    amount: Decimal
    category_name: str | None
    confidence_score: Decimal | None
    linked_document_id: UUID | None


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    """Synthèse financière calculée pour un mois civil."""

    month: str
    period_start: date
    period_end: date
    income: Decimal
    expenses: Decimal
    estimated_savings: Decimal
    estimated_remaining: Decimal
    expenses_by_category: list[MonthlyCategorySummary]
    top_categories: list[MonthlyCategorySummary]
    uncategorized_transactions: list[MonthlyTransactionAttention]
    low_confidence_transactions: list[MonthlyTransactionAttention]
    transactions_without_document: list[MonthlyTransactionAttention]


class MonthlySummaryService:
    """Calcule les indicateurs mensuels du dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_monthly_summary(self, user_id: UUID, month: str) -> MonthlySummary:
        """Retourne la synthèse d'un mois au format YYYY-MM."""

        period_start, period_end = month_bounds(month)
        common_params = {
            "user_id": user_id,
            "period_start": period_start,
            "period_end": period_end,
            "category_threshold": UNCERTAIN_CATEGORY_THRESHOLD,
        }

        totals = await self._fetch_totals(common_params)
        expenses_by_category = await self._fetch_expenses_by_category(common_params)
        return MonthlySummary(
            month=month,
            period_start=period_start,
            period_end=period_end,
            income=totals["income"],
            expenses=totals["expenses"],
            estimated_savings=totals["estimated_savings"],
            estimated_remaining=totals["estimated_remaining"],
            expenses_by_category=expenses_by_category,
            top_categories=expenses_by_category[:5],
            uncategorized_transactions=await self._fetch_attention_transactions(
                common_params,
                "t.category_id IS NULL",
            ),
            low_confidence_transactions=await self._fetch_attention_transactions(
                common_params,
                "(t.confidence_score IS NULL "
                "OR t.confidence_score < :category_threshold)",
            ),
            transactions_without_document=await self._fetch_attention_transactions(
                common_params,
                "t.linked_document_id IS NULL",
            ),
        )

    async def _fetch_totals(self, params: dict[str, object]) -> dict[str, Decimal]:
        result = await self._session.execute(
            text(
                """
                SELECT
                    coalesce(
                        sum(CASE WHEN amount > 0 THEN amount ELSE 0 END),
                        0
                    ) AS income,
                    coalesce(
                        sum(CASE WHEN amount < 0 THEN abs(amount) ELSE 0 END),
                        0
                    ) AS expenses
                FROM transactions
                WHERE user_id = :user_id
                  AND booking_date >= :period_start
                  AND booking_date <= :period_end
                  AND is_internal_transfer = false
                """
            ),
            params,
        )
        row = result.mappings().one()
        income = Decimal(row.income)
        expenses = Decimal(row.expenses)
        estimated_savings = income - expenses
        return {
            "income": income,
            "expenses": expenses,
            "estimated_savings": estimated_savings,
            "estimated_remaining": estimated_savings,
        }

    async def _fetch_expenses_by_category(
        self,
        params: dict[str, object],
    ) -> list[MonthlyCategorySummary]:
        result = await self._session.execute(
            text(
                """
                SELECT
                    t.category_id,
                    coalesce(c.name, 'Non catégorisé') AS category_name,
                    coalesce(sum(abs(t.amount)), 0) AS amount,
                    count(*) AS transaction_count
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = :user_id
                  AND t.booking_date >= :period_start
                  AND t.booking_date <= :period_end
                  AND t.is_internal_transfer = false
                  AND t.amount < 0
                GROUP BY t.category_id, c.name
                ORDER BY amount DESC, category_name ASC
                """
            ),
            params,
        )
        return [
            MonthlyCategorySummary(
                category_id=row.category_id,
                category_name=row.category_name,
                amount=Decimal(row.amount),
                transaction_count=int(row.transaction_count),
            )
            for row in result.mappings().all()
        ]

    async def _fetch_attention_transactions(
        self,
        params: dict[str, object],
        extra_condition: str,
    ) -> list[MonthlyTransactionAttention]:
        result = await self._session.execute(
            text(
                f"""
                SELECT
                    t.id,
                    t.booking_date,
                    coalesce(t.label_clean, t.label_raw) AS label,
                    t.amount,
                    c.name AS category_name,
                    t.confidence_score,
                    t.linked_document_id
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = :user_id
                  AND t.booking_date >= :period_start
                  AND t.booking_date <= :period_end
                  AND t.is_internal_transfer = false
                  AND {extra_condition}
                ORDER BY t.booking_date DESC, abs(t.amount) DESC
                LIMIT 20
                """
            ),
            params,
        )
        return [
            MonthlyTransactionAttention(
                id=row.id,
                booking_date=row.booking_date,
                label=row.label,
                amount=Decimal(row.amount),
                category_name=row.category_name,
                confidence_score=row.confidence_score,
                linked_document_id=row.linked_document_id,
            )
            for row in result.mappings().all()
        ]


def month_bounds(month: str) -> tuple[date, date]:
    """Convertit YYYY-MM en bornes inclusives de mois civil."""

    try:
        year_text, month_text = month.split("-", maxsplit=1)
        year = int(year_text)
        month_number = int(month_text)
        period_start = date(year, month_number, 1)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le paramètre month doit respecter le format YYYY-MM.",
        ) from exc

    if month_number == 12:
        period_end = date(year, 12, 31)
    else:
        period_end = date.fromordinal(date(year, month_number + 1, 1).toordinal() - 1)
    return period_start, period_end


async def get_monthly_summary_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MonthlySummaryService:
    """Construit le service de synthèse mensuelle pour FastAPI."""

    return MonthlySummaryService(session)
