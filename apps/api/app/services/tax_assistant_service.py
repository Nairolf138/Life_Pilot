"""Service métier pour l'assistant fiscal."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.tax_year_file import TaxYearFile
from app.schemas.tax import TaxChecklistExport, TaxYearFileCreate, TaxYearFileUpdate

TAX_YEAR_FILE_COLUMNS = """
    id, user_id, tax_year, income_year, status, summary_markdown, checklist_json,
    known_amounts_json, manual_prefilled_data_json, created_at, updated_at
"""


class TaxAssistantService:
    """Orchestre la préparation des dossiers fiscaux annuels."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tax_year_files(self, user_id: UUID) -> list[TaxYearFile]:
        """Liste les dossiers fiscaux de l'utilisateur courant."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {TAX_YEAR_FILE_COLUMNS}
                FROM tax_year_files
                WHERE user_id = :user_id
                ORDER BY tax_year DESC, created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_tax_year_file_from_row(row) for row in result.mappings().all()]

    async def get_tax_year_file(
        self,
        user_id: UUID,
        tax_year_file_id: UUID,
    ) -> TaxYearFile:
        """Retourne un dossier fiscal appartenant à l'utilisateur courant."""

        row = await self._fetch_tax_year_file(user_id, tax_year_file_id)
        if row is None:
            raise_tax_year_file_not_found()
        return _tax_year_file_from_row(row)

    async def create_tax_year_file(
        self,
        user_id: UUID,
        payload: TaxYearFileCreate,
    ) -> TaxYearFile:
        """Crée un dossier fiscal pour l'utilisateur courant."""

        values = payload.model_dump(mode="json")
        try:
            result = await self._session.execute(
                text(
                    f"""
                    INSERT INTO tax_year_files (
                        user_id, tax_year, income_year, status, summary_markdown,
                        checklist_json, known_amounts_json,
                        manual_prefilled_data_json
                    ) VALUES (
                        :user_id, :tax_year, :income_year, :status,
                        :summary_markdown, :checklist_json, :known_amounts_json,
                        :manual_prefilled_data_json
                    )
                    RETURNING {TAX_YEAR_FILE_COLUMNS}
                    """
                ).bindparams(*_json_bindparams()),
                {"user_id": user_id, **values},
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un dossier fiscal existe déjà pour cette année.",
            ) from exc
        tax_year_file = _tax_year_file_from_row(result.mappings().one())
        await self.refresh_checklist(user_id, tax_year_file.id)
        return await self.get_tax_year_file(user_id, tax_year_file.id)

    async def update_tax_year_file(
        self,
        user_id: UUID,
        tax_year_file_id: UUID,
        payload: TaxYearFileUpdate,
    ) -> TaxYearFile:
        """Met à jour partiellement un dossier fiscal de l'utilisateur courant."""

        if await self._fetch_tax_year_file(user_id, tax_year_file_id) is None:
            raise_tax_year_file_not_found()

        changes = payload.model_dump(exclude_unset=True, mode="json")
        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        update_query = text(
            f"""
            UPDATE tax_year_files
            SET {assignments},
                updated_at = now()
            WHERE id = :tax_year_file_id
              AND user_id = :user_id
            RETURNING {TAX_YEAR_FILE_COLUMNS}
            """
        )
        json_params = _json_bindparams(changes)
        if json_params:
            update_query = update_query.bindparams(*json_params)
        try:
            result = await self._session.execute(
                update_query,
                {"tax_year_file_id": tax_year_file_id, "user_id": user_id, **changes},
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un dossier fiscal existe déjà pour cette année.",
            ) from exc
        tax_year_file = _tax_year_file_from_row(result.mappings().one())
        if {
            "tax_year",
            "income_year",
            "known_amounts_json",
            "manual_prefilled_data_json",
        } & set(changes):
            await self.refresh_checklist(user_id, tax_year_file.id)
            return await self.get_tax_year_file(user_id, tax_year_file.id)
        return tax_year_file

    async def refresh_checklist(
        self,
        user_id: UUID,
        tax_year_file_id: UUID,
    ) -> TaxYearFile:
        """Reconstruit la checklist fiscale JSON et son export Markdown."""

        row = await self._fetch_tax_year_file(user_id, tax_year_file_id)
        if row is None:
            raise_tax_year_file_not_found()

        checklist = await self._build_checklist(row)
        markdown = render_checklist_markdown(checklist)
        result = await self._session.execute(
            text(
                f"""
                UPDATE tax_year_files
                SET checklist_json = :checklist_json,
                    summary_markdown = :summary_markdown,
                    updated_at = now()
                WHERE id = :tax_year_file_id
                  AND user_id = :user_id
                RETURNING {TAX_YEAR_FILE_COLUMNS}
                """
            ).bindparams(bindparam("checklist_json", type_=JSONB)),
            {
                "checklist_json": checklist,
                "summary_markdown": markdown,
                "tax_year_file_id": tax_year_file_id,
                "user_id": user_id,
            },
        )
        await self._session.commit()
        return _tax_year_file_from_row(result.mappings().one())

    async def export_checklist_markdown(
        self,
        user_id: UUID,
        tax_year_file_id: UUID,
    ) -> TaxChecklistExport:
        """Retourne l'export Markdown; le PDF sera ajouté via ce contrat."""

        tax_year_file = await self.get_tax_year_file(user_id, tax_year_file_id)
        checklist = tax_year_file.checklist_json or await self._build_checklist_row(
            tax_year_file
        )
        markdown = tax_year_file.summary_markdown or render_checklist_markdown(
            checklist
        )
        return TaxChecklistExport(
            format="markdown",
            content=markdown,
            filename=f"checklist-fiscale-{tax_year_file.tax_year}.md",
            pdf_export_available=False,
        )

    async def _build_checklist_row(self, tax_year_file: TaxYearFile) -> dict[str, Any]:
        return await self._build_checklist(tax_year_file)

    async def _build_checklist(self, row) -> dict[str, Any]:
        income_year = row.income_year
        period_start = date(income_year, 1, 1)
        period_end = date(income_year, 12, 31)
        documents = await self._fetch_tax_documents(row.id)
        incomes = await self._fetch_income_transactions(
            row.user_id, period_start, period_end
        )
        bank_interests = await self._fetch_matching_transactions(
            row.user_id, period_start, period_end, ("intérêt", "interet", "interest")
        )
        donations = await self._fetch_matching_transactions(
            row.user_id,
            period_start,
            period_end,
            ("don", "donation", "association", "frais réel", "frais reel"),
        )
        crypto_assets = await self._fetch_assets(row.user_id, "crypto")
        broker_assets = await self._fetch_broker_assets(row.user_id)
        found_types = {doc["fiscal_document_type"] for doc in documents}
        required = {
            "tax_notice",
            "previous_tax_declaration",
            "bank_tax_document",
            "income_proof",
        }
        missing = sorted(required - found_types)
        checklist = {
            "tax_year": row.tax_year,
            "income_year": income_year,
            "pdf_export_available": False,
            "pdf_export_note": "Export PDF prévu ultérieurement à partir du Markdown.",
            "known_income_to_verify": _items(incomes),
            "found_tax_documents": documents,
            "probable_missing_documents": [
                {"type": item, "status": "missing_probable"} for item in missing
            ],
            "bank_interests_to_verify": _items(bank_interests),
            "crypto_operations_to_analyze": crypto_assets,
            "broker_operations_to_analyze": broker_assets,
            "address_to_confirm": row.manual_prefilled_data_json.get("address")
            if row.manual_prefilled_data_json
            else None,
            "donations_or_real_expenses_to_confirm_manually": _items(donations),
            "human_intervention_points": _human_points(
                missing, bank_interests, crypto_assets, broker_assets, donations
            ),
        }
        return _jsonable(checklist)

    async def _fetch_tax_year_file(self, user_id: UUID, tax_year_file_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {TAX_YEAR_FILE_COLUMNS}
                FROM tax_year_files
                WHERE id = :tax_year_file_id
                  AND user_id = :user_id
                """
            ),
            {"tax_year_file_id": tax_year_file_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def _fetch_tax_documents(
        self, tax_year_file_id: UUID
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT d.id, d.title, d.issuer, d.issue_date, d.amount, d.currency,
                       tyfd.fiscal_document_type
                FROM tax_year_file_documents tyfd
                JOIN documents d ON d.id = tyfd.document_id
                WHERE tyfd.tax_year_file_id = :tax_year_file_id
                ORDER BY d.issue_date DESC NULLS LAST, d.created_at DESC
                """
            ),
            {"tax_year_file_id": tax_year_file_id},
        )
        return [_jsonable(dict(row)) for row in result.mappings().all()]

    async def _fetch_income_transactions(self, user_id: UUID, start: date, end: date):
        result = await self._session.execute(
            text(
                """
                SELECT id, booking_date, label_clean, label_raw, amount, currency
                FROM transactions
                WHERE user_id = :user_id AND booking_date BETWEEN :start AND :end
                  AND amount > 0 AND is_internal_transfer = false
                ORDER BY amount DESC LIMIT 25
                """
            ),
            {"user_id": user_id, "start": start, "end": end},
        )
        return result.mappings().all()

    async def _fetch_matching_transactions(
        self, user_id: UUID, start: date, end: date, terms: tuple[str, ...]
    ):
        pattern = "|".join(terms)
        result = await self._session.execute(
            text(
                """
                SELECT id, booking_date, label_clean, label_raw, amount, currency
                FROM transactions
                WHERE user_id = :user_id AND booking_date BETWEEN :start AND :end
                  AND concat_ws(
                      ' ', label_clean, label_raw, merchant_name, notes
                  ) ~* :pattern
                ORDER BY booking_date DESC LIMIT 50
                """
            ),
            {"user_id": user_id, "start": start, "end": end, "pattern": pattern},
        )
        return result.mappings().all()

    async def _fetch_assets(
        self, user_id: UUID, asset_type: str
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, provider, asset_type, symbol, name, quantity,
                       current_value, currency
                FROM assets WHERE user_id = :user_id AND asset_type = :asset_type
                ORDER BY provider, name LIMIT 50
                """
            ),
            {"user_id": user_id, "asset_type": asset_type},
        )
        return [_jsonable(dict(row)) for row in result.mappings().all()]

    async def _fetch_broker_assets(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT id, provider, asset_type, symbol, name, quantity,
                       current_value, currency
                FROM assets
                WHERE user_id = :user_id
                  AND (
                      asset_type IN ('stock', 'etf', 'fund', 'bond')
                      OR provider ~* 'etoro|broker|courtier'
                  )
                ORDER BY provider, name LIMIT 50
                """
            ),
            {"user_id": user_id},
        )
        return [_jsonable(dict(row)) for row in result.mappings().all()]


async def get_tax_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaxAssistantService:
    """Construit le service d'assistant fiscal pour FastAPI."""

    return TaxAssistantService(session)


def raise_tax_year_file_not_found() -> None:
    """Retourne une erreur uniforme pour un dossier fiscal absent."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Dossier fiscal introuvable.",
    )


def _tax_year_file_from_row(row) -> TaxYearFile:
    return TaxYearFile(
        id=row.id,
        user_id=row.user_id,
        tax_year=row.tax_year,
        income_year=row.income_year,
        status=row.status,
        summary_markdown=row.summary_markdown,
        checklist_json=row.checklist_json,
        known_amounts_json=row.known_amounts_json,
        manual_prefilled_data_json=row.manual_prefilled_data_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _json_bindparams(fields: object = None):
    json_fields = {
        "checklist_json",
        "known_amounts_json",
        "manual_prefilled_data_json",
    }
    if fields is not None:
        json_fields &= set(fields)
    return (bindparam(field, type_=JSONB) for field in sorted(json_fields))


def _items(rows) -> list[dict[str, Any]]:
    return [
        _jsonable(
            {
                "id": row.id,
                "date": row.booking_date,
                "label": row.label_clean or row.label_raw,
                "amount": row.amount,
                "currency": row.currency,
            }
        )
        for row in rows
    ]


def _human_points(
    missing, bank_interests, crypto_assets, broker_assets, donations
) -> list[str]:
    points = [
        "Confirmer l'adresse fiscale et la situation familiale avant déclaration.",
        "Valider manuellement les dons, frais réels et justificatifs associés.",
    ]
    if missing:
        points.append(
            "Retrouver ou importer les documents fiscaux probablement manquants."
        )
    if bank_interests:
        points.append(
            "Comparer les intérêts bancaires détectés avec les IFU bancaires."
        )
    if crypto_assets:
        points.append(
            "Analyser les opérations crypto et plus-values imposables éventuelles."
        )
    if broker_assets:
        points.append(
            "Analyser les opérations broker, dividendes et plus-values mobilières."
        )
    if donations:
        points.append(
            "Vérifier l'éligibilité fiscale des dons et frais réels détectés."
        )
    return points


def render_checklist_markdown(checklist: dict[str, Any]) -> str:
    title = (
        f"# Checklist fiscale {checklist.get('tax_year')} "
        f"(revenus {checklist.get('income_year')})"
    )
    sections = [
        ("Salaires ou revenus connus à vérifier", "known_income_to_verify"),
        ("Documents fiscaux trouvés", "found_tax_documents"),
        ("Documents manquants probables", "probable_missing_documents"),
        ("Intérêts bancaires à vérifier", "bank_interests_to_verify"),
        ("Opérations crypto à analyser", "crypto_operations_to_analyze"),
        ("Opérations broker à analyser", "broker_operations_to_analyze"),
        (
            "Dons ou frais réels à confirmer manuellement",
            "donations_or_real_expenses_to_confirm_manually",
        ),
        ("Points nécessitant intervention humaine", "human_intervention_points"),
    ]
    default_address = "Adresse fiscale à confirmer manuellement."
    lines = [
        title,
        "",
        f"> {checklist.get('pdf_export_note', 'Export PDF prévu ultérieurement.')} ",
        "",
        "## Adresse à confirmer",
        "",
        f"- {checklist.get('address_to_confirm') or default_address}",
        "",
    ]
    for heading, key in sections:
        lines.extend([f"## {heading}", ""])
        values = checklist.get(key) or []
        if not values:
            lines.append("- Aucun élément détecté automatiquement.")
        else:
            for value in values:
                lines.append(f"- {_markdown_item(value)}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _markdown_item(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        label = (
            value.get("label")
            or value.get("title")
            or value.get("name")
            or value.get("type")
            or value.get("symbol")
            or value.get("id")
        )
        amount = value.get("amount") or value.get("current_value")
        currency = value.get("currency")
        date_value = value.get("date") or value.get("issue_date")
        parts = [str(part) for part in (date_value, label) if part]
        if amount is not None:
            parts.append(f"{amount} {currency or ''}".strip())
        return " — ".join(parts) or str(value)
    return str(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value
