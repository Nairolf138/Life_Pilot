"""Service métier pour les transactions financières."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.transaction import (
    TransactionCategoryPatch,
    TransactionDocumentLink,
    TransactionImportItem,
    TransactionImportRequest,
    TransactionImportResponse,
)

UNCERTAIN_CATEGORY_THRESHOLD = Decimal("0.8000")


@dataclass(frozen=True, slots=True)
class TransactionRecord:
    """Transaction financière retournée par le service."""

    id: UUID
    account_id: UUID
    external_id_hash: str | None
    booking_date: date
    value_date: date | None
    label_raw: str
    label_clean: str | None
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_type: str | None
    category_id: UUID | None
    subcategory_id: UUID | None
    confidence_score: Decimal | None
    is_recurring: bool
    is_internal_transfer: bool
    linked_document_id: UUID | None
    notes: str | None
    raw_data_json: dict
    created_at: datetime
    updated_at: datetime


class TransactionService:
    """Orchestre les opérations de lecture et d'écriture des transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_transactions(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        category_id: UUID | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        without_reliable_category: bool = False,
        without_document: bool = False,
    ) -> list[TransactionRecord]:
        """Liste les transactions de l'utilisateur courant avec filtres optionnels."""

        conditions = ["user_id = :user_id"]
        params: dict[str, object] = {"user_id": user_id}
        if account_id is not None:
            conditions.append("account_id = :account_id")
            params["account_id"] = account_id
        if date_from is not None:
            conditions.append("booking_date >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            conditions.append("booking_date <= :date_to")
            params["date_to"] = date_to
        if category_id is not None:
            conditions.append("category_id = :category_id")
            params["category_id"] = category_id
        if amount_min is not None:
            conditions.append("amount >= :amount_min")
            params["amount_min"] = amount_min
        if amount_max is not None:
            conditions.append("amount <= :amount_max")
            params["amount_max"] = amount_max
        if without_reliable_category:
            conditions.append(
                "(category_id IS NULL OR confidence_score IS NULL "
                "OR confidence_score < :category_threshold)"
            )
            params["category_threshold"] = UNCERTAIN_CATEGORY_THRESHOLD
        if without_document:
            conditions.append("linked_document_id IS NULL")

        result = await self._session.execute(
            text(
                f"""
                SELECT {TRANSACTION_COLUMNS}
                FROM transactions
                WHERE {" AND ".join(conditions)}
                ORDER BY booking_date DESC, created_at DESC
                """
            ),
            params,
        )
        return [_transaction_from_row(row) for row in result.mappings().all()]

    async def get_transaction(
        self,
        user_id: UUID,
        transaction_id: UUID,
    ) -> TransactionRecord:
        """Retourne une transaction appartenant à l'utilisateur courant."""

        row = await self._fetch_transaction(user_id, transaction_id)
        if row is None:
            raise_transaction_not_found()
        return _transaction_from_row(row)

    async def import_transactions(
        self,
        user_id: UUID,
        payload: TransactionImportRequest,
    ) -> TransactionImportResponse:
        """Importe un lot de transactions en ignorant les doublons détectés."""

        imported: list[TransactionRecord] = []
        duplicate_count = 0
        seen_keys: set[tuple[str | None, date, Decimal, UUID, str]] = set()

        for item in payload.transactions:
            await self._ensure_account_belongs_to_user(user_id, item.account_id)
            await self._ensure_category_belongs_to_user(user_id, item.category_id)
            await self._ensure_category_belongs_to_user(user_id, item.subcategory_id)
            external_id_hash = normalize_external_id_hash(item)
            dedup_key = (
                external_id_hash,
                item.booking_date,
                item.amount,
                item.account_id,
                normalized_label(item.label_raw),
            )
            is_duplicate = await self._is_duplicate(item, external_id_hash)
            if dedup_key in seen_keys or is_duplicate:
                duplicate_count += 1
                continue
            seen_keys.add(dedup_key)
            imported.append(
                await self._insert_transaction(user_id, item, external_id_hash)
            )

        await self._session.commit()
        return TransactionImportResponse(
            imported=len(imported),
            duplicates=duplicate_count,
            transactions=imported,
        )

    async def update_category(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: TransactionCategoryPatch,
    ) -> TransactionRecord:
        """Met à jour la catégorie d'une transaction utilisateur."""

        await self._ensure_category_belongs_to_user(user_id, payload.category_id)
        await self._ensure_category_belongs_to_user(user_id, payload.subcategory_id)
        transaction = await self._fetch_transaction(user_id, transaction_id)
        if transaction is None:
            raise_transaction_not_found()

        notes = (
            payload.notes if "notes" in payload.model_fields_set else transaction.notes
        )

        if payload.learning_scope != "transaction_only":
            await self._create_categorization_rule_from_transaction(
                user_id=user_id,
                transaction=transaction,
                payload=payload,
            )

        if payload.learning_scope == "past_and_future_similar":
            await self._apply_category_to_similar_past_transactions(
                user_id=user_id,
                transaction=transaction,
                payload=payload,
            )

        result = await self._session.execute(
            text(
                f"""
                UPDATE transactions
                SET category_id = :category_id,
                    subcategory_id = :subcategory_id,
                    notes = :notes,
                    confidence_score = :confidence_score,
                    updated_at = now()
                WHERE id = :transaction_id
                  AND user_id = :user_id
                RETURNING {TRANSACTION_COLUMNS}
                """
            ),
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "category_id": payload.category_id,
                "subcategory_id": payload.subcategory_id,
                "notes": notes,
                "confidence_score": payload.confidence_score,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise_transaction_not_found()
        await self._session.commit()
        return _transaction_from_row(row)

    async def link_document(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: TransactionDocumentLink,
    ) -> TransactionRecord:
        """Rattache un document utilisateur à une transaction utilisateur."""

        await self._ensure_document_belongs_to_user(user_id, payload.document_id)
        result = await self._session.execute(
            text(
                f"""
                UPDATE transactions
                SET linked_document_id = :document_id,
                    updated_at = now()
                WHERE id = :transaction_id
                  AND user_id = :user_id
                RETURNING {TRANSACTION_COLUMNS}
                """
            ),
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "document_id": payload.document_id,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise_transaction_not_found()
        await self._session.execute(
            text(
                """
                UPDATE documents
                SET linked_transaction_id = :transaction_id,
                    updated_at = now()
                WHERE id = :document_id
                  AND user_id = :user_id
                """
            ),
            {
                "transaction_id": transaction_id,
                "document_id": payload.document_id,
                "user_id": user_id,
            },
        )
        await self._session.commit()
        return _transaction_from_row(row)

    async def _create_categorization_rule_from_transaction(
        self,
        *,
        user_id: UUID,
        transaction,
        payload: TransactionCategoryPatch,
    ) -> None:
        match_type, pattern = _similarity_rule(transaction)
        await self._session.execute(
            text(
                """
                INSERT INTO categorization_rules (
                    user_id, name, priority, match_type, pattern, category_id,
                    subcategory_id, confidence_score, is_active
                ) VALUES (
                    :user_id, :name, 5, :match_type, :pattern, :category_id,
                    :subcategory_id, :confidence_score, true
                )
                """
            ),
            {
                "user_id": user_id,
                "name": f"Apprentissage: {pattern[:80]}",
                "match_type": match_type,
                "pattern": pattern,
                "category_id": payload.category_id,
                "subcategory_id": payload.subcategory_id,
                "confidence_score": payload.confidence_score,
            },
        )

    async def _apply_category_to_similar_past_transactions(
        self,
        *,
        user_id: UUID,
        transaction,
        payload: TransactionCategoryPatch,
    ) -> None:
        match_type, pattern = _similarity_rule(transaction)
        if match_type == "merchant_exact":
            similarity_condition = "lower(trim(merchant_name)) = lower(trim(:pattern))"
        else:
            similarity_condition = (
                "lower(coalesce(label_clean, label_raw)) LIKE :pattern_like"
            )
        await self._session.execute(
            text(
                f"""
                UPDATE transactions
                SET category_id = :category_id,
                    subcategory_id = :subcategory_id,
                    confidence_score = :confidence_score,
                    updated_at = now()
                WHERE user_id = :user_id
                  AND booking_date <= :booking_date
                  AND id != :transaction_id
                  AND {similarity_condition}
                """
            ),
            {
                "user_id": user_id,
                "transaction_id": transaction.id,
                "booking_date": transaction.booking_date,
                "pattern": pattern,
                "pattern_like": f"%{pattern.lower()}%",
                "category_id": payload.category_id,
                "subcategory_id": payload.subcategory_id,
                "confidence_score": payload.confidence_score,
            },
        )

    async def _fetch_transaction(self, user_id: UUID, transaction_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {TRANSACTION_COLUMNS}
                FROM transactions
                WHERE id = :transaction_id
                  AND user_id = :user_id
                """
            ),
            {"transaction_id": transaction_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def _insert_transaction(
        self,
        user_id: UUID,
        item: TransactionImportItem,
        external_id_hash: str,
    ) -> TransactionRecord:
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO transactions (
                    user_id, account_id, external_id_hash, booking_date, value_date,
                    label_raw, label_clean, merchant_name, amount, currency,
                    transaction_type, category_id, subcategory_id, confidence_score,
                    is_recurring, is_internal_transfer, notes, raw_data_json
                ) VALUES (
                    :user_id, :account_id, :external_id_hash,
                    :booking_date, :value_date,
                    :label_raw, :label_clean, :merchant_name, :amount, :currency,
                    :transaction_type, :category_id, :subcategory_id, :confidence_score,
                    :is_recurring, :is_internal_transfer, :notes, :raw_data_json
                )
                RETURNING {TRANSACTION_COLUMNS}
                """
            ),
            {
                "user_id": user_id,
                "external_id_hash": external_id_hash,
                **item.model_dump(exclude={"external_id", "external_id_hash"}),
            },
        )
        return _transaction_from_row(result.mappings().one())

    async def _is_duplicate(
        self,
        item: TransactionImportItem,
        external_id_hash: str,
    ) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM transactions
                WHERE account_id = :account_id
                  AND (
                    external_id_hash = :external_id_hash
                    OR (
                      booking_date = :booking_date
                      AND amount = :amount
                      AND lower(trim(label_raw)) = :label_raw
                    )
                  )
                LIMIT 1
                """
            ),
            {
                "account_id": item.account_id,
                "external_id_hash": external_id_hash,
                "booking_date": item.booking_date,
                "amount": item.amount,
                "label_raw": normalized_label(item.label_raw),
            },
        )
        return result.first() is not None

    async def _ensure_account_belongs_to_user(
        self,
        user_id: UUID,
        account_id: UUID,
    ) -> None:
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM accounts
                WHERE id = :account_id
                  AND user_id = :user_id
                """
            ),
            {"account_id": account_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")

    async def _ensure_category_belongs_to_user(
        self,
        user_id: UUID,
        category_id: UUID | None,
    ) -> None:
        if category_id is None:
            return
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM categories
                WHERE id = :category_id
                  AND (user_id = :user_id OR is_system = true)
                """
            ),
            {"category_id": category_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Catégorie introuvable.")

    async def _ensure_document_belongs_to_user(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> None:
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
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable.")


TRANSACTION_COLUMNS = """
    id, account_id, external_id_hash, booking_date, value_date, label_raw,
    label_clean, merchant_name, amount, currency, transaction_type, category_id,
    subcategory_id, confidence_score, is_recurring, is_internal_transfer,
    linked_document_id, notes, raw_data_json, created_at, updated_at
"""


def normalize_external_id_hash(item: TransactionImportItem) -> str:
    """Retourne un hash d'identifiant externe stable."""

    if item.external_id_hash is not None:
        return item.external_id_hash
    assert item.external_id is not None
    return sha256(item.external_id.encode("utf-8")).hexdigest()


def normalized_label(label: str) -> str:
    """Normalise un libellé pour la déduplication applicative."""

    return " ".join(label.strip().lower().split())


async def get_transaction_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TransactionService:
    """Construit le service de transactions pour FastAPI."""

    return TransactionService(session)


def raise_transaction_not_found() -> None:
    """Retourne une erreur uniforme pour une transaction absente ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transaction introuvable.",
    )


def _transaction_from_row(row) -> TransactionRecord:
    return TransactionRecord(
        id=row.id,
        account_id=row.account_id,
        external_id_hash=row.external_id_hash,
        booking_date=row.booking_date,
        value_date=row.value_date,
        label_raw=row.label_raw,
        label_clean=row.label_clean,
        merchant_name=row.merchant_name,
        amount=row.amount,
        currency=row.currency,
        transaction_type=row.transaction_type,
        category_id=row.category_id,
        subcategory_id=row.subcategory_id,
        confidence_score=row.confidence_score,
        is_recurring=bool(row.is_recurring),
        is_internal_transfer=bool(row.is_internal_transfer),
        linked_document_id=row.linked_document_id,
        notes=row.notes,
        raw_data_json=dict(row.raw_data_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _similarity_rule(transaction) -> tuple[str, str]:
    merchant_name = (transaction.merchant_name or "").strip()
    if merchant_name:
        return "merchant_exact", merchant_name
    label = transaction.label_clean or transaction.label_raw
    pattern = " ".join(label.strip().split())
    return "contains", pattern
