"""Service métier pour les documents administratifs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.document import (
    DocumentExtractRequest,
    DocumentTransactionLink,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.document_extraction_service import DocumentExtractionService
from app.services.storage_service import (
    DownloadedFile,
    StorageService,
    get_storage_service,
)


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Document administratif retourné par le service."""

    id: UUID
    provider: str | None
    document_type: str
    title: str
    issuer: str | None
    issue_date: date | None
    due_date: date | None
    amount: Decimal | None
    currency: str
    file_path: str
    file_hash: str
    mime_type: str | None
    extracted_text: str | None
    extraction_status: str | None
    confidence_score: Decimal | None
    linked_transaction_id: UUID | None
    source_email_id: UUID | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class DocumentService:
    """Orchestre les opérations de lecture et d'écriture des documents."""

    def __init__(self, session: AsyncSession, storage_service: StorageService) -> None:
        self._session = session
        self._storage_service = storage_service

    async def list_documents(self, user_id: UUID) -> list[DocumentRecord]:
        """Liste les documents de l'utilisateur courant."""

        result = await self._session.execute(
            text(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [_document_from_row(row) for row in result.mappings().all()]

    async def get_document(self, user_id: UUID, document_id: UUID) -> DocumentRecord:
        """Retourne un document appartenant à l'utilisateur courant."""

        row = await self._fetch_document(user_id, document_id)
        if row is None:
            raise_document_not_found()
        return _document_from_row(row)

    async def upload_document(
        self,
        user_id: UUID,
        *,
        file: UploadFile,
        document_type: str,
        title: str | None = None,
    ) -> DocumentUploadResponse:
        """Stocke un fichier et crée le document, en évitant les doublons par hash."""

        content = await file.read()
        file_hash = self._storage_service.calculate_file_hash(content)
        existing = await self._fetch_document_by_hash(user_id, file_hash)
        if existing is not None:
            return DocumentUploadResponse(
                document=_document_from_row(existing), duplicate=True
            )

        stored_file = self._storage_service.upload_document_bytes(
            user_id=user_id,
            document_type=document_type,
            filename=file.filename,
            content=content,
            mime_type=file.content_type,
        )

        result = await self._session.execute(
            text(
                f"""
                INSERT INTO documents (
                    user_id, document_type, title, file_path, file_hash,
                    mime_type, extraction_status
                ) VALUES (
                    :user_id, :document_type, :title, :file_path, :file_hash,
                    :mime_type, 'pending'
                )
                RETURNING {DOCUMENT_COLUMNS}
                """
            ),
            {
                "user_id": user_id,
                "document_type": document_type,
                "title": title or (file.filename or "document"),
                "file_path": stored_file.file_path,
                "file_hash": stored_file.file_hash,
                "mime_type": stored_file.mime_type,
            },
        )
        await self._session.commit()
        return DocumentUploadResponse(
            document=_document_from_row(result.mappings().one()), duplicate=False
        )

    async def download_document(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> DownloadedFile:
        """Retourne le contenu après contrôle d'appartenance utilisateur."""

        document = await self.get_document(user_id, document_id)
        return self._storage_service.download_document_file(
            user_id=user_id,
            document_type=document.document_type,
            file_path=document.file_path,
            file_hash=document.file_hash,
            mime_type=document.mime_type,
        )

    async def extract_document(
        self,
        user_id: UUID,
        document_id: UUID,
        payload: DocumentExtractRequest,
    ) -> DocumentRecord:
        """Enregistre ou lance l'extraction texte native d'un document PDF."""

        changes = payload.model_dump(exclude_unset=True)
        if changes:
            return await self._update_document_fields(user_id, document_id, changes)

        document = await self.get_document(user_id, document_id)
        downloaded_file = self._storage_service.download_document_file(
            user_id=user_id,
            document_type=document.document_type,
            file_path=document.file_path,
            file_hash=document.file_hash,
            mime_type=document.mime_type,
        )
        extraction = DocumentExtractionService().extract_document(
            downloaded_file.content,
            mime_type=downloaded_file.mime_type,
            filename=downloaded_file.file_path,
        )
        extraction_changes = {
            "extracted_text": extraction.extracted_text,
            "extraction_status": extraction.extraction_status,
            "confidence_score": extraction.confidence_score,
        }
        if extraction.issuer is not None:
            extraction_changes["issuer"] = extraction.issuer
        if extraction.issue_date is not None:
            extraction_changes["issue_date"] = extraction.issue_date
        if extraction.amount is not None:
            extraction_changes["amount"] = extraction.amount
        if extraction.currency is not None:
            extraction_changes["currency"] = extraction.currency
        return await self._update_document_fields(
            user_id, document_id, extraction_changes
        )

    async def link_transaction(
        self,
        user_id: UUID,
        document_id: UUID,
        payload: DocumentTransactionLink,
    ) -> DocumentRecord:
        """Rattache un document utilisateur à une transaction utilisateur."""

        await self._ensure_transaction_belongs_to_user(user_id, payload.transaction_id)
        document = await self._update_document_fields(
            user_id,
            document_id,
            {"linked_transaction_id": payload.transaction_id},
            commit=False,
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
                "transaction_id": payload.transaction_id,
                "user_id": user_id,
            },
        )
        await self._session.commit()
        return document

    async def update_document(
        self,
        user_id: UUID,
        document_id: UUID,
        payload: DocumentUpdate,
    ) -> DocumentRecord:
        """Met à jour les métadonnées modifiables d'un document."""

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return await self.get_document(user_id, document_id)
        return await self._update_document_fields(user_id, document_id, changes)

    async def _update_document_fields(
        self,
        user_id: UUID,
        document_id: UUID,
        changes: dict[str, object],
        *,
        commit: bool = True,
    ) -> DocumentRecord:
        assignments = ",\n                    ".join(
            f"{field} = :{field}" for field in changes
        )
        result = await self._session.execute(
            text(
                f"""
                UPDATE documents
                SET {assignments},
                    updated_at = now()
                WHERE id = :document_id
                  AND user_id = :user_id
                RETURNING {DOCUMENT_COLUMNS}
                """
            ),
            {"document_id": document_id, "user_id": user_id, **changes},
        )
        row = result.mappings().first()
        if row is None:
            raise_document_not_found()
        if commit:
            await self._session.commit()
        return _document_from_row(row)

    async def _fetch_document(self, user_id: UUID, document_id: UUID):
        result = await self._session.execute(
            text(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                WHERE id = :document_id
                  AND user_id = :user_id
                """
            ),
            {"document_id": document_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def _fetch_document_by_hash(self, user_id: UUID, file_hash: str):
        result = await self._session.execute(
            text(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                WHERE user_id = :user_id
                  AND file_hash = :file_hash
                """
            ),
            {"user_id": user_id, "file_hash": file_hash},
        )
        return result.mappings().first()

    async def _ensure_transaction_belongs_to_user(
        self,
        user_id: UUID,
        transaction_id: UUID,
    ) -> None:
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM transactions
                WHERE id = :transaction_id
                  AND user_id = :user_id
                """
            ),
            {"transaction_id": transaction_id, "user_id": user_id},
        )
        if result.first() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction introuvable.")


DOCUMENT_COLUMNS = """
    id, provider, document_type, title, issuer, issue_date, due_date, amount,
    currency, file_path, file_hash, mime_type, extracted_text, extraction_status,
    confidence_score, linked_transaction_id, source_email_id, tags, created_at,
    updated_at
"""


async def get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> DocumentService:
    """Construit le service de documents pour FastAPI."""

    return DocumentService(session, storage_service)


def raise_document_not_found() -> None:
    """Retourne une erreur uniforme pour un document absent ou inaccessible."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document introuvable.",
    )


def _document_from_row(row) -> DocumentRecord:
    return DocumentRecord(
        id=row.id,
        provider=row.provider,
        document_type=row.document_type,
        title=row.title,
        issuer=row.issuer,
        issue_date=row.issue_date,
        due_date=row.due_date,
        amount=row.amount,
        currency=row.currency,
        file_path=row.file_path,
        file_hash=row.file_hash,
        mime_type=row.mime_type,
        extracted_text=row.extracted_text,
        extraction_status=row.extraction_status,
        confidence_score=row.confidence_score,
        linked_transaction_id=row.linked_transaction_id,
        source_email_id=row.source_email_id,
        tags=list(row.tags or []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
