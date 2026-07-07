"""Routes auth de l'API Life Pilot."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field

from app.services.auth_service import (
    AuthenticatedUser,
    AuthService,
    TokenPair,
    create_token_pair,
    get_auth_service,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Identifiants nécessaires à l'ouverture de session."""

    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class RefreshRequest(BaseModel):
    """Jeton utilisé pour prolonger une session."""

    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    """Réponse de session renvoyée par login et refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Profil minimal de l'utilisateur authentifié."""

    id: str
    email: EmailStr
    display_name: str | None
    locale: str
    timezone: str
    currency_default: str
    mfa_enabled: bool
    passkey_enabled: bool


class LogoutResponse(BaseModel):
    """Confirmation de fermeture de session côté client."""

    detail: str


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authentifie un utilisateur et retourne une paire de JWT expirables."""

    user = await auth_service.authenticate(payload.email, payload.password)
    return _token_response(create_token_pair(user))


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> LogoutResponse:
    """Ferme la session en demandant au client de supprimer ses jetons."""

    _ = current_user
    return LogoutResponse(detail="Session fermée. Supprimez les jetons côté client.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Émet une nouvelle paire de jetons depuis un refresh token valide."""

    return _token_response(await auth_service.refresh(payload.refresh_token))


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserResponse:
    """Retourne le profil minimal associé au jeton d'accès."""

    return _user_response(current_user)


def _token_response(token_pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


def _user_response(user: AuthenticatedUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        locale=user.locale,
        timezone=user.timezone,
        currency_default=user.currency_default,
        mfa_enabled=user.mfa_enabled,
        passkey_enabled=user.passkey_enabled,
    )
