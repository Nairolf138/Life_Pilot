"""Modèles de persistance des actifs patrimoniaux."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AssetType(StrEnum):
    """Types d'actifs suivis par Life Pilot."""

    CASH = "cash"
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    FUND = "fund"
    BOND = "bond"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Asset:
    """Actif financier ou patrimonial appartenant à un utilisateur."""

    id: UUID
    user_id: UUID
    provider: str
    account_id: UUID | None
    asset_type: str
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


@dataclass(frozen=True, slots=True)
class AssetSummary:
    """Synthèse agrégée du patrimoine d'un utilisateur."""

    currency: str
    total_value: Decimal
    total_pnl_unrealized: Decimal
    by_type: list[dict]
