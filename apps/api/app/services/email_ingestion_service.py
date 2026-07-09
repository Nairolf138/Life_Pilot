"""Service d'ingestion et de déduplication des emails entrants."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.document_service import (
    DOCUMENT_COLUMNS,
    DocumentRecord,
    _document_from_row,
)
from app.services.storage_service import StorageService, get_storage_service


@dataclass(frozen=True, slots=True)
class EmailAttachmentDocument:
    """Document à créer depuis une pièce jointe d'email."""

    filename: str | None
    content: bytes
    mime_type: str | None = None
    document_type: str = "email_attachment"
    title: str | None = None
    provider: str | None = None


@dataclass(frozen=True, slots=True)
class EmailIngestionPayload:
    """Données normalisées d'un email à persister."""

    provider: str
    external_message_id_hash: str
    received_at: datetime
    thread_id_hash: str | None = None
    from_email_hash: str | None = None
    from_name: str | None = None
    subject: str | None = None
    snippet: str | None = None
    classification: str | None = None
    has_attachments: bool = False
    processed_at: datetime | None = None
    raw_headers_json: dict[str, Any] = field(default_factory=dict)
    documents: list[EmailAttachmentDocument] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EmailRecord:
    """Email ingéré retourné par le service."""

    id: UUID
    user_id: UUID
    provider: str
    external_message_id_hash: str
    thread_id_hash: str | None
    from_email_hash: str | None
    from_name: str | None
    subject: str | None
    received_at: datetime
    snippet: str | None
    classification: str | None
    has_attachments: bool
    processed_at: datetime | None
    raw_headers_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class EmailIngestionResult:
    """Résultat d'ingestion avec indicateur de déduplication."""

    email: EmailRecord
    documents: list[DocumentRecord]
    duplicate: bool = False


class EmailIngestionService:
    """Persiste les emails entrants et les documents extraits associés."""

    def __init__(self, session: AsyncSession, storage_service: StorageService) -> None:
        self._session = session
        self._storage_service = storage_service

    async def ingest_email(
        self,
        user_id: UUID,
        payload: EmailIngestionPayload,
    ) -> EmailIngestionResult:
        """Insère un email et ses documents, en évitant les doublons."""

        existing_email = await self._fetch_email_by_external_message_id(
            payload.provider,
            payload.external_message_id_hash,
        )
        if existing_email is not None:
            documents = await self._fetch_documents_for_email(
                user_id, existing_email.id
            )
            return EmailIngestionResult(
                email=_email_from_row(existing_email),
                documents=documents,
                duplicate=True,
            )

        email = await self._insert_email(user_id, payload)
        documents = await self._create_documents_from_email(user_id, email.id, payload)
        await self._session.commit()
        return EmailIngestionResult(email=email, documents=documents, duplicate=False)

    async def _insert_email(
        self, user_id: UUID, payload: EmailIngestionPayload
    ) -> EmailRecord:
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO emails (
                    user_id, provider, external_message_id_hash, thread_id_hash,
                    from_email_hash, from_name, subject, received_at, snippet,
                    classification, has_attachments, processed_at, raw_headers_json
                ) VALUES (
                    :user_id, :provider, :external_message_id_hash, :thread_id_hash,
                    :from_email_hash, :from_name, :subject, :received_at, :snippet,
                    :classification, :has_attachments, :processed_at, :raw_headers_json
                )
                RETURNING {EMAIL_COLUMNS}
                """
            ),
            {
                "user_id": user_id,
                "provider": payload.provider,
                "external_message_id_hash": payload.external_message_id_hash,
                "thread_id_hash": payload.thread_id_hash,
                "from_email_hash": payload.from_email_hash,
                "from_name": payload.from_name,
                "subject": payload.subject,
                "received_at": payload.received_at,
                "snippet": payload.snippet,
                "classification": payload.classification,
                "has_attachments": payload.has_attachments or bool(payload.documents),
                "processed_at": payload.processed_at,
                "raw_headers_json": payload.raw_headers_json,
            },
        )
        return _email_from_row(result.mappings().one())

    async def _create_documents_from_email(
        self, user_id: UUID, email_id: UUID, payload: EmailIngestionPayload
    ) -> list[DocumentRecord]:
        documents: list[DocumentRecord] = []
        for attachment in payload.documents:
            stored_file = self._storage_service.upload_document_bytes(
                user_id=user_id,
                document_type=attachment.document_type,
                filename=attachment.filename,
                content=attachment.content,
                mime_type=attachment.mime_type,
            )
            result = await self._session.execute(
                text(
                    f"""
                    INSERT INTO documents (
                        user_id, provider, document_type, title, file_path, file_hash,
                        mime_type, extraction_status, source_email_id
                    ) VALUES (
                        :user_id, :provider, :document_type, :title, :file_path,
                        :file_hash, :mime_type, 'pending', :source_email_id
                    )
                    ON CONFLICT (user_id, file_hash) DO UPDATE
                    SET source_email_id = EXCLUDED.source_email_id,
                        updated_at = now()
                    RETURNING {DOCUMENT_COLUMNS}
                    """
                ),
                {
                    "user_id": user_id,
                    "provider": attachment.provider or payload.provider,
                    "document_type": attachment.document_type,
                    "title": (
                        attachment.title
                        or attachment.filename
                        or payload.subject
                        or "document"
                    ),
                    "file_path": stored_file.file_path,
                    "file_hash": stored_file.file_hash,
                    "mime_type": stored_file.mime_type,
                    "source_email_id": email_id,
                },
            )
            documents.append(_document_from_row(result.mappings().one()))
        return documents

    async def _fetch_email_by_external_message_id(
        self, provider: str, external_message_id_hash: str
    ):
        result = await self._session.execute(
            text(
                f"""
                SELECT {EMAIL_COLUMNS}
                FROM emails
                WHERE provider = :provider
                  AND external_message_id_hash = :external_message_id_hash
                """
            ),
            {
                "provider": provider,
                "external_message_id_hash": external_message_id_hash,
            },
        )
        return result.mappings().first()

    async def _fetch_documents_for_email(
        self, user_id: UUID, email_id: UUID
    ) -> list[DocumentRecord]:
        result = await self._session.execute(
            text(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                WHERE user_id = :user_id
                  AND source_email_id = :source_email_id
                ORDER BY created_at ASC
                """
            ),
            {"user_id": user_id, "source_email_id": email_id},
        )
        return [_document_from_row(row) for row in result.mappings().all()]


EMAIL_COLUMNS = """
    id, user_id, provider, external_message_id_hash, thread_id_hash,
    from_email_hash, from_name, subject, received_at, snippet, classification,
    has_attachments, processed_at, raw_headers_json, created_at, updated_at
"""


async def get_email_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> EmailIngestionService:
    """Construit le service d'ingestion d'emails pour FastAPI."""

    return EmailIngestionService(session, storage_service)


def _email_from_row(row) -> EmailRecord:
    return EmailRecord(
        id=row.id,
        user_id=row.user_id,
        provider=row.provider,
        external_message_id_hash=row.external_message_id_hash,
        thread_id_hash=row.thread_id_hash,
        from_email_hash=row.from_email_hash,
        from_name=row.from_name,
        subject=row.subject,
        received_at=row.received_at,
        snippet=row.snippet,
        classification=row.classification,
        has_attachments=row.has_attachments,
        processed_at=row.processed_at,
        raw_headers_json=dict(row.raw_headers_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
