"""Service métier pour l'assistant fiscal."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.tax_year_file import TaxYearFile
from app.schemas.tax import TaxYearFileCreate, TaxYearFileUpdate

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
        return _tax_year_file_from_row(result.mappings().one())

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
        return _tax_year_file_from_row(result.mappings().one())

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
    return (
        bindparam(field, type_=JSONB)
        for field in sorted(json_fields)
    )
