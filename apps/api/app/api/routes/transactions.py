"""Routes transactions de l'API Life Pilot."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from app.schemas.transaction import (
    TransactionCategoryPatch,
    TransactionDocumentLink,
    TransactionImportRequest,
    TransactionImportResponse,
    TransactionResponse,
)
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.importers.csv_bank_importer import CsvBankImporter, config_from_json
from app.services.transaction_service import TransactionService, get_transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
    account_id: Annotated[
        UUID | None,
        Query(description="Filtre par compte."),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Date de début incluse."),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Date de fin incluse."),
    ] = None,
    category_id: Annotated[
        UUID | None,
        Query(description="Filtre par catégorie."),
    ] = None,
    amount_min: Annotated[
        Decimal | None,
        Query(description="Montant minimum inclus."),
    ] = None,
    amount_max: Annotated[
        Decimal | None,
        Query(description="Montant maximum inclus."),
    ] = None,
    without_reliable_category: Annotated[
        bool,
        Query(description="Transactions sans catégorie fiable."),
    ] = False,
    without_document: Annotated[
        bool,
        Query(description="Transactions sans justificatif lié."),
    ] = False,
) -> list[TransactionResponse]:
    """Liste les transactions de l'utilisateur authentifié avec filtres."""

    return await transaction_service.list_transactions(
        current_user.id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        amount_min=amount_min,
        amount_max=amount_max,
        without_reliable_category=without_reliable_category,
        without_document=without_document,
    )


@router.get("/{id}", response_model=TransactionResponse)
async def get_transaction(
    id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Retourne le détail d'une transaction de l'utilisateur authentifié."""

    return await transaction_service.get_transaction(current_user.id, id)


@router.post(
    "/import",
    response_model=TransactionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_transactions(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionImportResponse:
    """Importe des transactions depuis JSON, upload CSV ou chemin CSV serveur."""

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        payload = await _csv_import_payload_from_form(request)
    else:
        payload = TransactionImportRequest.model_validate(await request.json())
    return await transaction_service.import_transactions(current_user.id, payload)


async def _csv_import_payload_from_form(request: Request) -> TransactionImportRequest:
    """Construit un payload d'import depuis un formulaire multipart CSV."""

    form = await request.form()
    account_id = form.get("account_id")
    if not isinstance(account_id, str) or not account_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le champ form-data account_id est requis pour un import CSV.",
        )
    mapping_json = form.get("mapping")
    config_json = mapping_json if isinstance(mapping_json, str) else None
    try:
        config = config_from_json(config_json, account_id=UUID(account_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    importer = CsvBankImporter(config)

    uploaded_file = form.get("file")
    file_path = form.get("file_path")
    if uploaded_file is not None and hasattr(uploaded_file, "file"):
        try:
            result = importer.parse_upload(
                uploaded_file.file,
                filename=getattr(uploaded_file, "filename", None),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
    elif isinstance(file_path, str) and file_path.strip():
        try:
            result = importer.parse_path(file_path)
        except (OSError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Fournir un fichier CSV uploadé (file) "
                "ou un chemin serveur (file_path)."
            ),
        )
    return result.request


@router.patch("/{id}/category", response_model=TransactionResponse)
async def update_transaction_category(
    id: UUID,
    payload: TransactionCategoryPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Met à jour la catégorie d'une transaction."""

    return await transaction_service.update_category(current_user.id, id, payload)


@router.post("/{id}/link-document", response_model=TransactionResponse)
async def link_transaction_document(
    id: UUID,
    payload: TransactionDocumentLink,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    transaction_service: Annotated[
        TransactionService,
        Depends(get_transaction_service),
    ],
) -> TransactionResponse:
    """Lie un justificatif à une transaction."""

    return await transaction_service.link_document(current_user.id, id, payload)
