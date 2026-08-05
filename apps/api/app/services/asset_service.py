"""Service métier pour les actifs patrimoniaux."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.asset import Asset, AssetSummary

ASSET_COLUMNS = """
    id, user_id, provider, account_id, asset_type, symbol, name, quantity,
    average_buy_price, current_price, currency, current_value, pnl_unrealized,
    last_price_sync_at, raw_data_json, created_at, updated_at
"""


class AssetService:
    """Orchestre les opérations de lecture et synchronisation des actifs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_assets(self, user_id: UUID) -> list[Asset]:
        """Liste les actifs de l'utilisateur courant."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {ASSET_COLUMNS}
                FROM assets
                WHERE user_id = :user_id
                ORDER BY currency ASC, asset_type ASC, name ASC, created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_asset_from_row(row) for row in result.mappings().all()]

    async def get_summary(self, user_id: UUID) -> list[AssetSummary]:
        """Retourne une synthèse agrégée des actifs par devise et par type."""

        result = await self._session.execute(
            text(
                """
                SELECT
                    currency,
                    asset_type,
                    COUNT(*) AS asset_count,
                    COALESCE(SUM(current_value), 0) AS type_value,
                    COALESCE(SUM(pnl_unrealized), 0) AS type_pnl_unrealized
                FROM assets
                WHERE user_id = :user_id
                GROUP BY currency, asset_type
                ORDER BY currency ASC, asset_type ASC
                """
            ),
            {"user_id": user_id},
        )

        summaries: dict[str, AssetSummary] = {}
        by_type: dict[str, list[dict]] = {}
        totals: dict[str, dict[str, object]] = {}
        for row in result.mappings().all():
            currency = row.currency
            by_type.setdefault(currency, []).append(
                {
                    "asset_type": row.asset_type,
                    "value": row.type_value,
                    "pnl_unrealized": row.type_pnl_unrealized,
                    "count": row.asset_count,
                }
            )
            totals.setdefault(
                currency,
                {"total_value": 0, "total_pnl_unrealized": 0},
            )
            totals[currency]["total_value"] += row.type_value
            totals[currency]["total_pnl_unrealized"] += row.type_pnl_unrealized

        for currency, total in totals.items():
            summaries[currency] = AssetSummary(
                currency=currency,
                total_value=total["total_value"],
                total_pnl_unrealized=total["total_pnl_unrealized"],
                by_type=by_type[currency],
            )
        return list(summaries.values())

    async def sync_assets(self, user_id: UUID) -> tuple[object, list[Asset]]:
        """Recalcule les valorisations locales et marque les actifs synchronisés."""

        sync_result = await self._session.execute(
            text(
                """
                UPDATE assets
                SET current_value = ROUND(
                        (quantity * COALESCE(current_price, 0))::numeric,
                        2
                    ),
                    pnl_unrealized = CASE
                        WHEN average_buy_price IS NULL OR current_price IS NULL
                            THEN NULL
                        ELSE ROUND(
                            (quantity * (current_price - average_buy_price))::numeric,
                            2
                        )
                    END,
                    last_price_sync_at = now(),
                    updated_at = now()
                WHERE user_id = :user_id
                RETURNING last_price_sync_at
                """
            ),
            {"user_id": user_id},
        )
        rows = sync_result.mappings().all()
        await self._session.commit()
        assets = await self.list_assets(user_id)
        synced_at = rows[0].last_price_sync_at if rows else datetime.now(UTC)
        return synced_at, assets


async def get_asset_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AssetService:
    """Construit le service d'actifs pour FastAPI."""

    return AssetService(session)


def _asset_from_row(row) -> Asset:
    return Asset(
        id=row.id,
        user_id=row.user_id,
        provider=row.provider,
        account_id=row.account_id,
        asset_type=row.asset_type,
        symbol=row.symbol,
        name=row.name,
        quantity=row.quantity,
        average_buy_price=row.average_buy_price,
        current_price=row.current_price,
        currency=row.currency,
        current_value=row.current_value,
        pnl_unrealized=row.pnl_unrealized,
        last_price_sync_at=row.last_price_sync_at,
        raw_data_json=row.raw_data_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
