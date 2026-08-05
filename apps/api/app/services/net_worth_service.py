"""Service de calcul du patrimoine net estimé."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session


@dataclass(frozen=True, slots=True)
class AssetClassAllocation:
    """Répartition d'une classe d'actifs dans le patrimoine estimé."""

    asset_class: str
    label: str
    value: Decimal
    percentage: Decimal


@dataclass(frozen=True, slots=True)
class NetWorthSummary:
    """Synthèse du patrimoine estimé d'un utilisateur."""

    currency: str
    bank_cash_total: Decimal
    crypto_total: Decimal
    stocks_total: Decimal
    other_assets_total: Decimal
    estimated_net_worth: Decimal
    allocation: list[AssetClassAllocation]
    last_sync_at: datetime | None


class NetWorthService:
    """Calcule les agrégats patrimoniaux à partir des comptes et actifs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_summary(self, user_id: UUID) -> NetWorthSummary:
        """Retourne le patrimoine estimé consolidé de l'utilisateur."""

        result = await self._session.execute(
            text(
                """
                WITH preferred_currency AS (
                    SELECT currency_default AS currency
                    FROM users
                    WHERE id = :user_id
                ), bank_cash AS (
                    SELECT
                        COALESCE(SUM(balance_current), 0) AS total,
                        MAX(last_sync_at) AS last_sync_at
                    FROM accounts
                    WHERE user_id = :user_id
                      AND is_active = true
                      AND currency = (SELECT currency FROM preferred_currency)
                ), asset_totals AS (
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN asset_type = 'crypto' THEN current_value
                            ELSE 0
                        END), 0) AS crypto_total,
                        COALESCE(SUM(CASE
                            WHEN asset_type = 'stock' THEN current_value
                            ELSE 0
                        END), 0) AS stocks_total,
                        COALESCE(SUM(CASE
                            WHEN asset_type NOT IN ('crypto', 'stock')
                                THEN current_value
                            ELSE 0
                        END), 0) AS other_assets_total,
                        MAX(last_price_sync_at) AS last_sync_at
                    FROM assets
                    WHERE user_id = :user_id
                      AND currency = (SELECT currency FROM preferred_currency)
                )
                SELECT
                    preferred_currency.currency,
                    bank_cash.total AS bank_cash_total,
                    asset_totals.crypto_total,
                    asset_totals.stocks_total,
                    asset_totals.other_assets_total,
                    (
                        bank_cash.total +
                        asset_totals.crypto_total +
                        asset_totals.stocks_total +
                        asset_totals.other_assets_total
                    ) AS estimated_net_worth,
                    CASE
                        WHEN bank_cash.last_sync_at IS NULL
                            THEN asset_totals.last_sync_at
                        WHEN asset_totals.last_sync_at IS NULL
                            THEN bank_cash.last_sync_at
                        ELSE GREATEST(
                            bank_cash.last_sync_at,
                            asset_totals.last_sync_at
                        )
                    END AS last_sync_at
                FROM preferred_currency, bank_cash, asset_totals
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().one()
        return _summary_from_row(row)


async def get_net_worth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NetWorthService:
    """Construit le service de patrimoine net pour FastAPI."""

    return NetWorthService(session)


def _summary_from_row(row) -> NetWorthSummary:
    values = [
        ("bank_cash", "Cash bancaire", row.bank_cash_total),
        ("crypto", "Crypto", row.crypto_total),
        ("stocks", "Actions", row.stocks_total),
        ("other_assets", "Autres actifs", row.other_assets_total),
    ]
    total = row.estimated_net_worth or Decimal("0")
    allocation = [
        AssetClassAllocation(
            asset_class=asset_class,
            label=label,
            value=value or Decimal("0"),
            percentage=_percentage(value or Decimal("0"), total),
        )
        for asset_class, label, value in values
    ]
    return NetWorthSummary(
        currency=row.currency,
        bank_cash_total=row.bank_cash_total or Decimal("0"),
        crypto_total=row.crypto_total or Decimal("0"),
        stocks_total=row.stocks_total or Decimal("0"),
        other_assets_total=row.other_assets_total or Decimal("0"),
        estimated_net_worth=total,
        allocation=allocation,
        last_sync_at=row.last_sync_at,
    )


def _percentage(value: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0")
    return (value / total * Decimal("100")).quantize(Decimal("0.01"))
