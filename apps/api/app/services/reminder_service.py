"""Service métier pour les rappels utilisateur."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.reminder import ReminderCreate, ReminderSourceType, ReminderUpdate


@dataclass(frozen=True, slots=True)
class ReminderRecord:
    """Rappel retourné par le service."""

    id: UUID
    source_type: str | None
    source_id: UUID | None
    title: str
    description: str | None
    due_date: date
    reminder_date: date | None
    severity: str
    status: str
    recurrence_rule: str | None
    notification_channels: list[str]
    created_at: datetime
    updated_at: datetime


class ReminderService:
    """Orchestre les opérations de lecture et d'écriture des rappels."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_reminders(self, user_id: UUID) -> list[ReminderRecord]:
        """Liste les rappels de l'utilisateur courant, par échéance croissante."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {REMINDER_COLUMNS}
                FROM reminders
                WHERE user_id = :user_id
                ORDER BY due_date ASC, reminder_date ASC NULLS LAST, created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_reminder_from_row(row) for row in result.mappings().all()]

    async def create_reminder(
        self,
        user_id: UUID,
        payload: ReminderCreate,
    ) -> ReminderRecord:
        """Crée un rappel manuel ou rattaché à une source utilisateur."""

        await self._ensure_source_belongs_to_user(
            user_id, payload.source_type, payload.source_id
        )
        values = payload.model_dump()
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO reminders (
                    user_id, source_type, source_id, title, description, due_date,
                    reminder_date, severity, status, recurrence_rule,
                    notification_channels
                ) VALUES (
                    :user_id, :source_type, :source_id, :title, :description,
                    :due_date, :reminder_date, :severity, :status,
                    :recurrence_rule, :notification_channels
                )
                RETURNING {REMINDER_COLUMNS}
                """
            ),
            {"user_id": user_id, **values},
        )
        await self._session.commit()
        return _reminder_from_row(result.mappings().one())

    async def update_reminder(
        self,
        user_id: UUID,
        reminder_id: UUID,
        payload: ReminderUpdate,
    ) -> ReminderRecord:
        """Met à jour partiellement un rappel de l'utilisateur courant."""

        current = await self._fetch_reminder(user_id, reminder_id)
        if current is None:
            raise_reminder_not_found()

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return _reminder_from_row(current)

        source_type = changes.get("source_type", current.source_type)
        source_id = changes.get("source_id", current.source_id)
        _validate_source_pair(source_type, source_id)
        await self._ensure_source_belongs_to_user(user_id, source_type, source_id)

        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        result = await self._session.execute(
            text(
                f"""
                UPDATE reminders
                SET {assignments},
                    updated_at = now()
                WHERE id = :reminder_id
                  AND user_id = :user_id
                RETURNING {REMINDER_COLUMNS}
                """
            ),
            {"reminder_id": reminder_id, "user_id": user_id, **changes},
        )
        await self._session.commit()
        return _reminder_from_row(result.mappings().one())

    async def complete_reminder(
        self,
        user_id: UUID,
        reminder_id: UUID,
    ) -> ReminderRecord:
        """Marque un rappel comme terminé."""

        result = await self._session.execute(
            text(
                f"""
                UPDATE reminders
                SET status = 'completed',
                    updated_at = now()
                WHERE id = :reminder_id
                  AND user_id = :user_id
                RETURNING {REMINDER_COLUMNS}
                """
            ),
            {"reminder_id": reminder_id, "user_id": user_id},
        )
        row = result.mappings().first()
        if row is None:
            raise_reminder_not_found()
        await self._session.commit()
        return _reminder_from_row(row)

    async def _fetch_reminder(self, user_id: UUID, reminder_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {REMINDER_COLUMNS}
                FROM reminders
                WHERE id = :reminder_id
                  AND user_id = :user_id
                """
            ),
            {"reminder_id": reminder_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def _ensure_source_belongs_to_user(
        self,
        user_id: UUID,
        source_type: str | None,
        source_id: UUID | str | None,
    ) -> None:
        source_type_value = str(source_type) if source_type is not None else None
        if (
            source_type_value is None
            or source_type_value == ReminderSourceType.MANUAL.value
        ):
            return
        table_by_source = {
            ReminderSourceType.DOCUMENT.value: "documents",
            ReminderSourceType.CONTRACT.value: "contracts",
            ReminderSourceType.VEHICLE.value: "vehicles",
        }
        table = table_by_source.get(source_type_value)
        if table is None or source_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Source de rappel invalide.",
            )
        result = await self._session.execute(
            text(
                f"""
                SELECT 1
                FROM {table}
                WHERE id = :source_id
                  AND user_id = :user_id
                """
            ),
            {"source_id": source_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source de rappel introuvable.",
            )


REMINDER_COLUMNS = """
    id, source_type, source_id, title, description, due_date, reminder_date,
    severity, status, recurrence_rule, notification_channels, created_at, updated_at
"""


async def get_reminder_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReminderService:
    """Construit le service de rappels pour FastAPI."""

    return ReminderService(session)


def raise_reminder_not_found() -> None:
    """Retourne une erreur uniforme pour un rappel absent ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Rappel introuvable.",
    )


def _validate_source_pair(
    source_type: str | None,
    source_id: UUID | str | None,
) -> None:
    source_type_value = str(source_type) if source_type is not None else None
    if source_type_value == ReminderSourceType.MANUAL.value and source_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une source manuelle ne doit pas définir source_id.",
        )
    if (
        source_type_value is not None
        and source_type_value != ReminderSourceType.MANUAL.value
        and source_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_id est requis pour une source externe.",
        )


def _reminder_from_row(row) -> ReminderRecord:
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
