"""Détection des transactions récurrentes et alertes associées.

Le service analyse l'historique bancaire par compte, catégorie et marchand (ou
libellé nettoyé) afin de repérer les prélèvements hebdomadaires, mensuels ou
annuels. Lorsqu'une récurrence est détectée, les transactions concernées sont
marquées comme récurrentes et un contrat actif existant est associé par
suggestion. À défaut de contrat trouvé, une alerte invite l'utilisateur à créer
le contrat correspondant.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from statistics import median
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.contract import ContractPaymentFrequency, ContractType

MIN_WEEKLY_OCCURRENCES = 4
MIN_MONTHLY_OCCURRENCES = 3
MIN_YEARLY_OCCURRENCES = 2
AMOUNT_ABSOLUTE_TOLERANCE = Decimal("2.00")
AMOUNT_RELATIVE_TOLERANCE = Decimal("0.08")
PRICE_INCREASE_RELATIVE_THRESHOLD = Decimal("0.10")
PRICE_INCREASE_ABSOLUTE_THRESHOLD = Decimal("2.00")
DUPLICATE_DAY_TOLERANCE = 3


class RecurrencePeriod(StrEnum):
    """Périodicités actuellement reconnues."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceAlertType(StrEnum):
    """Types d'alertes produites par la détection."""

    NEW_RECURRING_DEBIT = "new_recurring_debit"
    PRICE_INCREASE = "price_increase"
    SUBSCRIPTION_WITHOUT_CONTRACT = "subscription_without_contract"
    POTENTIAL_DUPLICATE = "potential_duplicate"


@dataclass(frozen=True, slots=True)
class RecurrenceTransaction:
    """Transaction minimale nécessaire à l'algorithme de détection."""

    id: UUID
    account_id: UUID
    booking_date: date
    label_raw: str
    label_clean: str | None
    merchant_name: str | None
    amount: Decimal
    currency: str
    category_id: UUID | None
    is_recurring: bool


@dataclass(frozen=True, slots=True)
class ContractSuggestion:
    """Contrat existant ou suggestion de contrat à créer."""

    provider: str
    name: str
    contract_type: str
    payment_frequency: str
    monthly_cost: Decimal | None
    yearly_cost: Decimal | None
    contract_id: UUID | None = None
    should_create: bool = False


@dataclass(frozen=True, slots=True)
class RecurrenceAlert:
    """Alerte métier générée pendant l'analyse."""

    alert_type: RecurrenceAlertType
    title: str
    description: str
    severity: str
    transaction_ids: tuple[UUID, ...]
    contract_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecurrenceDetection:
    """Récurrence détectée pour un groupe homogène de transactions."""

    key: str
    period: RecurrencePeriod
    account_id: UUID
    category_id: UUID | None
    merchant_or_label: str
    average_amount: Decimal
    currency: str
    first_seen_at: date
    last_seen_at: date
    transaction_ids: tuple[UUID, ...]
    contract: ContractSuggestion
    alerts: tuple[RecurrenceAlert, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RecurrenceDetectionReport:
    """Résultat d'une exécution du service."""

    detections: tuple[RecurrenceDetection, ...]
    marked_transaction_ids: tuple[UUID, ...]
    created_alerts: tuple[RecurrenceAlert, ...]


@dataclass(frozen=True, slots=True)
class _ContractCandidate:
    id: UUID
    provider: str
    name: str
    contract_type: str
    monthly_cost: Decimal | None
    yearly_cost: Decimal | None
    payment_frequency: str | None


class RecurrenceDetectionService:
    """Détecte les dépenses récurrentes et crée les alertes correspondantes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def detect_for_user(
        self,
        user_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        create_alerts: bool = True,
    ) -> RecurrenceDetectionReport:
        """Analyse les transactions d'un utilisateur et persiste les marqueurs.

        Les alertes sont enregistrées dans ``reminders`` comme alertes in-app
        manuelles afin d'éviter d'introduire une nouvelle table. Le contrat est
        suggéré lorsqu'aucun contrat actif ne correspond au marchand/libellé.
        """

        transactions = await self._fetch_transactions(user_id, date_from, date_to)
        contracts = await self._fetch_contracts(user_id)
        detections = self._detect_recurrences(transactions, contracts)
        marked_ids = tuple(
            sorted(
                {
                    tx_id
                    for detection in detections
                    for tx_id in detection.transaction_ids
                },
                key=str,
            )
        )
        if marked_ids:
            await self._mark_transactions_as_recurring(user_id, marked_ids)
        alerts = tuple(alert for detection in detections for alert in detection.alerts)
        if create_alerts and alerts:
            await self._create_alert_reminders(user_id, alerts)
        if marked_ids or (create_alerts and alerts):
            await self._session.commit()
        return RecurrenceDetectionReport(detections, marked_ids, alerts)

    def _detect_recurrences(
        self,
        transactions: Iterable[RecurrenceTransaction],
        contracts: Iterable[_ContractCandidate],
    ) -> tuple[RecurrenceDetection, ...]:
        grouped: dict[
            tuple[UUID, UUID | None, str, str], list[RecurrenceTransaction]
        ] = defaultdict(list)
        for transaction in transactions:
            if transaction.amount >= 0:
                continue
            merchant_key = _normalized_merchant_key(transaction)
            amount_bucket = _amount_bucket(transaction.amount)
            grouped[
                (
                    transaction.account_id,
                    transaction.category_id,
                    merchant_key,
                    amount_bucket,
                )
            ].append(transaction)

        detections: list[RecurrenceDetection] = []
        contract_list = list(contracts)
        for (
            account_id,
            category_id,
            merchant_key,
            _amount_bucket_value,
        ), items in grouped.items():
            ordered = sorted(items, key=lambda item: item.booking_date)
            period = _infer_period(ordered)
            if period is None:
                continue
            contract = _suggest_contract(merchant_key, period, ordered, contract_list)
            alerts = _build_alerts(merchant_key, period, ordered, contract)
            detections.append(
                RecurrenceDetection(
                    key=f"{account_id}:{category_id}:{merchant_key}:{period.value}",
                    period=period,
                    account_id=account_id,
                    category_id=category_id,
                    merchant_or_label=merchant_key,
                    average_amount=_average_abs_amount(ordered),
                    currency=ordered[-1].currency,
                    first_seen_at=ordered[0].booking_date,
                    last_seen_at=ordered[-1].booking_date,
                    transaction_ids=tuple(item.id for item in ordered),
                    contract=contract,
                    alerts=alerts,
                )
            )
        return tuple(detections)

    async def _fetch_transactions(
        self, user_id: UUID, date_from: date | None, date_to: date | None
    ) -> list[RecurrenceTransaction]:
        conditions = ["user_id = :user_id"]
        params: dict[str, object] = {"user_id": user_id}
        if date_from is not None:
            conditions.append("booking_date >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            conditions.append("booking_date <= :date_to")
            params["date_to"] = date_to
        result = await self._session.execute(
            text(
                f"""
                SELECT id, account_id, booking_date, label_raw, label_clean,
                       merchant_name, amount, currency, category_id, is_recurring
                FROM transactions
                WHERE {" AND ".join(conditions)}
                ORDER BY account_id, category_id, booking_date
                """
            ),
            params,
        )
        return [RecurrenceTransaction(**row) for row in result.mappings().all()]

    async def _fetch_contracts(self, user_id: UUID) -> list[_ContractCandidate]:
        result = await self._session.execute(
            text(
                """
                SELECT id, provider, name, contract_type, monthly_cost, yearly_cost,
                       payment_frequency
                FROM contracts
                WHERE user_id = :user_id
                  AND status IN ('active', 'to_review')
                """
            ),
            {"user_id": user_id},
        )
        return [_ContractCandidate(**row) for row in result.mappings().all()]

    async def _mark_transactions_as_recurring(
        self, user_id: UUID, transaction_ids: tuple[UUID, ...]
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE transactions
                SET is_recurring = true,
                    updated_at = now()
                WHERE user_id = :user_id
                  AND id = ANY(:transaction_ids)
                """
            ),
            {"user_id": user_id, "transaction_ids": list(transaction_ids)},
        )

    async def _create_alert_reminders(
        self, user_id: UUID, alerts: tuple[RecurrenceAlert, ...]
    ) -> None:
        today = date.today()
        for alert in alerts:
            await self._session.execute(
                text(
                    """
                    INSERT INTO reminders (
                        user_id, source_type, source_id, title, description,
                        due_date, reminder_date, severity, status,
                        recurrence_rule, notification_channels
                    ) VALUES (
                        :user_id, 'manual', NULL, :title, :description,
                        :due_date, :reminder_date, :severity, 'pending',
                        NULL, ARRAY['in_app']
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "title": alert.title,
                    "description": alert.description,
                    "due_date": today,
                    "reminder_date": today,
                    "severity": alert.severity,
                },
            )


def _normalized_merchant_key(transaction: RecurrenceTransaction) -> str:
    value = (
        transaction.merchant_name or transaction.label_clean or transaction.label_raw
    )
    value = value.lower()
    value = re.sub(r"\b\d{2,}\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()[:120] or "unknown"


def _amount_bucket(amount: Decimal) -> str:
    absolute = abs(amount)
    bucket = max(AMOUNT_ABSOLUTE_TOLERANCE, absolute * AMOUNT_RELATIVE_TOLERANCE)
    rounded = (absolute / bucket).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * bucket
    return str(rounded.quantize(Decimal("0.01")))


def _infer_period(transactions: list[RecurrenceTransaction]) -> RecurrencePeriod | None:
    if len(transactions) < MIN_YEARLY_OCCURRENCES:
        return None
    day_gaps = [
        (current.booking_date - previous.booking_date).days
        for previous, current in zip(transactions, transactions[1:], strict=False)
    ]
    if not day_gaps:
        return None
    median_gap = median(day_gaps)
    if len(transactions) >= MIN_WEEKLY_OCCURRENCES and 5 <= median_gap <= 9:
        return RecurrencePeriod.WEEKLY
    if len(transactions) >= MIN_MONTHLY_OCCURRENCES and 25 <= median_gap <= 35:
        return RecurrencePeriod.MONTHLY
    if len(transactions) >= MIN_YEARLY_OCCURRENCES and 350 <= median_gap <= 380:
        return RecurrencePeriod.YEARLY
    return None


def _suggest_contract(
    merchant_key: str,
    period: RecurrencePeriod,
    transactions: list[RecurrenceTransaction],
    contracts: list[_ContractCandidate],
) -> ContractSuggestion:
    matching_contract = next(
        (
            contract
            for contract in contracts
            if _text_matches_contract(merchant_key, contract)
        ),
        None,
    )
    monthly_cost, yearly_cost = _contract_costs(period, transactions)
    frequency = _payment_frequency(period)
    if matching_contract is not None:
        return ContractSuggestion(
            provider=matching_contract.provider,
            name=matching_contract.name,
            contract_type=matching_contract.contract_type,
            payment_frequency=matching_contract.payment_frequency or frequency,
            monthly_cost=matching_contract.monthly_cost or monthly_cost,
            yearly_cost=matching_contract.yearly_cost or yearly_cost,
            contract_id=matching_contract.id,
            should_create=False,
        )
    provider = merchant_key.title()
    return ContractSuggestion(
        provider=provider,
        name=provider,
        contract_type=ContractType.OTHER.value,
        payment_frequency=frequency,
        monthly_cost=monthly_cost,
        yearly_cost=yearly_cost,
        should_create=True,
    )


def _build_alerts(
    merchant_key: str,
    period: RecurrencePeriod,
    transactions: list[RecurrenceTransaction],
    contract: ContractSuggestion,
) -> tuple[RecurrenceAlert, ...]:
    latest = transactions[-1]
    transaction_ids = tuple(transaction.id for transaction in transactions)
    alerts = [
        RecurrenceAlert(
            alert_type=RecurrenceAlertType.NEW_RECURRING_DEBIT,
            title=f"Nouveau prélèvement récurrent détecté : {merchant_key}",
            description=(
                f"{len(transactions)} opérations {period.value} ont été repérées."
            ),
            severity="info",
            transaction_ids=transaction_ids,
            contract_id=contract.contract_id,
        )
    ]
    if contract.should_create:
        alerts.append(
            RecurrenceAlert(
                alert_type=RecurrenceAlertType.SUBSCRIPTION_WITHOUT_CONTRACT,
                title=f"Abonnement sans contrat associé : {merchant_key}",
                description="Créez ou rattachez un contrat pour suivre cet abonnement.",
                severity="warning",
                transaction_ids=transaction_ids,
            )
        )
    previous_amounts = [abs(transaction.amount) for transaction in transactions[:-1]]
    if previous_amounts:
        reference = Decimal(str(median(previous_amounts))).quantize(Decimal("0.01"))
        increase = abs(latest.amount) - reference
        if (
            increase >= PRICE_INCREASE_ABSOLUTE_THRESHOLD
            and increase / reference >= PRICE_INCREASE_RELATIVE_THRESHOLD
        ):
            alerts.append(
                RecurrenceAlert(
                    alert_type=RecurrenceAlertType.PRICE_INCREASE,
                    title=f"Hausse de prix détectée : {merchant_key}",
                    description=(
                        f"Le dernier prélèvement ({abs(latest.amount)} "
                        f"{latest.currency}) dépasse la référence "
                        f"({reference} {latest.currency})."
                    ),
                    severity="warning",
                    transaction_ids=(latest.id,),
                    contract_id=contract.contract_id,
                )
            )
    alerts.extend(_duplicate_alerts(merchant_key, transactions, contract.contract_id))
    return tuple(alerts)


def _duplicate_alerts(
    merchant_key: str,
    transactions: list[RecurrenceTransaction],
    contract_id: UUID | None,
) -> list[RecurrenceAlert]:
    alerts: list[RecurrenceAlert] = []
    for previous, current in zip(transactions, transactions[1:], strict=False):
        if (
            current.booking_date - previous.booking_date
        ).days > DUPLICATE_DAY_TOLERANCE:
            continue
        if abs(abs(current.amount) - abs(previous.amount)) > AMOUNT_ABSOLUTE_TOLERANCE:
            continue
        alerts.append(
            RecurrenceAlert(
                alert_type=RecurrenceAlertType.POTENTIAL_DUPLICATE,
                title=f"Doublon potentiel : {merchant_key}",
                description=(
                    "Deux prélèvements proches ont un montant similaire "
                    "à quelques jours d'écart."
                ),
                severity="warning",
                transaction_ids=(previous.id, current.id),
                contract_id=contract_id,
            )
        )
    return alerts


def _text_matches_contract(merchant_key: str, contract: _ContractCandidate) -> bool:
    contract_text = f"{contract.provider} {contract.name}".lower()
    tokens = [token for token in merchant_key.split() if len(token) >= 3]
    return bool(tokens) and any(token in contract_text for token in tokens)


def _contract_costs(
    period: RecurrencePeriod,
    transactions: list[RecurrenceTransaction],
) -> tuple[Decimal | None, Decimal | None]:
    average = _average_abs_amount(transactions)
    if period == RecurrencePeriod.MONTHLY:
        return average, (average * Decimal("12")).quantize(Decimal("0.01"))
    if period == RecurrencePeriod.YEARLY:
        return (average / Decimal("12")).quantize(Decimal("0.01")), average
    return (
        (average * Decimal("4.345")).quantize(Decimal("0.01")),
        (average * Decimal("52")).quantize(Decimal("0.01")),
    )


def _payment_frequency(period: RecurrencePeriod) -> str:
    if period == RecurrencePeriod.MONTHLY:
        return ContractPaymentFrequency.MONTHLY.value
    if period == RecurrencePeriod.YEARLY:
        return ContractPaymentFrequency.YEARLY.value
    return ContractPaymentFrequency.OTHER.value


def _average_abs_amount(transactions: list[RecurrenceTransaction]) -> Decimal:
    total = sum((abs(transaction.amount) for transaction in transactions), Decimal("0"))
    return (total / Decimal(len(transactions))).quantize(Decimal("0.01"))


async def get_recurrence_detection_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecurrenceDetectionService:
    """Construit le service de détection des récurrences pour FastAPI."""

    return RecurrenceDetectionService(session)
