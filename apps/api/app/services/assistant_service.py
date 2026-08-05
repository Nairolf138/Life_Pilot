"""Service métier pour l'assistant transversal Life Pilot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

AssistantDomain = Literal[
    "transactions",
    "documents",
    "contrats",
    "rappels",
    "vehicules",
    "actifs",
    "dossier_fiscal",
]
AssistantCategory = Literal[
    "fait_verifie",
    "estimation",
    "hypothese",
    "action_recommandee",
    "action_requise",
]
SensitiveActionType = Literal["create_reminder"]

SUPPORTED_DOMAINS: tuple[AssistantDomain, ...] = (
    "transactions",
    "documents",
    "contrats",
    "rappels",
    "vehicules",
    "actifs",
    "dossier_fiscal",
)


class AssistantQueryRequest(BaseModel):
    """Question posée à l'assistant transversal."""

    question: str = Field(min_length=1, max_length=2_000)
    domains: list[AssistantDomain] | None = Field(
        default=None,
        description=(
            "Domaines à interroger. Tous les domaines sont interrogés par défaut."
        ),
    )


class AssistantInsight(BaseModel):
    """Élément de réponse typé selon son niveau de certitude ou d'action."""

    category: AssistantCategory
    domain: AssistantDomain
    title: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


class AssistantQueryResponse(BaseModel):
    """Réponse structurée de l'assistant."""

    question: str
    facts_verified: list[AssistantInsight] = Field(default_factory=list)
    estimations: list[AssistantInsight] = Field(default_factory=list)
    hypotheses: list[AssistantInsight] = Field(default_factory=list)
    recommended_actions: list[AssistantInsight] = Field(default_factory=list)
    required_actions: list[AssistantInsight] = Field(default_factory=list)


class AssistantActionPayload(BaseModel):
    """Action sensible demandée à l'assistant."""

    action_type: SensitiveActionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=1_000)


class AssistantActionPreviewRequest(BaseModel):
    """Demande de prévisualisation d'une action sensible."""

    action: AssistantActionPayload


class AssistantActionPreviewResponse(BaseModel):
    """Prévisualisation obligatoire avant confirmation."""

    preview_token: str
    action_type: SensitiveActionType
    summary: str
    impacts: list[str]
    required_confirmation: bool = True
    expires_hint: str = (
        "Le jeton est déterministe pour cette action et cet utilisateur."
    )


class AssistantActionConfirmRequest(BaseModel):
    """Confirmation explicite d'une action prévisualisée."""

    preview_token: str = Field(min_length=64, max_length=64)
    action: AssistantActionPayload
    confirm: bool = Field(description="Doit être true pour exécuter l'action sensible.")


class AssistantActionConfirmResponse(BaseModel):
    """Résultat d'exécution d'une action confirmée."""

    status: Literal["executed"]
    action_type: SensitiveActionType
    result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DomainSnapshot:
    """Synthèse SQL d'un domaine interrogeable par l'assistant."""

    domain: AssistantDomain
    total_count: int
    recent_items: list[dict[str, Any]]
    metrics: dict[str, Any]


class AssistantService:
    """Interroge les données utilisateur et encadre les actions sensibles."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(
        self,
        user_id: UUID,
        payload: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        """Répond à une question avec une réponse structurée par certitude."""

        domains = payload.domains or list(SUPPORTED_DOMAINS)
        snapshots = [await self._snapshot_domain(user_id, domain) for domain in domains]

        response = AssistantQueryResponse(question=payload.question)
        for snapshot in snapshots:
            response.facts_verified.append(_verified_fact_from_snapshot(snapshot))
            if snapshot.domain in {"transactions", "contrats", "actifs"}:
                estimation = _estimation_from_snapshot(snapshot)
                if estimation is not None:
                    response.estimations.append(estimation)
            hypothesis = _hypothesis_from_question(payload.question, snapshot)
            if hypothesis is not None:
                response.hypotheses.append(hypothesis)
            response.recommended_actions.extend(_recommended_actions(snapshot))
            response.required_actions.extend(_required_actions(snapshot))
        return response

    async def preview_action(
        self,
        user_id: UUID,
        payload: AssistantActionPreviewRequest,
    ) -> AssistantActionPreviewResponse:
        """Prévisualise une action sensible sans la modifier en base."""

        summary, impacts = _describe_action(payload.action)
        return AssistantActionPreviewResponse(
            preview_token=_preview_token(user_id, payload.action),
            action_type=payload.action.action_type,
            summary=summary,
            impacts=impacts,
        )

    async def confirm_action(
        self,
        user_id: UUID,
        payload: AssistantActionConfirmRequest,
    ) -> AssistantActionConfirmResponse:
        """Exécute une action sensible uniquement après prévisualisation valide."""

        if not payload.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La confirmation explicite est requise.",
            )
        expected_token = _preview_token(user_id, payload.action)
        if payload.preview_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Le jeton de prévisualisation ne correspond pas à l'action.",
            )
        if payload.action.action_type == "create_reminder":
            result = await self._create_reminder(user_id, payload.action.parameters)
        else:  # pragma: no cover - garde défensive pour l'évolution du Literal.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action non supportée."
            )
        await self._session.commit()
        return AssistantActionConfirmResponse(
            status="executed",
            action_type=payload.action.action_type,
            result=result,
        )

    async def _snapshot_domain(
        self, user_id: UUID, domain: AssistantDomain
    ) -> DomainSnapshot:
        if domain == "transactions":
            return await self._transactions_snapshot(user_id)
        if domain == "documents":
            return await self._simple_snapshot(
                user_id,
                "documents",
                "created_at",
                "title, document_type, amount, due_date",
            )
        if domain == "contrats":
            return await self._simple_snapshot(
                user_id,
                "contracts",
                "renewal_date NULLS LAST, created_at",
                "name, contract_type, monthly_cost, yearly_cost, renewal_date, status",
            )
        if domain == "rappels":
            return await self._simple_snapshot(
                user_id, "reminders", "due_date", "title, due_date, severity, status"
            )
        if domain == "vehicules":
            return await self._simple_snapshot(
                user_id,
                "vehicles",
                "created_at",
                "brand, model, mileage_current, technical_inspection_due_date",
            )
        if domain == "actifs":
            return await self._simple_snapshot(
                user_id,
                "assets",
                "updated_at",
                "name, asset_type, symbol, current_value, currency",
            )
        return await self._simple_snapshot(
            user_id,
            "tax_year_files",
            "tax_year DESC",
            "tax_year, income_year, status, known_amounts_json",
        )

    async def _transactions_snapshot(self, user_id: UUID) -> DomainSnapshot:
        totals = await self._session.execute(
            text(
                """
                SELECT count(*) AS total_count,
                       COALESCE(sum(amount), 0) AS net_amount,
                       COALESCE(
                           sum(CASE WHEN amount < 0 THEN amount ELSE 0 END),
                           0
                       ) AS expenses,
                       COALESCE(
                           sum(CASE WHEN amount > 0 THEN amount ELSE 0 END),
                           0
                       ) AS income
                FROM transactions
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        row = totals.mappings().one()
        recent = await self._session.execute(
            text(
                """
                SELECT booking_date, label_raw, merchant_name, amount, currency
                FROM transactions
                WHERE user_id = :user_id
                ORDER BY booking_date DESC, created_at DESC
                LIMIT 5
                """
            ),
            {"user_id": user_id},
        )
        return DomainSnapshot(
            domain="transactions",
            total_count=int(row["total_count"]),
            recent_items=[_jsonable(dict(item)) for item in recent.mappings().all()],
            metrics={
                "net_amount": row["net_amount"],
                "expenses": row["expenses"],
                "income": row["income"],
            },
        )

    async def _simple_snapshot(
        self, user_id: UUID, table: str, order_by: str, columns: str
    ) -> DomainSnapshot:
        count = await self._session.execute(
            text(f"SELECT count(*) FROM {table} WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        recent = await self._session.execute(
            text(
                f"SELECT {columns} FROM {table} "
                f"WHERE user_id = :user_id ORDER BY {order_by} LIMIT 5"
            ),
            {"user_id": user_id},
        )
        return DomainSnapshot(
            domain=_domain_from_table(table),
            total_count=int(count.scalar_one()),
            recent_items=[_jsonable(dict(item)) for item in recent.mappings().all()],
            metrics={},
        )

    async def _create_reminder(
        self, user_id: UUID, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        title = str(parameters.get("title") or "Action assistant")
        due_date = parameters.get("due_date")
        if not due_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="due_date est requis pour créer un rappel.",
            )
        result = await self._session.execute(
            text(
                """
                INSERT INTO reminders (
                    user_id, title, description, due_date,
                    reminder_date, severity, status
                )
                VALUES (
                    :user_id, :title, :description, :due_date,
                    :reminder_date, :severity, 'pending'
                )
                RETURNING id, title, due_date, severity, status
                """
            ),
            {
                "user_id": user_id,
                "title": title,
                "description": parameters.get("description"),
                "due_date": due_date,
                "reminder_date": parameters.get("reminder_date"),
                "severity": parameters.get("severity", "info"),
            },
        )
        return _jsonable(dict(result.mappings().one()))


def _verified_fact_from_snapshot(snapshot: DomainSnapshot) -> AssistantInsight:
    return AssistantInsight(
        category="fait_verifie",
        domain=snapshot.domain,
        title=f"{snapshot.total_count} élément(s) dans {snapshot.domain}",
        detail="Comptage vérifié depuis la base utilisateur.",
        data={
            "recent_items": snapshot.recent_items,
            "metrics": _jsonable(snapshot.metrics),
        },
    )


def _estimation_from_snapshot(snapshot: DomainSnapshot) -> AssistantInsight | None:
    if not snapshot.metrics:
        return None
    return AssistantInsight(
        category="estimation",
        domain=snapshot.domain,
        title=f"Synthèse estimée pour {snapshot.domain}",
        detail=(
            "Montants agrégés à partir des données importées; ils peuvent être "
            "incomplets si des synchronisations manquent."
        ),
        data=_jsonable(snapshot.metrics),
    )


def _hypothesis_from_question(
    question: str, snapshot: DomainSnapshot
) -> AssistantInsight | None:
    terms = {
        term.lower().strip(" ?,.;:!") for term in question.split() if len(term) >= 4
    }
    if not terms or not snapshot.recent_items:
        return None
    matching_items = [
        item
        for item in snapshot.recent_items
        if any(term in json.dumps(item, default=str).lower() for term in terms)
    ]
    if not matching_items:
        return None
    return AssistantInsight(
        category="hypothese",
        domain=snapshot.domain,
        title="Correspondance possible avec la question",
        detail=(
            "Des éléments récents contiennent des termes proches; "
            "une vérification humaine peut être nécessaire."
        ),
        data={"matching_items": matching_items},
    )


def _recommended_actions(snapshot: DomainSnapshot) -> list[AssistantInsight]:
    if snapshot.domain == "documents" and snapshot.total_count == 0:
        return [
            AssistantInsight(
                category="action_recommandee",
                domain=snapshot.domain,
                title="Importer des documents",
                detail=(
                    "Ajoutez vos factures, justificatifs et avis fiscaux "
                    "pour enrichir les réponses."
                ),
            )
        ]
    return []


def _required_actions(snapshot: DomainSnapshot) -> list[AssistantInsight]:
    if snapshot.domain == "rappels":
        overdue = [
            item
            for item in snapshot.recent_items
            if item.get("status") == "pending"
            and item.get("due_date")
            and str(item["due_date"]) < date.today().isoformat()
        ]
        if overdue:
            return [
                AssistantInsight(
                    category="action_requise",
                    domain=snapshot.domain,
                    title="Rappels en retard",
                    detail="Des rappels échus sont encore en attente.",
                    data={"overdue": overdue},
                )
            ]
    return []


def _describe_action(action: AssistantActionPayload) -> tuple[str, list[str]]:
    if action.action_type == "create_reminder":
        return (
            f"Créer le rappel '{action.parameters.get('title', 'Action assistant')}'.",
            [
                "Ajout d'une ligne dans reminders.",
                "Aucune notification externe n'est envoyée par cet endpoint.",
            ],
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Action non supportée."
    )


def _preview_token(user_id: UUID, action: AssistantActionPayload) -> str:
    settings = get_settings()
    payload = json.dumps(
        action.model_dump(), sort_keys=True, default=str, separators=(",", ":")
    )
    return sha256(f"{settings.secret_key}:{user_id}:{payload}".encode()).hexdigest()


def _domain_from_table(table: str) -> AssistantDomain:
    return {
        "documents": "documents",
        "contracts": "contrats",
        "reminders": "rappels",
        "vehicles": "vehicules",
        "assets": "actifs",
        "tax_year_files": "dossier_fiscal",
    }[table]


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def get_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AssistantService:
    """Construit le service assistant pour l'injection FastAPI."""

    return AssistantService(session)
