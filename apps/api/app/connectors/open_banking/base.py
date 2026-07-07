"""Contrats communs pour les connecteurs Open Banking.

Les connecteurs définis ici sont volontairement limités à la lecture :
création/rafraîchissement de consentement, consultation des comptes, soldes et
transactions. Aucune méthode d'initiation de paiement ou d'écriture bancaire ne
fait partie de l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ConsentCreationResult:
    """Résultat de création d'un consentement chez un fournisseur Open Banking."""

    provider: str
    provider_consent_id: str
    status: str
    authorization_url: str
    consent_expires_at: datetime | None
    scopes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConsentStatus:
    """Statut courant d'un consentement fournisseur."""

    provider_consent_id: str
    status: str
    consent_expires_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AccountData:
    """Compte bancaire exposé par un connecteur Open Banking."""

    provider_account_id: str
    name: str
    currency: str
    account_type: str = "checking"
    iban: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BalanceData:
    """Solde associé à un compte Open Banking."""

    provider_account_id: str
    current: Decimal | None
    available: Decimal | None
    currency: str
    observed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransactionData:
    """Transaction bancaire lue depuis un fournisseur Open Banking."""

    provider_transaction_id: str
    provider_account_id: str
    booking_date: date
    amount: Decimal
    currency: str
    label: str
    value_date: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OpenBankingConnector(Protocol):
    """Interface commune de connecteur Open Banking en lecture seule."""

    async def create_consent(
        self,
        *,
        user_reference: str,
        institution_id: str,
        redirect_url: str,
        scopes: tuple[str, ...],
    ) -> ConsentCreationResult:
        """Crée un consentement utilisateur chez le fournisseur."""

    async def refresh_consent_status(
        self,
        *,
        provider_consent_id: str,
    ) -> ConsentStatus:
        """Rafraîchit le statut d'un consentement fournisseur."""

    async def list_accounts(self, *, provider_consent_id: str) -> list[AccountData]:
        """Liste les comptes accessibles par le consentement."""

    async def get_balances(
        self,
        *,
        provider_consent_id: str,
        provider_account_id: str,
    ) -> list[BalanceData]:
        """Récupère les soldes d'un compte accessible en lecture."""

    async def get_transactions(
        self,
        *,
        provider_consent_id: str,
        provider_account_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionData]:
        """Récupère les transactions d'un compte accessible en lecture."""
