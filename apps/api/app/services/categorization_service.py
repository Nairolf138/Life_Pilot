"""Service métier pour la catégorisation des transactions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.audit_log_service import (
    AuditAction,
    AuditActor,
    AuditLogEntry,
    AuditLogService,
)

DEFAULT_CONFIDENCE_SCORE = Decimal("0.9000")
UNKNOWN_CONFIDENCE_SCORE = Decimal("0.0000")
SYSTEM_RULE_NAME_PREFIX = "Système:"
SUPPORTED_MATCH_TYPES = {"contains", "regex", "merchant_exact", "amount_range"}
SYSTEM_RULE_DEFINITIONS = (
    ("FULLI", "contains", "FULLI", "Voiture", "Péage"),
    ("UBER EATS", "contains", "UBER EATS", "Restaurants / livraison", None),
    ("BINANCE", "contains", "BINANCE", "Investissement", "Crypto"),
    ("ETORO", "contains", "ETORO", "Investissement", "Broker"),
    ("EDF", "contains", "EDF", "Logement", "Électricité"),
    ("IMPOTS", "contains", "IMPOTS", "Impôts", "Fiscalité"),
)


@dataclass(frozen=True, slots=True)
class CategorizationRule:
    """Règle active de catégorisation chargée depuis la base."""

    id: UUID
    name: str
    priority: int
    match_type: str
    pattern: str
    provider_filter: str | None
    amount_min: Decimal | None
    amount_max: Decimal | None
    category_id: UUID | None
    subcategory_id: UUID | None
    confidence_score: Decimal | None


@dataclass(frozen=True, slots=True)
class CategorizationResult:
    """Résultat de catégorisation à appliquer à une transaction."""

    category_id: UUID | None
    subcategory_id: UUID | None
    confidence_score: Decimal
    applied_rule: str
    rule_id: UUID | None = None


class CategorizationService:
    """Applique les règles de catégorisation et journalise leur impact."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._session = session
        self._audit_log_service = audit_log_service

    async def categorize_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        actor: AuditActor = AuditActor.SYSTEM,
    ) -> CategorizationResult:
        """Catégorise une transaction en respectant l'ordre de priorité V1."""

        transaction = await self._fetch_transaction(user_id, transaction_id)
        if transaction is None:
            raise ValueError("Transaction introuvable.")

        result = await self.resolve_category(
            user_id=user_id,
            label_raw=transaction.label_raw,
            label_clean=transaction.label_clean,
            merchant_name=transaction.merchant_name,
            amount=transaction.amount,
            provider=transaction.provider,
        )
        await self._session.execute(
            text(
                """
                UPDATE transactions
                SET category_id = :category_id,
                    subcategory_id = :subcategory_id,
                    confidence_score = :confidence_score,
                    updated_at = now()
                WHERE id = :transaction_id
                  AND user_id = :user_id
                """
            ),
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "category_id": result.category_id,
                "subcategory_id": result.subcategory_id,
                "confidence_score": result.confidence_score,
            },
        )
        await self.audit_categorization(
            user_id=user_id,
            transaction_id=transaction_id,
            before_state={
                "category_id": transaction.category_id,
                "subcategory_id": transaction.subcategory_id,
                "confidence_score": transaction.confidence_score,
            },
            after_state={
                "category_id": result.category_id,
                "subcategory_id": result.subcategory_id,
                "confidence_score": result.confidence_score,
            },
            applied_rule=result.applied_rule,
            actor=actor,
        )
        await self._session.commit()
        return result

    async def resolve_category(
        self,
        *,
        user_id: UUID,
        label_raw: str,
        amount: Decimal,
        label_clean: str | None = None,
        merchant_name: str | None = None,
        provider: str | None = None,
    ) -> CategorizationResult:
        """Résout la meilleure catégorie sans modifier la transaction."""

        await self.ensure_initial_system_rules(user_id)
        rules = await self._list_active_rules(user_id)
        for rule in sorted(rules, key=_rule_sort_key):
            if _matches(rule, label_raw, label_clean, merchant_name, amount, provider):
                return CategorizationResult(
                    category_id=rule.category_id,
                    subcategory_id=rule.subcategory_id,
                    confidence_score=rule.confidence_score or DEFAULT_CONFIDENCE_SCORE,
                    applied_rule=rule.name,
                    rule_id=rule.id,
                )

        unknown_category_id = await self._get_unknown_category_id(user_id)
        return CategorizationResult(
            category_id=unknown_category_id,
            subcategory_id=None,
            confidence_score=UNKNOWN_CONFIDENCE_SCORE,
            applied_rule="Catégorie Inconnu par défaut",
        )

    async def audit_categorization(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        before_state: Mapping[str, Any],
        after_state: Mapping[str, Any],
        applied_rule: str,
        actor: AuditActor = AuditActor.SYSTEM,
    ) -> None:
        """Journalise une catégorisation automatique ou semi-automatique."""

        if self._audit_log_service is None:
            return
        await self._audit_log_service.record(
            AuditLogEntry(
                user_id=user_id,
                actor=actor,
                action=AuditAction.CATEGORIZATION,
                entity_type="transaction",
                entity_id=transaction_id,
                before_state=before_state,
                after_state=after_state,
                reason=applied_rule,
            )
        )


    async def ensure_initial_system_rules(self, user_id: UUID) -> None:
        """Crée les règles système initiales du cahier des charges."""

        for (
            label,
            match_type,
            pattern,
            category_name,
            subcategory_name,
        ) in SYSTEM_RULE_DEFINITIONS:
            category_type = (
                "investment" if category_name == "Investissement" else "expense"
            )
            category_id = await self._ensure_category(
                user_id=user_id,
                name=category_name,
                category_type=category_type,
            )
            subcategory_id = None
            if subcategory_name is not None:
                subcategory_id = await self._ensure_category(
                    user_id=user_id,
                    name=subcategory_name,
                    category_type=category_type,
                    parent_id=category_id,
                )
            await self._session.execute(
                text(
                    """
                    INSERT INTO categorization_rules (
                        user_id, name, priority, match_type, pattern,
                        category_id, subcategory_id, confidence_score, is_active
                    )
                    SELECT :user_id, :name, 10, :match_type, :pattern,
                           :category_id, :subcategory_id, :confidence_score, true
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM categorization_rules
                        WHERE user_id = :user_id
                          AND name = :name
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "name": f"{SYSTEM_RULE_NAME_PREFIX} {label}",
                    "match_type": match_type,
                    "pattern": pattern,
                    "category_id": category_id,
                    "subcategory_id": subcategory_id,
                    "confidence_score": DEFAULT_CONFIDENCE_SCORE,
                },
            )

    async def _ensure_category(
        self,
        *,
        user_id: UUID,
        name: str,
        category_type: str,
        parent_id: UUID | None = None,
    ) -> UUID:
        result = await self._session.execute(
            text(
                """
                SELECT id
                FROM categories
                WHERE user_id = :user_id
                  AND name = :name
                  AND (
                    (:parent_id IS NULL AND parent_id IS NULL)
                    OR parent_id = :parent_id
                  )
                LIMIT 1
                """
            ),
            {"user_id": user_id, "name": name, "parent_id": parent_id},
        )
        row = result.first()
        if row is not None:
            return row.id

        result = await self._session.execute(
            text(
                """
                INSERT INTO categories (user_id, parent_id, name, type, is_system)
                VALUES (:user_id, :parent_id, :name, :category_type, true)
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "parent_id": parent_id,
                "name": name,
                "category_type": category_type,
            },
        )
        return result.one().id

    async def _list_active_rules(self, user_id: UUID) -> list[CategorizationRule]:
        result = await self._session.execute(
            text(
                """
                SELECT id, name, priority, match_type, pattern, provider_filter,
                       amount_min, amount_max, category_id, subcategory_id,
                       confidence_score
                FROM categorization_rules
                WHERE user_id = :user_id
                  AND is_active = true
                """
            ),
            {"user_id": user_id},
        )
        return [
            CategorizationRule(**row)
            for row in result.mappings().all()
            if row["match_type"] in SUPPORTED_MATCH_TYPES
        ]

    async def _get_unknown_category_id(self, user_id: UUID) -> UUID | None:
        result = await self._session.execute(
            text(
                """
                SELECT id
                FROM categories
                WHERE name = 'Inconnu'
                  AND (user_id = :user_id OR user_id IS NULL OR is_system = true)
                ORDER BY CASE WHEN user_id = :user_id THEN 0 ELSE 1 END
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        row = result.first()
        return row.id if row is not None else None

    async def _fetch_transaction(self, user_id: UUID, transaction_id: UUID):
        result = await self._session.execute(
            text(
                """
                SELECT transactions.category_id, transactions.subcategory_id,
                       transactions.confidence_score, transactions.label_raw,
                       transactions.label_clean, transactions.merchant_name,
                       transactions.amount, accounts.provider
                FROM transactions
                JOIN accounts ON accounts.id = transactions.account_id
                WHERE transactions.id = :transaction_id
                  AND transactions.user_id = :user_id
                """
            ),
            {"transaction_id": transaction_id, "user_id": user_id},
        )
        return result.mappings().first()


def _rule_sort_key(rule: CategorizationRule) -> tuple[int, int, str]:
    if rule.match_type == "merchant_exact" and not rule.name.startswith(
        SYSTEM_RULE_NAME_PREFIX
    ):
        priority_group = 0
    else:
        priority_group = 1
    return (priority_group, rule.priority, rule.name)


def _matches(
    rule: CategorizationRule,
    label_raw: str,
    label_clean: str | None,
    merchant_name: str | None,
    amount: Decimal,
    provider: str | None,
) -> bool:
    if rule.provider_filter and rule.provider_filter != provider:
        return False

    searchable = " ".join(
        value for value in (label_raw, label_clean, merchant_name) if value
    ).lower()
    pattern = rule.pattern.lower()

    if rule.match_type == "contains":
        return pattern in searchable
    if rule.match_type == "regex":
        return re.search(rule.pattern, searchable, flags=re.IGNORECASE) is not None
    if rule.match_type == "merchant_exact":
        return merchant_name is not None and merchant_name.strip().lower() == pattern
    if rule.match_type == "amount_range":
        return (rule.amount_min is None or amount >= rule.amount_min) and (
            rule.amount_max is None or amount <= rule.amount_max
        )
    return False


async def get_categorization_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategorizationService:
    """Construit le service de catégorisation pour FastAPI."""

    return CategorizationService(session)
