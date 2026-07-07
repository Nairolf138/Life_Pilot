"""Service prévu pour les corrections manuelles opérées par un utilisateur."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID

from app.services.audit_log_service import (
    AuditAction,
    AuditActor,
    AuditLogEntry,
    AuditLogService,
)


class ManualCorrectionService:
    """Centralise l'audit des corrections manuelles futures."""

    def __init__(self, audit_log_service: AuditLogService) -> None:
        self._audit_log_service = audit_log_service

    async def audit_manual_update(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_state: Mapping[str, Any],
        after_state: Mapping[str, Any],
        reason: str,
    ) -> None:
        """Journalise une correction manuelle faite par un utilisateur."""

        await self._audit_log_service.record(
            AuditLogEntry(
                user_id=user_id,
                actor=AuditActor.USER,
                action=AuditAction.MODIFICATION,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                reason=reason,
            )
        )
