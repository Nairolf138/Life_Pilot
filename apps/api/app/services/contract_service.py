"""Service métier pour les contrats et abonnements."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.contract import Contract
from app.schemas.contract import ContractCreate, ContractUpdate

CONTRACT_COLUMNS = """
    id, user_id, provider, contract_type, name, reference, start_date, end_date,
    renewal_date, notice_period_days, monthly_cost, yearly_cost, payment_frequency,
    status, document_id, notes, created_at, updated_at
"""


class ContractService:
    """Orchestre les opérations de lecture et d'écriture des contrats."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_contracts(self, user_id: UUID) -> list[Contract]:
        """Liste les contrats de l'utilisateur courant."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {CONTRACT_COLUMNS}
                FROM contracts
                WHERE user_id = :user_id
                ORDER BY renewal_date ASC NULLS LAST, provider ASC, created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_contract_from_row(row) for row in result.mappings().all()]

    async def get_contract(self, user_id: UUID, contract_id: UUID) -> Contract:
        """Retourne un contrat appartenant à l'utilisateur courant."""

        row = await self._fetch_contract(user_id, contract_id)
        if row is None:
            raise_contract_not_found()
        return _contract_from_row(row)

    async def create_contract(self, user_id: UUID, payload: ContractCreate) -> Contract:
        """Crée un contrat ou abonnement pour l'utilisateur courant."""

        values = payload.model_dump()
        await self._ensure_document_belongs_to_user(user_id, values.get("document_id"))
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO contracts (
                    user_id, provider, contract_type, name, reference, start_date,
                    end_date, renewal_date, notice_period_days, monthly_cost,
                    yearly_cost, payment_frequency, status, document_id, notes
                ) VALUES (
                    :user_id, :provider, :contract_type, :name, :reference,
                    :start_date, :end_date, :renewal_date, :notice_period_days,
                    :monthly_cost, :yearly_cost, :payment_frequency, :status,
                    :document_id, :notes
                )
                RETURNING {CONTRACT_COLUMNS}
                """
            ),
            {"user_id": user_id, **values},
        )
        await self._session.commit()
        return _contract_from_row(result.mappings().one())

    async def update_contract(
        self,
        user_id: UUID,
        contract_id: UUID,
        payload: ContractUpdate,
    ) -> Contract:
        """Met à jour partiellement un contrat de l'utilisateur courant."""

        current = await self._fetch_contract(user_id, contract_id)
        if current is None:
            raise_contract_not_found()

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return _contract_from_row(current)
        if "document_id" in changes:
            await self._ensure_document_belongs_to_user(user_id, changes["document_id"])

        start_date = changes.get("start_date", current.start_date)
        end_date = changes.get("end_date", current.end_date)
        if start_date and end_date and end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_date doit être postérieure ou égale à start_date.",
            )

        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        result = await self._session.execute(
            text(
                f"""
                UPDATE contracts
                SET {assignments},
                    updated_at = now()
                WHERE id = :contract_id
                  AND user_id = :user_id
                RETURNING {CONTRACT_COLUMNS}
                """
            ),
            {"contract_id": contract_id, "user_id": user_id, **changes},
        )
        await self._session.commit()
        return _contract_from_row(result.mappings().one())

    async def _fetch_contract(self, user_id: UUID, contract_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {CONTRACT_COLUMNS}
                FROM contracts
                WHERE id = :contract_id
                  AND user_id = :user_id
                """
            ),
            {"contract_id": contract_id, "user_id": user_id},
        )
        return result.mappings().first()

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


async def get_contract_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContractService:
    """Construit le service de contrats pour FastAPI."""

    return ContractService(session)


def raise_contract_not_found() -> None:
    """Retourne une erreur uniforme pour un contrat absent ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Contrat introuvable.",
    )


def _contract_from_row(row) -> Contract:
    return Contract(
        id=row.id,
        user_id=row.user_id,
        provider=row.provider,
        contract_type=row.contract_type,
        name=row.name,
        reference=row.reference,
        start_date=row.start_date,
        end_date=row.end_date,
        renewal_date=row.renewal_date,
        notice_period_days=row.notice_period_days,
        monthly_cost=row.monthly_cost,
        yearly_cost=row.yearly_cost,
        payment_frequency=row.payment_frequency,
        status=row.status,
        document_id=row.document_id,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
