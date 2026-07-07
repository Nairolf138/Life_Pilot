"""Tâche future de notification d'expiration des consentements Open Banking."""

from __future__ import annotations


async def notify_expiring_open_banking_consents() -> None:
    """Notifier les utilisateurs avant expiration de leur consentement bancaire.

    TODO: brancher cette tâche au planificateur applicatif lorsque le système de
    jobs sera disponible. La tâche devra sélectionner les lignes ``connections``
    avec ``provider_type='open_banking'`` et ``consent_expires_at`` proche, puis
    créer une notification ou un rappel utilisateur sans renouveler le
    consentement automatiquement.
    """

    raise NotImplementedError
