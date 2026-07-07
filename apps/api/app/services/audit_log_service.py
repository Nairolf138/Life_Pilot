"""Service centralisé d'écriture des journaux d'audit Life Pilot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class AuditActor(StrEnum):
    """Acteurs autorisés à produire une entrée d'audit."""

    USER = "user"
    SYSTEM = "system"
    WORKER = "worker"
    N8N = "n8n"


class AuditAction(StrEnum):
    """Actions métier journalisées dans la table audit_logs."""

    CREATION = "creation"
    MODIFICATION = "modification"
    LOGICAL_DELETION = "logical_deletion"
    IMPORT = "import"
    CATEGORIZATION = "categorization"
    MATCHING = "matching"


class AuditDatabase(Protocol):
    """Contrat minimal attendu d'un client SQL asynchrone."""

    async def execute(
        self,
        query: str,
        values: Mapping[str, Any] | None = None,
    ) -> Any:
        """Exécute une requête SQL paramétrée."""


@dataclass(frozen=True, slots=True)
class AuditLogEntry:
    """Données nécessaires à la création d'une entrée d'audit."""

    actor: AuditActor
    action: AuditAction
    entity_type: str
    user_id: UUID | None = None
    entity_id: UUID | None = None
    before_state: Mapping[str, Any] | None = None
    after_state: Mapping[str, Any] | None = None
    reason: str | None = None


class AuditLogService:
    """Service dédié à l'enregistrement des changements auditables."""

    def __init__(self, database: AuditDatabase) -> None:
        self._database = database

    async def record(self, entry: AuditLogEntry) -> None:
        """Persiste une entrée d'audit dans la table audit_logs."""

        await self._database.execute(
            """
            INSERT INTO audit_logs (
                user_id,
                actor,
                action,
                entity_type,
                entity_id,
                before_json,
                after_json,
                reason
            ) VALUES (
                :user_id,
                :actor,
                :action,
                :entity_type,
                :entity_id,
                :before_json,
                :after_json,
                :reason
            )
            """,
            {
                "user_id": entry.user_id,
                "actor": entry.actor.value,
                "action": entry.action.value,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "before_json": dict(entry.before_state) if entry.before_state else None,
                "after_json": dict(entry.after_state) if entry.after_state else None,
                "reason": entry.reason,
            },
        )
