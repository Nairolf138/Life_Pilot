"""Routes internes réservées aux automatisations serveur-à-serveur."""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)

from app.core.config import Settings, get_settings
from app.schemas.document import (
    DocumentExtractRequest,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(prefix="/internal", tags=["internal"])


class InternalDocumentIngestionResponse(DocumentUploadResponse):
    """Résultat d'ingestion interne avec extraction texte déclenchée."""

    extraction: DocumentResponse


async def verify_n8n_secret(
    settings: Annotated[Settings, Depends(get_settings)],
    x_n8n_secret: Annotated[str | None, Header(alias="X-N8N-Secret")] = None,
) -> None:
    """Vérifie le secret partagé utilisé par les workflows n8n internes."""

    if not settings.n8n_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Secret interne n8n non configuré.",
        )
    if not x_n8n_secret or not compare_digest(
        x_n8n_secret, settings.n8n_internal_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret interne n8n invalide.",
        )


@router.post(
    "/n8n/documents",
    response_model=InternalDocumentIngestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_n8n_secret)],
)
async def ingest_n8n_document(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: Annotated[
        UploadFile, File(description="PDF téléchargé depuis Gmail par n8n.")
    ],
    user_id: Annotated[
        UUID, Form(description="Utilisateur Life Pilot propriétaire du document.")
    ],
    document_type: Annotated[
        str,
        Form(
            description="Type simple déduit par n8n, par exemple invoice ou contract."
        ),
    ] = "email_pdf",
    title: Annotated[
        str | None,
        Form(description="Titre issu du sujet Gmail ou du nom de pièce jointe."),
    ] = None,
) -> InternalDocumentIngestionResponse:
    """Reçoit un PDF depuis n8n, le stocke puis déclenche l'extraction texte."""

    uploaded = await document_service.upload_document(
        user_id,
        file=file,
        document_type=document_type,
        title=title,
    )
    extracted = await document_service.extract_document(
        user_id, uploaded.document.id, DocumentExtractRequest()
    )
    return InternalDocumentIngestionResponse(
        document=uploaded.document,
        duplicate=uploaded.duplicate,
        extraction=extracted,
    )
