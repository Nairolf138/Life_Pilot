"""Squelette du connecteur Open Banking GoCardless.

Cette implémentation pose le contrat d'intégration sans appeler l'API distante.
Elle ne contient aucune capacité d'écriture bancaire.
"""

from __future__ import annotations

from datetime import date

from app.connectors.open_banking.base import (
    AccountData,
    BalanceData,
    ConsentCreationResult,
    ConsentStatus,
    OpenBankingConnector,
    TransactionData,
)


class GoCardlessOpenBankingConnector(OpenBankingConnector):
    """Connecteur GoCardless Bank Account Data, limité à la lecture."""

    provider = "gocardless"

    def __init__(self, *, secret_id: str, secret_key: str, base_url: str) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")

    async def create_consent(
        self,
        *,
        user_reference: str,
        institution_id: str,
        redirect_url: str,
        scopes: tuple[str, ...],
    ) -> ConsentCreationResult:
        """Crée une demande de consentement GoCardless.

        À implémenter avec l'endpoint de requisition GoCardless. Le résultat
        devra être persisté dans ``connections`` avec ``provider='gocardless'``,
        ``provider_type='open_banking'`` et ``consent_expires_at``.
        """

        raise NotImplementedError

    async def refresh_consent_status(
        self,
        *,
        provider_consent_id: str,
    ) -> ConsentStatus:
        """Rafraîchit le statut d'une requisition/consentement GoCardless."""

        raise NotImplementedError

    async def list_accounts(self, *, provider_consent_id: str) -> list[AccountData]:
        """Liste les comptes rattachés à un consentement GoCardless."""

        raise NotImplementedError

    async def get_balances(
        self,
        *,
        provider_consent_id: str,
        provider_account_id: str,
    ) -> list[BalanceData]:
        """Récupère les soldes d'un compte GoCardless en lecture seule."""

        raise NotImplementedError

    async def get_transactions(
        self,
        *,
        provider_consent_id: str,
        provider_account_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionData]:
        """Récupère les transactions d'un compte GoCardless en lecture seule."""

        raise NotImplementedError
