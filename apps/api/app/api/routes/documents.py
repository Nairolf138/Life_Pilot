"""Routes documents de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile, status

from app.schemas.document import (
    DocumentExtractRequest,
    DocumentResponse,
    DocumentTransactionLink,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentResponse]:
    """Liste les documents de l'utilisateur authentifié."""

    return await document_service.list_documents(current_user.id)


@router.get("/{id}", response_model=DocumentResponse)
async def get_document(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Retourne le détail d'un document de l'utilisateur authentifié."""

    return await document_service.get_document(current_user.id, id)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: Annotated[UploadFile, File(description="Fichier document à stocker.")],
    document_type: Annotated[str, Form(description="Type métier du document.")],
    title: Annotated[str | None, Form(description="Titre lisible du document.")] = None,
) -> DocumentUploadResponse:
    """Téléverse un document avec déduplication par hash de fichier."""

    return await document_service.upload_document(
        current_user.id,
        file=file,
        document_type=document_type,
        title=title,
    )


@router.post("/{id}/extract", response_model=DocumentResponse)
async def extract_document(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    payload: Annotated[
        DocumentExtractRequest | None,
        Body(description="Résultat OCR optionnel à enregistrer."),
    ] = None,
) -> DocumentResponse:
    """Enregistre ou déclenche le statut d'extraction d'un document."""

    return await document_service.extract_document(
        current_user.id, id, payload or DocumentExtractRequest()
    )


@router.post("/{id}/link-transaction", response_model=DocumentResponse)
async def link_document_transaction(
    id: UUID,
    payload: DocumentTransactionLink,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Lie un document à une transaction de l'utilisateur authentifié."""

    return await document_service.link_transaction(current_user.id, id, payload)


@router.patch("/{id}", response_model=DocumentResponse)
async def update_document(
    id: UUID,
    payload: DocumentUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Met à jour les métadonnées d'un document."""

    return await document_service.update_document(current_user.id, id, payload)
