"""Service prévu pour le rapprochement document / transaction."""

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


class DocumentTransactionMatchingService:
    """Rapproche les documents et transactions puis audite les liens créés."""

    def __init__(self, audit_log_service: AuditLogService) -> None:
        self._audit_log_service = audit_log_service

    async def audit_match(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        before_state: Mapping[str, Any],
        after_state: Mapping[str, Any],
        matching_rule: str,
        actor: AuditActor = AuditActor.WORKER,
    ) -> None:
        """Journalise un rapprochement entre un document et une transaction."""

        await self._audit_log_service.record(
            AuditLogEntry(
                user_id=user_id,
                actor=actor,
                action=AuditAction.MATCHING,
                entity_type="transaction",
                entity_id=transaction_id,
                before_state=before_state,
                after_state=after_state,
                reason=matching_rule,
            )
        )
