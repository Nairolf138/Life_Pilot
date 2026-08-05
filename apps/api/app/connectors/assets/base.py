"""Contrats communs pour les connecteurs d'actifs financiers.

Les connecteurs définis ici sont strictement limités à la lecture du
portefeuille : positions, soldes, prix et historique. Aucune méthode d'achat,
de vente, de virement ou de trading ne doit être ajoutée à cette interface.

Les credentials ne doivent jamais être passés en clair ni persistés dans le
code. Ils doivent être référencés par variables d'environnement ou par une
référence de coffre de secrets compatible avec l'environnement de déploiement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CredentialSource:
    """Référence de credentials lus depuis l'environnement ou un coffre.

    ``env_prefix`` désigne un préfixe de variables d'environnement, par exemple
    ``BINANCE`` pour ``BINANCE_API_KEY`` et ``BINANCE_API_SECRET``.
    ``vault_secret_ref`` désigne une référence opaque vers un coffre de secrets
    compatible. Les valeurs secrètes elles-mêmes ne doivent pas transiter par
    cette structure.
    """

    env_prefix: str | None = None
    vault_secret_ref: str | None = None


@dataclass(frozen=True, slots=True)
class AssetPositionData:
    """Position d'actif exposée en lecture seule par un fournisseur."""

    provider_position_id: str
    asset_type: str
    symbol: str | None
    name: str
    quantity: Decimal
    currency: str
    current_price: Decimal | None = None
    current_value: Decimal | None = None
    observed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssetBalanceData:
    """Solde cash ou assimilé exposé par un fournisseur d'actifs."""

    provider_account_id: str
    currency: str
    available: Decimal | None
    total: Decimal | None
    observed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PriceSnapshotData:
    """Instantané de prix pour un symbole suivi."""

    symbol: str
    price: Decimal
    currency: str
    observed_at: datetime
    provider_price_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssetHistorySyncResult:
    """Résultat d'une synchronisation d'historique en lecture seule."""

    provider: str
    synced_from: date | None
    synced_to: date | None
    positions_count: int = 0
    balances_count: int = 0
    prices_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ReadOnlyAssetConnector(Protocol):
    """Interface commune des connecteurs d'actifs, strictement en lecture."""

    async def list_positions(self) -> list[AssetPositionData]:
        """Liste les positions accessibles en lecture seule."""

    async def get_balances(self) -> list[AssetBalanceData]:
        """Récupère les soldes accessibles en lecture seule."""

    async def get_price_snapshot(
        self, *, symbols: tuple[str, ...]
    ) -> list[PriceSnapshotData]:
        """Récupère un instantané de prix pour les symboles demandés."""

    async def sync_history(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AssetHistorySyncResult:
        """Synchronise l'historique disponible sans opération de trading."""
