"""Schémas Pydantic pour les rappels utilisateur."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReminderSeverity(StrEnum):
    """Niveaux de sévérité d'un rappel."""

    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"


class ReminderStatus(StrEnum):
    """États métier d'un rappel."""

    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class ReminderSourceType(StrEnum):
    """Origines possibles d'un rappel."""

    DOCUMENT = "document"
    CONTRACT = "contract"
    VEHICLE = "vehicle"
    MANUAL = "manual"


class NotificationChannel(StrEnum):
    """Canaux de notification prévus pour un rappel."""

    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class ReminderBase(BaseModel):
    """Champs communs de création et de modification d'un rappel."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    due_date: date
    reminder_date: date | None = None
    severity: ReminderSeverity = ReminderSeverity.INFO
    status: ReminderStatus = ReminderStatus.PENDING
    source_type: ReminderSourceType = ReminderSourceType.MANUAL
    source_id: UUID | None = None
    recurrence_rule: str | None = Field(default=None, max_length=255)
    notification_channels: list[NotificationChannel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> ReminderBase:
        """Empêche une source manuelle de porter un identifiant externe."""

        if self.source_type == ReminderSourceType.MANUAL and self.source_id is not None:
            raise ValueError("Une source manuelle ne doit pas définir source_id.")
        if self.source_type != ReminderSourceType.MANUAL and self.source_id is None:
            raise ValueError("source_id est requis pour une source externe.")
        return self


class ReminderCreate(ReminderBase):
    """Données nécessaires à la création d'un rappel."""


class ReminderUpdate(BaseModel):
    """Modification partielle d'un rappel."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    due_date: date | None = None
    reminder_date: date | None = None
    severity: ReminderSeverity | None = None
    status: ReminderStatus | None = None
    source_type: ReminderSourceType | None = None
    source_id: UUID | None = None
    recurrence_rule: str | None = Field(default=None, max_length=255)
    notification_channels: list[NotificationChannel] | None = None


class ReminderResponse(BaseModel):
    """Représentation publique d'un rappel utilisateur."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: ReminderSourceType | None
    source_id: UUID | None
    title: str
    description: str | None
    due_date: date
    reminder_date: date | None
    severity: ReminderSeverity
    status: ReminderStatus
    recurrence_rule: str | None
    notification_channels: list[NotificationChannel]
    created_at: datetime
    updated_at: datetime
