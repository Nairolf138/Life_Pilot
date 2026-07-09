"""Rapprochement des documents financiers avec les transactions bancaires."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.audit_log_service import AuditAction, AuditActor


class MatchingLevel(StrEnum):
    """Niveaux de confiance du cahier des charges."""

    AUTOMATIC = "automatic_link"
    PROPOSAL = "proposal_to_validate"
    WEAK = "weak_candidate"
    UNMATCHED = "unmatched"


@dataclass(frozen=True, slots=True)
class MatchingCandidate:
    """Transaction candidate enrichie avec le détail du score de rapprochement."""

    transaction_id: UUID
    score: int
    level: MatchingLevel
    reasons: tuple[str, ...]
    amount: Decimal
    currency: str
    booking_date: date
    merchant_name: str | None
    label: str
    category_id: UUID | None
    linked_document_id: UUID | None


@dataclass(frozen=True, slots=True)
class MatchingResult:
    """Résultat d'un lien document / transaction persistant."""

    document_id: UUID
    transaction_id: UUID
    score: int
    level: MatchingLevel
    automatic: bool


class MatchingService:
    """Calcule, propose et applique les rapprochements document / transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_candidates_for_document(
        self,
        user_id: UUID,
        document_id: UUID,
        *,
        limit: int = 10,
    ) -> list[MatchingCandidate]:
        """Cherche les transactions candidates pour un document donné."""

        document = await self._fetch_document(user_id, document_id)
        candidates = await self._fetch_candidate_transactions(user_id, document)
        scored_candidates = [
            self.score_candidate(document=document, transaction=candidate)
            for candidate in candidates
        ]
        return sorted(
            scored_candidates,
            key=lambda candidate: (candidate.score, candidate.booking_date),
            reverse=True,
        )[:limit]

    async def auto_match_document(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> MatchingResult | None:
        """Rapproche automatiquement le meilleur candidat si son score atteint 90."""

        candidates = await self.find_candidates_for_document(
            user_id, document_id, limit=1
        )
        if not candidates or candidates[0].level != MatchingLevel.AUTOMATIC:
            return None
        candidate = candidates[0]
        return await self.link_document_to_transaction(
            user_id=user_id,
            document_id=document_id,
            transaction_id=candidate.transaction_id,
            score=candidate.score,
            actor=AuditActor.WORKER,
            automatic=True,
        )

    async def link_document_to_transaction(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        transaction_id: UUID,
        score: int | None = None,
        actor: AuditActor = AuditActor.USER,
        automatic: bool = False,
    ) -> MatchingResult:
        """Crée un lien manuel ou automatique et journalise le rapprochement."""

        document = await self._fetch_document(user_id, document_id)
        transaction = await self._fetch_transaction(
            user_id, transaction_id, document=document
        )
        effective_score = score
        if effective_score is None:
            effective_score = self.score_candidate(
                document=document,
                transaction=transaction,
            ).score
        level = matching_level(effective_score)

        before_state = {
            "document": {
                "id": str(document.id),
                "linked_transaction_id": _uuid_to_str(document.linked_transaction_id),
            },
            "transaction": {
                "id": str(transaction.id),
                "linked_document_id": _uuid_to_str(transaction.linked_document_id),
            },
        }

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
                "document_id": document_id,
                "user_id": user_id,
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE transactions
                SET linked_document_id = :document_id,
                    updated_at = now()
                WHERE id = :transaction_id
                  AND user_id = :user_id
                """
            ),
            {
                "document_id": document_id,
                "transaction_id": transaction_id,
                "user_id": user_id,
            },
        )
        after_state = {
            "document": {
                "id": str(document_id),
                "linked_transaction_id": str(transaction_id),
            },
            "transaction": {
                "id": str(transaction_id),
                "linked_document_id": str(document_id),
            },
            "score": effective_score,
            "level": level.value,
            "automatic": automatic,
        }
        await self._record_audit_log(
            user_id=user_id,
            actor=actor,
            transaction_id=transaction_id,
            before_state=before_state,
            after_state=after_state,
            reason="automatic_matching" if automatic else "manual_matching",
        )
        await self._session.commit()
        return MatchingResult(
            document_id=document_id,
            transaction_id=transaction_id,
            score=effective_score,
            level=level,
            automatic=automatic,
        )

    def score_candidate(self, *, document: Any, transaction: Any) -> MatchingCandidate:
        """Calcule un score sur 100 selon les critères du cahier des charges."""

        score = 0
        reasons: list[str] = []
        if _same_amount(document.amount, transaction.amount):
            score += 40
            reasons.append("amount_exact")
        if _date_within_three_days(
            _document_reference_date(document), transaction.booking_date
        ):
            score += 20
            reasons.append("date_within_3_days")
        if _merchant_similarity(document, transaction) >= Decimal("0.70"):
            score += 15
            reasons.append("merchant_or_provider_similar")
        if getattr(transaction, "known_provider", False):
            score += 10
            reasons.append("known_provider")
        if _category_coherent(document, transaction):
            score += 10
            reasons.append("category_coherent")
        if _known_reference(document, transaction):
            score += 5
            reasons.append("known_reference_or_contract")

        return MatchingCandidate(
            transaction_id=transaction.id,
            score=min(score, 100),
            level=matching_level(score),
            reasons=tuple(reasons),
            amount=transaction.amount,
            currency=transaction.currency,
            booking_date=transaction.booking_date,
            merchant_name=transaction.merchant_name,
            label=transaction.label_clean or transaction.label_raw,
            category_id=transaction.category_id,
            linked_document_id=transaction.linked_document_id,
        )

    async def _fetch_document(self, user_id: UUID, document_id: UUID):
        result = await self._session.execute(
            text(
                """
                SELECT id, user_id, provider, document_type, title, issuer, issue_date,
                       due_date, amount, currency, extracted_text,
                       linked_transaction_id, tags
                FROM documents
                WHERE id = :document_id
                  AND user_id = :user_id
                """
            ),
            {"document_id": document_id, "user_id": user_id},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable.")
        return row

    async def _fetch_transaction(
        self,
        user_id: UUID,
        transaction_id: UUID,
        *,
        document: Any | None = None,
    ):
        result = await self._session.execute(
            text(
                """
                SELECT t.id, t.user_id, t.booking_date, t.value_date, t.label_raw,
                       t.label_clean, t.merchant_name, t.amount, t.currency,
                       t.category_id, t.linked_document_id, t.notes,
                       t.raw_data_json, c.name AS category_name,
                       EXISTS (
                           SELECT 1
                           FROM documents d_known
                           JOIN transactions t_known
                             ON t_known.id = d_known.linked_transaction_id
                           WHERE d_known.user_id = t.user_id
                             AND t_known.user_id = t.user_id
                             AND d_known.id != :excluded_document_id
                             AND lower(coalesce(d_known.issuer, d_known.provider, '')) =
                                 lower(coalesce(:provider_name, ''))
                             AND lower(coalesce(t_known.merchant_name, '')) =
                                 lower(coalesce(t.merchant_name, ''))
                       ) AS known_provider
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.id = :transaction_id
                  AND t.user_id = :user_id
                """
            ),
            {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "excluded_document_id": document.id if document is not None else None,
                "provider_name": _provider_name(document)
                if document is not None
                else None,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction introuvable.")
        return row

    async def _fetch_candidate_transactions(self, user_id: UUID, document: Any):
        reference_date = _document_reference_date(document)
        result = await self._session.execute(
            text(
                """
                SELECT t.id, t.user_id, t.booking_date, t.value_date, t.label_raw,
                       t.label_clean, t.merchant_name, t.amount, t.currency,
                       t.category_id, t.linked_document_id, t.notes,
                       t.raw_data_json, c.name AS category_name,
                       EXISTS (
                           SELECT 1
                           FROM documents d_known
                           JOIN transactions t_known
                             ON t_known.id = d_known.linked_transaction_id
                           WHERE d_known.user_id = t.user_id
                             AND t_known.user_id = t.user_id
                             AND d_known.id != :document_id
                             AND lower(coalesce(d_known.issuer, d_known.provider, '')) =
                                 lower(coalesce(:provider_name, ''))
                             AND lower(coalesce(t_known.merchant_name, '')) =
                                 lower(coalesce(t.merchant_name, ''))
                       ) AS known_provider
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = :user_id
                  AND t.currency = :currency
                  AND (
                      t.linked_document_id IS NULL
                      OR t.linked_document_id = :document_id
                  )
                  AND (
                      :amount IS NULL
                      OR abs(t.amount) BETWEEN :amount_min AND :amount_max
                  )
                  AND (
                      CAST(:reference_date AS date) IS NULL
                      OR t.booking_date BETWEEN
                          CAST(:reference_date AS date) - INTERVAL '30 days'
                          AND CAST(:reference_date AS date) + INTERVAL '30 days'
                  )
                ORDER BY t.booking_date DESC, t.created_at DESC
                LIMIT 100
                """
            ),
            {
                "user_id": user_id,
                "document_id": document.id,
                "currency": document.currency,
                "amount": document.amount,
                "amount_min": _amount_min(document.amount),
                "amount_max": _amount_max(document.amount),
                "reference_date": reference_date,
                "provider_name": _provider_name(document),
            },
        )
        return result.mappings().all()

    async def _record_audit_log(
        self,
        *,
        user_id: UUID,
        actor: AuditActor,
        transaction_id: UUID,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        reason: str,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO audit_logs (
                    user_id, actor, action, entity_type, entity_id,
                    before_json, after_json, reason
                ) VALUES (
                    :user_id, :actor, :action, 'transaction', :entity_id,
                    :before_json, :after_json, :reason
                )
                """
            ),
            {
                "user_id": user_id,
                "actor": actor.value,
                "action": AuditAction.MATCHING.value,
                "entity_id": transaction_id,
                "before_json": before_state,
                "after_json": after_state,
                "reason": reason,
            },
        )


def matching_level(score: int) -> MatchingLevel:
    """Retourne le niveau correspondant au score sur 100."""

    if score >= 90:
        return MatchingLevel.AUTOMATIC
    if score >= 70:
        return MatchingLevel.PROPOSAL
    if score >= 40:
        return MatchingLevel.WEAK
    return MatchingLevel.UNMATCHED


def _same_amount(document_amount: Decimal | None, transaction_amount: Decimal) -> bool:
    if document_amount is None:
        return False
    return abs(document_amount) == abs(transaction_amount)


def _date_within_three_days(
    document_date: date | None,
    transaction_date: date | None,
) -> bool:
    if document_date is None or transaction_date is None:
        return False
    return abs((transaction_date - document_date).days) <= 3


def _merchant_similarity(document: Any, transaction: Any) -> Decimal:
    provider = _normalize_text(_provider_name(document))
    merchant = _normalize_text(
        transaction.merchant_name or transaction.label_clean or transaction.label_raw
    )
    if not provider or not merchant:
        return Decimal("0")
    if provider in merchant or merchant in provider:
        return Decimal("1")
    return Decimal(str(SequenceMatcher(None, provider, merchant).ratio()))


def _category_coherent(document: Any, transaction: Any) -> bool:
    category_name = _normalize_text(getattr(transaction, "category_name", None))
    document_tokens = _normalize_text(
        " ".join(
            filter(
                None,
                [
                    document.document_type,
                    document.title,
                    _provider_name(document),
                    " ".join(document.tags or []),
                ],
            )
        )
    )
    return bool(category_name and category_name in document_tokens)


def _known_reference(document: Any, transaction: Any) -> bool:
    haystack = _normalize_text(
        " ".join(
            filter(
                None,
                [
                    document.title,
                    document.extracted_text,
                    transaction.label_raw,
                    transaction.label_clean,
                    transaction.notes,
                    str(transaction.raw_data_json or {}),
                ],
            )
        )
    )
    reference_tokens = [
        token
        for token in haystack.split()
        if any(character.isdigit() for character in token) and len(token) >= 6
    ]
    return len(reference_tokens) != len(set(reference_tokens))


def _document_reference_date(document: Any) -> date | None:
    return document.due_date or document.issue_date


def _provider_name(document: Any) -> str | None:
    return document.issuer or document.provider


def _uuid_to_str(value: UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").casefold().strip().split())


def _amount_min(amount: Decimal | None) -> Decimal | None:
    if amount is None:
        return None
    return max(abs(amount) - Decimal("1.00"), Decimal("0.00"))


def _amount_max(amount: Decimal | None) -> Decimal | None:
    if amount is None:
        return None
    return abs(amount) + Decimal("1.00")


async def get_matching_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MatchingService:
    """Construit le service de rapprochement pour FastAPI."""

    return MatchingService(session)
