"""Schémas Pydantic pour les actifs patrimoniaux."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import AssetType


class AssetResponse(BaseModel):
    """Représentation publique d'un actif."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    account_id: UUID | None
    asset_type: AssetType
    symbol: str | None
    name: str
    quantity: Decimal
    average_buy_price: Decimal | None
    current_price: Decimal | None
    currency: str
    current_value: Decimal | None
    pnl_unrealized: Decimal | None
    last_price_sync_at: datetime | None
    raw_data_json: dict
    created_at: datetime
    updated_at: datetime


class AssetTypeSummary(BaseModel):
    """Agrégat par type d'actif."""

    asset_type: AssetType
    value: Decimal
    pnl_unrealized: Decimal
    count: int


class AssetCurrencySummary(BaseModel):
    """Synthèse patrimoniale dans une devise."""

    currency: str
    total_value: Decimal
    total_pnl_unrealized: Decimal
    by_type: list[AssetTypeSummary]


class AssetSyncResponse(BaseModel):
    """Résultat d'une synchronisation des valorisations d'actifs."""

    synced_at: datetime
    updated_count: int = Field(ge=0)
    assets: list[AssetResponse]


class AssetClassAllocationResponse(BaseModel):
    """Répartition d'une classe d'actifs dans le patrimoine estimé."""

    asset_class: str
    label: str
    value: Decimal
    percentage: Decimal


class NetWorthSummaryResponse(BaseModel):
    """Synthèse globale du patrimoine estimé."""

    model_config = ConfigDict(from_attributes=True)

    currency: str
    bank_cash_total: Decimal
    crypto_total: Decimal
    stocks_total: Decimal
    other_assets_total: Decimal
    estimated_net_worth: Decimal
    allocation: list[AssetClassAllocationResponse]
    last_sync_at: datetime | None
