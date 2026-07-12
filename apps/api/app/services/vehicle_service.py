"""Service métier pour les véhicules."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.vehicle import Vehicle, VehicleEvent
from app.schemas.vehicle import VehicleCreate, VehicleEventCreate, VehicleUpdate

TECHNICAL_INSPECTION_REMINDER_OFFSETS = (90, 60, 30, 15, 7)
TECHNICAL_INSPECTION_REMINDER_RULE_PREFIX = "vehicle:technical_inspection_due_date"

VEHICLE_COLUMNS = """
    id, user_id, brand, model, version, registration_masked, vin_hash,
    first_registration_date, mileage_current, mileage_updated_at,
    technical_inspection_due_date, insurance_contract_id, maintenance_notes,
    created_at, updated_at
"""

VEHICLE_EVENT_COLUMNS = """
    id, vehicle_id, event_type, event_date, mileage, title, description, cost,
    document_id, next_due_date, next_due_mileage, created_at
"""


class VehicleService:
    """Orchestre les opérations de lecture et d'écriture des véhicules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_vehicles(self, user_id: UUID) -> list[Vehicle]:
        """Liste les véhicules de l'utilisateur courant."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {VEHICLE_COLUMNS}
                FROM vehicles
                WHERE user_id = :user_id
                ORDER BY brand ASC, model ASC, created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_vehicle_from_row(row) for row in result.mappings().all()]

    async def get_vehicle(self, user_id: UUID, vehicle_id: UUID) -> Vehicle:
        """Retourne un véhicule appartenant à l'utilisateur courant."""

        row = await self._fetch_vehicle(user_id, vehicle_id)
        if row is None:
            raise_vehicle_not_found()
        return _vehicle_from_row(row)

    async def create_vehicle(self, user_id: UUID, payload: VehicleCreate) -> Vehicle:
        """Crée un véhicule pour l'utilisateur courant."""

        values = payload.model_dump()
        await self._ensure_contract_belongs_to_user(
            user_id,
            values.get("insurance_contract_id"),
        )
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO vehicles (
                    user_id, brand, model, version, registration_masked, vin_hash,
                    first_registration_date, mileage_current, mileage_updated_at,
                    technical_inspection_due_date, insurance_contract_id,
                    maintenance_notes
                ) VALUES (
                    :user_id, :brand, :model, :version, :registration_masked,
                    :vin_hash, :first_registration_date, :mileage_current,
                    :mileage_updated_at, :technical_inspection_due_date,
                    :insurance_contract_id, :maintenance_notes
                )
                RETURNING {VEHICLE_COLUMNS}
                """
            ),
            {"user_id": user_id, **values},
        )
        row = result.mappings().one()
        await self._sync_technical_inspection_reminders(user_id, row)
        await self._session.commit()
        return _vehicle_from_row(row)

    async def update_vehicle(
        self,
        user_id: UUID,
        vehicle_id: UUID,
        payload: VehicleUpdate,
    ) -> Vehicle:
        """Met à jour partiellement un véhicule de l'utilisateur courant."""

        current = await self._fetch_vehicle(user_id, vehicle_id)
        if current is None:
            raise_vehicle_not_found()

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return _vehicle_from_row(current)
        if "insurance_contract_id" in changes:
            await self._ensure_contract_belongs_to_user(
                user_id,
                changes["insurance_contract_id"],
            )

        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        result = await self._session.execute(
            text(
                f"""
                UPDATE vehicles
                SET {assignments},
                    updated_at = now()
                WHERE id = :vehicle_id
                  AND user_id = :user_id
                RETURNING {VEHICLE_COLUMNS}
                """
            ),
            {"vehicle_id": vehicle_id, "user_id": user_id, **changes},
        )
        row = result.mappings().one()
        await self._sync_technical_inspection_reminders(user_id, row)
        await self._session.commit()
        return _vehicle_from_row(row)

    async def create_vehicle_event(
        self,
        user_id: UUID,
        vehicle_id: UUID,
        payload: VehicleEventCreate,
    ) -> VehicleEvent:
        """Ajoute un événement à un véhicule de l'utilisateur courant."""

        if await self._fetch_vehicle(user_id, vehicle_id) is None:
            raise_vehicle_not_found()

        values = payload.model_dump()
        await self._ensure_document_belongs_to_user(user_id, values.get("document_id"))
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO vehicle_events (
                    vehicle_id, event_type, event_date, mileage, title, description,
                    cost, document_id, next_due_date, next_due_mileage
                ) VALUES (
                    :vehicle_id, :event_type, :event_date, :mileage, :title,
                    :description, :cost, :document_id, :next_due_date,
                    :next_due_mileage
                )
                RETURNING {VEHICLE_EVENT_COLUMNS}
                """
            ),
            {"vehicle_id": vehicle_id, **values},
        )
        await self._session.commit()
        return _vehicle_event_from_row(result.mappings().one())

    async def _sync_technical_inspection_reminders(self, user_id: UUID, vehicle) -> None:
        """Synchronise les rappels d'échéance de contrôle technique du véhicule."""

        await self._delete_technical_inspection_reminders(user_id, vehicle.id)
        due_date = vehicle.technical_inspection_due_date
        if due_date is None:
            return

        today = date.today()
        vehicle_label = _vehicle_label(vehicle)
        if due_date < today:
            await self._create_technical_inspection_reminder(
                user_id=user_id,
                vehicle_id=vehicle.id,
                vehicle_label=vehicle_label,
                due_date=due_date,
                reminder_date=today,
                severity="critical",
                recurrence_rule=f"{TECHNICAL_INSPECTION_REMINDER_RULE_PREFIX}:overdue",
            )
            return

        for offset_days in TECHNICAL_INSPECTION_REMINDER_OFFSETS:
            await self._create_technical_inspection_reminder(
                user_id=user_id,
                vehicle_id=vehicle.id,
                vehicle_label=vehicle_label,
                due_date=due_date,
                reminder_date=due_date - timedelta(days=offset_days),
                severity="warning" if offset_days in (90, 60, 30) else "urgent",
                recurrence_rule=(
                    f"{TECHNICAL_INSPECTION_REMINDER_RULE_PREFIX}:J-{offset_days}"
                ),
            )

    async def _delete_technical_inspection_reminders(
        self, user_id: UUID, vehicle_id: UUID
    ) -> None:
        await self._session.execute(
            text(
                """
                DELETE FROM reminders
                WHERE user_id = :user_id
                  AND source_type = 'vehicle'
                  AND source_id = :vehicle_id
                  AND recurrence_rule LIKE :recurrence_rule_pattern
                """
            ),
            {
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "recurrence_rule_pattern": (
                    f"{TECHNICAL_INSPECTION_REMINDER_RULE_PREFIX}:%"
                ),
            },
        )

    async def _create_technical_inspection_reminder(
        self,
        *,
        user_id: UUID,
        vehicle_id: UUID,
        vehicle_label: str,
        due_date: date,
        reminder_date: date,
        severity: str,
        recurrence_rule: str,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO reminders (
                    user_id, source_type, source_id, title, description, due_date,
                    reminder_date, severity, status, recurrence_rule,
                    notification_channels
                ) VALUES (
                    :user_id, 'vehicle', :vehicle_id, :title, :description,
                    :due_date, :reminder_date, :severity, 'pending',
                    :recurrence_rule, ARRAY[]::TEXT[]
                )
                """
            ),
            {
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "title": f"Contrôle technique à prévoir - {vehicle_label}",
                "description": (
                    "Échéance de contrôle technique du véhicule "
                    f"{vehicle_label} le {due_date.isoformat()}."
                ),
                "due_date": due_date,
                "reminder_date": reminder_date,
                "severity": severity,
                "recurrence_rule": recurrence_rule,
            },
        )

    async def _fetch_vehicle(self, user_id: UUID, vehicle_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {VEHICLE_COLUMNS}
                FROM vehicles
                WHERE id = :vehicle_id
                  AND user_id = :user_id
                """
            ),
            {"vehicle_id": vehicle_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def _ensure_contract_belongs_to_user(
        self,
        user_id: UUID,
        contract_id: UUID | None,
    ) -> None:
        if contract_id is None:
            return
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM contracts
                WHERE id = :contract_id
                  AND user_id = :user_id
                """
            ),
            {"contract_id": contract_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrat d'assurance associé introuvable.",
            )

    async def _ensure_document_belongs_to_user(
        self,
        user_id: UUID,
        document_id: UUID | None,
    ) -> None:
        if document_id is None:
            return
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM documents
                WHERE id = :document_id
                  AND user_id = :user_id
                """
            ),
            {"document_id": document_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document associé introuvable.",
            )


async def get_vehicle_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VehicleService:
    """Construit le service de véhicules pour FastAPI."""

    return VehicleService(session)


def raise_vehicle_not_found() -> None:
    """Retourne une erreur uniforme pour un véhicule absent ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Véhicule introuvable.",
    )


def _vehicle_from_row(row) -> Vehicle:
    return Vehicle(
        id=row.id,
        user_id=row.user_id,
        brand=row.brand,
        model=row.model,
        version=row.version,
        registration_masked=row.registration_masked,
        vin_hash=row.vin_hash,
        first_registration_date=row.first_registration_date,
        mileage_current=row.mileage_current,
        mileage_updated_at=row.mileage_updated_at,
        technical_inspection_due_date=row.technical_inspection_due_date,
        insurance_contract_id=row.insurance_contract_id,
        maintenance_notes=row.maintenance_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _vehicle_event_from_row(row) -> VehicleEvent:
    return VehicleEvent(
        id=row.id,
        vehicle_id=row.vehicle_id,
        event_type=row.event_type,
        event_date=row.event_date,
        mileage=row.mileage,
        title=row.title,
        description=row.description,
        cost=row.cost,
        document_id=row.document_id,
        next_due_date=row.next_due_date,
        next_due_mileage=row.next_due_mileage,
        created_at=row.created_at,
    )


def _vehicle_label(row) -> str:
    """Construit un libellé lisible et robuste pour les rappels véhicule."""

    return " ".join(part for part in (row.brand, row.model) if part)
