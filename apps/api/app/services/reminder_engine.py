"""Moteur de sélection et de cycle de vie des rappels.

Le moteur reste volontairement indépendant d'un fournisseur de notification : il
charge les rappels actifs, transforme les rappels échus en candidats à notifier,
marque les candidats comme envoyés pour éviter les doublons, puis expose les
actions utilisateur de complétion ou de rejet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.reminder_service import REMINDER_COLUMNS, ReminderRecord


class ReminderEngineSeverity(StrEnum):
    """Sévérités gérées par la politique de priorité du moteur."""

    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"


class ReminderEngineStatus(StrEnum):
    """Statuts gérés par le moteur d'exécution des rappels."""

    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


@dataclass(frozen=True, slots=True)
class NotificationCandidate:
    """Notification prête à être remise à un adaptateur email, push ou in-app."""

    reminder_id: UUID
    user_id: UUID
    title: str
    description: str | None
    due_date: date
    reminder_date: date | None
    severity: ReminderEngineSeverity
    priority: int
    channels: list[str]
    deduplication_key: str


@dataclass(frozen=True, slots=True)
class ReminderLifecycleResult:
    """Résultat minimal d'une action de cycle de vie sur un rappel."""

    reminder_id: UUID
    status: ReminderEngineStatus
    updated_at: datetime


class ReminderEngine:
    """Évalue les rappels actifs et orchestre leur cycle de notification."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_active_reminders(
        self, *, now: datetime | None = None
    ) -> list[ReminderRecord]:
        """Charge les rappels encore actionnables par ordre de priorité métier."""

        today = _business_date(now)
        result = await self._session.execute(
            text(
                f"""
                SELECT {REMINDER_COLUMNS}
                FROM reminders
                WHERE status IN ('pending', 'sent')
                  AND due_date >= :today
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'urgent' THEN 2
                        WHEN 'warning' THEN 3
                        ELSE 4
                    END,
                    COALESCE(reminder_date, due_date) ASC,
                    due_date ASC,
                    created_at ASC
                """
            ),
            {"today": today},
        )
        return [_reminder_record_from_row(row) for row in result.mappings().all()]

    async def collect_due_candidates(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
        mark_as_sent: bool = True,
    ) -> list[NotificationCandidate]:
        """Produit des notifications candidates pour les rappels arrivés à échéance.

        Seuls les rappels ``pending`` sont éligibles : dès qu'un candidat est
        produit, son statut peut être passé à ``sent`` dans la même transaction,
        ce qui rend l'opération idempotente et évite les doublons lors des appels
        suivants.
        """

        today = _business_date(now)
        result = await self._session.execute(
            text(
                """
                SELECT
                    id, user_id, title, description, due_date, reminder_date,
                    severity, notification_channels
                FROM reminders
                WHERE status = 'pending'
                  AND COALESCE(reminder_date, due_date) <= :today
                  AND due_date >= :today
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'urgent' THEN 2
                        WHEN 'warning' THEN 3
                        ELSE 4
                    END,
                    COALESCE(reminder_date, due_date) ASC,
                    due_date ASC,
                    created_at ASC
                LIMIT :limit
                """
            ),
            {"today": today, "limit": limit},
        )
        rows = result.mappings().all()
        candidates = [_candidate_from_row(row) for row in rows]

        if mark_as_sent and candidates:
            await self._session.execute(
                text(
                    """
                    UPDATE reminders
                    SET status = 'sent', updated_at = now()
                    WHERE id = ANY(:reminder_ids)
                      AND status = 'pending'
                    """
                ),
                {"reminder_ids": [candidate.reminder_id for candidate in candidates]},
            )
            await self._session.commit()

        return candidates

    async def complete_reminder(
        self, reminder_id: UUID, *, user_id: UUID
    ) -> ReminderLifecycleResult:
        """Marque un rappel comme complété après une action positive utilisateur."""

        return await self._set_user_terminal_status(
            reminder_id,
            user_id=user_id,
            next_status=ReminderEngineStatus.COMPLETED,
        )

    async def dismiss_reminder(
        self, reminder_id: UUID, *, user_id: UUID
    ) -> ReminderLifecycleResult:
        """Marque un rappel comme expiré/rejeté après une action utilisateur."""

        return await self._set_user_terminal_status(
            reminder_id,
            user_id=user_id,
            next_status=ReminderEngineStatus.DISMISSED,
        )

    async def dismiss_expired_reminders(self, *, now: datetime | None = None) -> int:
        """Expire les rappels dépassés qui ne peuvent plus être notifiés utilement."""

        today = _business_date(now)
        result = await self._session.execute(
            text(
                """
                UPDATE reminders
                SET status = 'dismissed', updated_at = now()
                WHERE status IN ('pending', 'sent')
                  AND due_date < :today
                """
            ),
            {"today": today},
        )
        await self._session.commit()
        return int(result.rowcount or 0)

    async def _set_user_terminal_status(
        self,
        reminder_id: UUID,
        *,
        user_id: UUID,
        next_status: ReminderEngineStatus,
    ) -> ReminderLifecycleResult:
        result = await self._session.execute(
            text(
                """
                UPDATE reminders
                SET status = :next_status, updated_at = now()
                WHERE id = :reminder_id
                  AND user_id = :user_id
                  AND status IN ('pending', 'sent')
                RETURNING id, status, updated_at
                """
            ),
            {
                "reminder_id": reminder_id,
                "user_id": user_id,
                "next_status": next_status.value,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rappel actif introuvable.",
            )
        await self._session.commit()
        return ReminderLifecycleResult(
            reminder_id=row.id,
            status=ReminderEngineStatus(row.status),
            updated_at=row.updated_at,
        )


async def get_reminder_engine(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReminderEngine:
    """Construit le moteur de rappels pour injection FastAPI ou workers."""

    return ReminderEngine(session)


def _business_date(now: datetime | None) -> date:
    if now is None:
        return datetime.now(UTC).date()
    return now.date()


def _candidate_from_row(row) -> NotificationCandidate:
    severity = ReminderEngineSeverity(row.severity)
    priority = _PRIORITY_BY_SEVERITY[severity]
    return NotificationCandidate(
        reminder_id=row.id,
        user_id=row.user_id,
        title=row.title,
        description=row.description,
        due_date=row.due_date,
        reminder_date=row.reminder_date,
        severity=severity,
        priority=priority,
        channels=list(row.notification_channels or []),
        deduplication_key=f"reminder:{row.id}:{row.due_date.isoformat()}",
    )


def _reminder_record_from_row(row) -> ReminderRecord:
    return ReminderRecord(
        id=row.id,
        source_type=row.source_type,
        source_id=row.source_id,
        title=row.title,
        description=row.description,
        due_date=row.due_date,
        reminder_date=row.reminder_date,
        severity=row.severity,
        status=row.status,
        recurrence_rule=row.recurrence_rule,
        notification_channels=list(row.notification_channels or []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


_PRIORITY_BY_SEVERITY = {
    ReminderEngineSeverity.CRITICAL: 1,
    ReminderEngineSeverity.URGENT: 2,
    ReminderEngineSeverity.WARNING: 3,
    ReminderEngineSeverity.INFO: 4,
}
