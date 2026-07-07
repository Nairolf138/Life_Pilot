"""Persistance des consentements Open Banking dans la table ``connections``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.open_banking.base import ConsentCreationResult, ConsentStatus

OPEN_BANKING_PROVIDER_TYPE = "open_banking"


class OpenBankingConnectionStore:
    """Écrit les métadonnées de consentement dans ``connections``.

    Les identifiants fournisseur et autres détails techniques sont conservés
    dans ``metadata_json`` afin d'éviter de stocker des secrets ou données
    bancaires sensibles en clair dans des colonnes dédiées.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_connection(
        self,
        *,
        user_id: UUID,
        consent: ConsentCreationResult,
    ) -> UUID:
        """Crée une connexion à partir d'un consentement fournisseur."""

        result = await self._session.execute(
            text(
                """
                INSERT INTO connections (
                    user_id,
                    provider,
                    provider_type,
                    status,
                    consent_expires_at,
                    scopes,
                    metadata_json
                ) VALUES (
                    :user_id,
                    :provider,
                    :provider_type,
                    :status,
                    :consent_expires_at,
                    :scopes,
                    :metadata_json
                )
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "provider": consent.provider,
                "provider_type": OPEN_BANKING_PROVIDER_TYPE,
                "status": consent.status,
                "consent_expires_at": consent.consent_expires_at,
                "scopes": list(consent.scopes),
                "metadata_json": _metadata_with_consent_id(
                    consent.metadata,
                    consent.provider_consent_id,
                ),
            },
        )
        await self._session.commit()
        return result.scalar_one()

    async def update_consent_status(
        self,
        *,
        connection_id: UUID,
        status: ConsentStatus,
    ) -> None:
        """Met à jour le statut et l'expiration d'un consentement existant."""

        await self._session.execute(
            text(
                """
                UPDATE connections
                SET status = :status,
                    consent_expires_at = :consent_expires_at,
                    metadata_json = metadata_json || :metadata_json,
                    updated_at = now()
                WHERE id = :connection_id
                  AND provider_type = :provider_type
                """
            ),
            {
                "connection_id": connection_id,
                "provider_type": OPEN_BANKING_PROVIDER_TYPE,
                "status": status.status,
                "consent_expires_at": status.consent_expires_at,
                "metadata_json": _metadata_with_consent_id(
                    status.metadata,
                    status.provider_consent_id,
                ),
            },
        )
        await self._session.commit()


def _metadata_with_consent_id(
    metadata: dict[str, Any],
    provider_consent_id: str,
) -> dict[str, Any]:
    return {
        **metadata,
        "provider_consent_id": provider_consent_id,
    }
