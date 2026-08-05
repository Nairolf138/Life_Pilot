"""Classification fiscale déterministe des documents utilisateur."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TAX_DOCUMENT_TAG = "fiscal"
TAX_YEAR_LINK_SOURCE = "document_classification"


@dataclass(frozen=True, slots=True)
class DocumentClassificationInput:
    """Champs documentaires utilisés par la classification fiscale."""

    document_type: str | None
    tags: list[str]
    issuer: str | None
    issue_date: date | None


@dataclass(frozen=True, slots=True)
class FiscalClassificationResult:
    """Résultat de classification fiscale et année de rattachement probable."""

    fiscal_type: str | None
    tags: list[str]
    tax_year: int | None

    @property
    def is_tax_relevant(self) -> bool:
        """Indique si le document doit être rattaché à un dossier fiscal."""

        return self.fiscal_type is not None


class DocumentClassificationService:
    """Classe et rattache les documents fiscaux aux dossiers annuels existants."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def classify_and_link_document(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        document: DocumentClassificationInput,
    ) -> FiscalClassificationResult:
        """Applique la classification fiscale puis lie le document au dossier annuel."""

        classification = classify_tax_document(document)
        if not classification.is_tax_relevant:
            return classification

        await self._session.execute(
            text(
                """
                UPDATE documents
                SET document_type = :document_type,
                    tags = :tags,
                    updated_at = now()
                WHERE id = :document_id
                  AND user_id = :user_id
                """
            ),
            {
                "document_id": document_id,
                "user_id": user_id,
                "document_type": classification.fiscal_type,
                "tags": classification.tags,
            },
        )
        if classification.tax_year is not None:
            await self._link_to_tax_year_file(
                user_id=user_id,
                document_id=document_id,
                tax_year=classification.tax_year,
                fiscal_type=classification.fiscal_type,
            )
        return classification

    async def _link_to_tax_year_file(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        tax_year: int,
        fiscal_type: str,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO tax_year_file_documents (
                    tax_year_file_id, document_id, fiscal_document_type, source
                )
                SELECT tyf.id, :document_id, :fiscal_type, :source
                FROM tax_year_files tyf
                WHERE tyf.user_id = :user_id
                  AND tyf.tax_year = :tax_year
                ON CONFLICT (tax_year_file_id, document_id) DO UPDATE
                SET fiscal_document_type = EXCLUDED.fiscal_document_type,
                    source = EXCLUDED.source,
                    updated_at = now()
                """
            ),
            {
                "document_id": document_id,
                "fiscal_type": fiscal_type,
                "source": TAX_YEAR_LINK_SOURCE,
                "tax_year": tax_year,
                "user_id": user_id,
            },
        )


def classify_tax_document(
    document: DocumentClassificationInput,
) -> FiscalClassificationResult:
    """Repère les principaux types de documents utiles à un dossier fiscal."""

    tokens = _document_tokens(document)
    fiscal_type = _detect_fiscal_type(tokens)
    tags = list(document.tags or [])
    if fiscal_type:
        tags = list(dict.fromkeys([*tags, TAX_DOCUMENT_TAG]))
    if fiscal_type:
        tags.append(f"tax:{fiscal_type}")
        tags = list(dict.fromkeys(tags))
    return FiscalClassificationResult(
        fiscal_type=fiscal_type,
        tags=tags,
        tax_year=(
            document.issue_date.year if fiscal_type and document.issue_date else None
        ),
    )


def _document_tokens(document: DocumentClassificationInput) -> str:
    values = [
        document.document_type or "",
        document.issuer or "",
        *(document.tags or []),
    ]
    return " ".join(values).casefold()


def _detect_fiscal_type(tokens: str) -> str | None:
    if "binance" in tokens:
        return "binance_export"
    if "etoro" in tokens or "e toro" in tokens:
        return "etoro_export"
    if any(
        term in tokens for term in ("prérempl", "prerempl", "pre-filled", "prefilled")
    ):
        return "manual_prefilled_declaration"
    if "avis" in tokens and any(term in tokens for term in ("impôt", "impot", "tax")):
        return "tax_notice"
    if any(
        term in tokens
        for term in (
            "déclaration précédente",
            "declaration precedente",
            "previous declaration",
        )
    ):
        return "previous_tax_declaration"
    if any(term in tokens for term in ("déclaration", "declaration")) and any(
        term in tokens for term in ("impôt", "impot", "revenus", "tax")
    ):
        return "previous_tax_declaration"
    if any(
        term in tokens
        for term in (
            "ifu",
            "imprimé fiscal unique",
            "imprime fiscal unique",
            "document bancaire fiscal",
        )
    ):
        return "bank_tax_document"
    if any(
        term in tokens
        for term in (
            "bulletin",
            "fiche de paie",
            "justificatif de revenu",
            "salary",
            "payslip",
        )
    ):
        return "income_proof"
    return None
