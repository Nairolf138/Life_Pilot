"""Service métier prévu pour la catégorisation des transactions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.services.audit_log_service import (
    AuditAction,
    AuditActor,
    AuditLogEntry,
    AuditLogService,
)


class CategorizationService:
    """Applique les règles de catégorisation et journalise leur impact."""

    def __init__(self, audit_log_service: AuditLogService) -> None:
        self._audit_log_service = audit_log_service

    async def audit_categorization(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        before_state: Mapping[str, Any],
        after_state: Mapping[str, Any],
        applied_rule: str,
        actor: AuditActor = AuditActor.SYSTEM,
    ) -> None:
        """Journalise une catégorisation automatique ou semi-automatique."""

        await self._audit_log_service.record(
            AuditLogEntry(
                user_id=user_id,
                actor=actor,
                action=AuditAction.CATEGORIZATION,
                entity_type="transaction",
                entity_id=transaction_id,
                before_state=before_state,
                after_state=after_state,
                reason=applied_rule,
            )
        )
