"""Routes de préférences utilisateur."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.user_settings import UserSettingsPatch, UserSettingsResponse
from app.services.auth_service import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Retourne les préférences de justificatifs de l'utilisateur."""

    result = await session.execute(
        text("SELECT ignored_document_category_ids FROM users WHERE id = :user_id"),
        {"user_id": current_user.id},
    )
    return UserSettingsResponse(
        ignored_document_category_ids=list(result.scalar_one_or_none() or []),
    )


@router.patch("", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSettingsResponse:
    """Met à jour les catégories ignorées pour l'exigence de justificatif."""

    if payload.ignored_document_category_ids:
        result = await session.execute(
            text(
                """
                SELECT count(*)
                FROM categories
                WHERE id = ANY(:category_ids)
                  AND (user_id = :user_id OR is_system = true)
                """
            ),
            {
                "category_ids": payload.ignored_document_category_ids,
                "user_id": current_user.id,
            },
        )
        if int(result.scalar_one()) != len(set(payload.ignored_document_category_ids)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Catégorie introuvable.")

    result = await session.execute(
        text(
            """
            UPDATE users
            SET ignored_document_category_ids = :category_ids,
                updated_at = now()
            WHERE id = :user_id
            RETURNING ignored_document_category_ids
            """
        ),
        {
            "category_ids": payload.ignored_document_category_ids,
            "user_id": current_user.id,
        },
    )
    await session.commit()
    return UserSettingsResponse(
        ignored_document_category_ids=list(result.scalar_one() or []),
    )
