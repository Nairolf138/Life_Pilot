"""Service métier pour les comptes financiers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.account import AccountUpdate, ManualAccountCreate


@dataclass(frozen=True, slots=True)
class AccountRecord:
    """Compte financier retourné par le service."""

    id: UUID
    provider: str
    account_type: str
    name: str
    iban_masked: str | None
    currency: str
    balance_current: Decimal | None
    is_active: bool


class AccountService:
    """Orchestre les opérations de lecture et d'écriture des comptes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_accounts(self, user_id: UUID) -> list[AccountRecord]:
        """Retourne les comptes actifs d'un utilisateur."""

        result = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    provider,
                    account_type,
                    name,
                    iban_masked,
                    currency,
                    balance_current,
                    is_active
                FROM accounts
                WHERE user_id = :user_id
                  AND is_active = true
                ORDER BY name ASC, created_at ASC
                """
            ),
            {"user_id": user_id},
        )
        return [_account_from_row(row) for row in result.mappings().all()]

    async def get_account(self, user_id: UUID, account_id: UUID) -> AccountRecord:
        """Retourne un compte appartenant à l'utilisateur courant."""

        row = await self._fetch_account(user_id=user_id, account_id=account_id)
        if row is None:
            raise_account_not_found()
        return _account_from_row(row)

    async def create_manual_account(
        self,
        user_id: UUID,
        payload: ManualAccountCreate,
    ) -> AccountRecord:
        """Crée un compte manuel sans connexion fournisseur externe."""

        result = await self._session.execute(
            text(
                """
                INSERT INTO accounts (
                    user_id,
                    provider,
                    account_type,
                    name,
                    iban_masked,
                    currency,
                    balance_current,
                    is_active
                ) VALUES (
                    :user_id,
                    :provider,
                    :account_type,
                    :name,
                    :iban_masked,
                    :currency,
                    :balance_current,
                    true
                )
                RETURNING
                    id,
                    provider,
                    account_type,
                    name,
                    iban_masked,
                    currency,
                    balance_current,
                    is_active
                """
            ),
            {
                "user_id": user_id,
                "provider": payload.provider,
                "account_type": payload.account_type,
                "name": payload.name,
                "iban_masked": mask_iban(payload.iban),
                "currency": payload.currency,
                "balance_current": payload.balance_current,
            },
        )
        await self._session.commit()
        return _account_from_row(result.mappings().one())

    async def update_account(
        self,
        user_id: UUID,
        account_id: UUID,
        payload: AccountUpdate,
    ) -> AccountRecord:
        """Met à jour les champs autorisés d'un compte utilisateur."""

        current = await self._fetch_account(user_id=user_id, account_id=account_id)
        if current is None:
            raise_account_not_found()

        changes = payload.model_dump(exclude_unset=True)
        if "iban" in changes:
            changes["iban_masked"] = mask_iban(changes.pop("iban"))
        if not changes:
            return _account_from_row(current)

        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        result = await self._session.execute(
            text(
                f"""
                UPDATE accounts
                SET {assignments},
                    updated_at = now()
                WHERE id = :account_id
                  AND user_id = :user_id
                RETURNING
                    id,
                    provider,
                    account_type,
                    name,
                    iban_masked,
                    currency,
                    balance_current,
                    is_active
                """
            ),
            {"account_id": account_id, "user_id": user_id, **changes},
        )
        await self._session.commit()
        return _account_from_row(result.mappings().one())

    async def _fetch_account(self, *, user_id: UUID, account_id: UUID):
        result = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    provider,
                    account_type,
                    name,
                    iban_masked,
                    currency,
                    balance_current,
                    is_active
                FROM accounts
                WHERE id = :account_id
                  AND user_id = :user_id
                """
            ),
            {"account_id": account_id, "user_id": user_id},
        )
        return result.mappings().first()


def mask_iban(iban: str | None) -> str | None:
    """Masque un IBAN en conservant uniquement ses quatre derniers caractères."""

    if iban is None:
        return None
    normalized = "".join(iban.split()).upper()
    if len(normalized) <= 4:
        return "*" * len(normalized)
    return f"{'*' * (len(normalized) - 4)}{normalized[-4:]}"


async def get_account_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountService:
    """Construit le service de comptes pour FastAPI."""

    return AccountService(session)


def raise_account_not_found() -> None:
    """Retourne une erreur uniforme pour un compte absent ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Compte introuvable.",
    )


def _account_from_row(row) -> AccountRecord:
    return AccountRecord(
        id=row.id,
        provider=row.provider,
        account_type=row.account_type,
        name=row.name,
        iban_masked=row.iban_masked,
        currency=row.currency,
        balance_current=row.balance_current,
        is_active=bool(row.is_active),
    )
