"""Squelette du connecteur d'actifs eToro en lecture seule."""

from __future__ import annotations

from datetime import date

from app.connectors.assets.base import (
    AssetBalanceData,
    AssetHistorySyncResult,
    AssetPositionData,
    CredentialSource,
    PriceSnapshotData,
    ReadOnlyAssetConnector,
)


class EtoroAssetConnector(ReadOnlyAssetConnector):
    """Connecteur eToro limité aux données de portefeuille et de marché.

    Les credentials doivent être chargés uniquement via ``CredentialSource``
    (variables d'environnement ou coffre de secrets compatible) et disposer de
    droits en lecture seule côté eToro.
    """

    provider = "etoro"

    def __init__(self, *, credential_source: CredentialSource, base_url: str) -> None:
        self._credential_source = credential_source
        self._base_url = base_url.rstrip("/")

    async def list_positions(self) -> list[AssetPositionData]:
        """Liste les positions eToro accessibles en lecture seule."""

        raise NotImplementedError

    async def get_balances(self) -> list[AssetBalanceData]:
        """Récupère les soldes eToro accessibles en lecture seule."""

        raise NotImplementedError

    async def get_price_snapshot(
        self, *, symbols: tuple[str, ...]
    ) -> list[PriceSnapshotData]:
        """Récupère les derniers prix de marché pour les symboles demandés."""

        raise NotImplementedError

    async def sync_history(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AssetHistorySyncResult:
        """Synchronise l'historique eToro disponible en lecture seule."""

        raise NotImplementedError
