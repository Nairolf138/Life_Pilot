"""Routes assets de l'API Life Pilot."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.asset import AssetResponse, AssetSyncResponse, NetWorthSummaryResponse
from app.services.asset_service import AssetService, get_asset_service
from app.services.auth_service import AuthenticatedUser, get_current_user
from app.services.net_worth_service import NetWorthService, get_net_worth_service

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> list[AssetResponse]:
    """Liste les actifs de l'utilisateur authentifié."""

    return await asset_service.list_assets(current_user.id)


@router.get("/summary", response_model=NetWorthSummaryResponse)
async def get_assets_summary(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    net_worth_service: Annotated[NetWorthService, Depends(get_net_worth_service)],
) -> NetWorthSummaryResponse:
    """Retourne une synthèse du patrimoine de l'utilisateur authentifié."""

    return await net_worth_service.get_summary(current_user.id)


@router.post("/sync", response_model=AssetSyncResponse)
async def sync_assets(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetSyncResponse:
    """Synchronise les valorisations locales des actifs de l'utilisateur."""

    synced_at, assets = await asset_service.sync_assets(current_user.id)
    return AssetSyncResponse(
        synced_at=synced_at or datetime.now(UTC),
        updated_count=len(assets),
        assets=assets,
    )
