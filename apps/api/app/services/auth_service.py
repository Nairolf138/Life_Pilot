"""Services d'authentification pour l'API Life Pilot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import ALGORITHM, create_access_token, verify_password
from app.db.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class TokenType(StrEnum):
    """Types de jetons émis par le service d'authentification."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Utilisateur authentifié exposé aux routes privées."""

    id: UUID
    email: str
    display_name: str | None
    locale: str
    timezone: str
    currency_default: str
    mfa_enabled: bool
    passkey_enabled: bool


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Paire de jetons retournée au client."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class AuthService:
    """Authentifie les utilisateurs et émet des JWT à durée limitée."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate(self, email: str, password: str) -> AuthenticatedUser:
        """Valide les identifiants d'un utilisateur actif."""

        user_row = await self._fetch_user_by_email(email)
        if user_row is None or not user_row.password_hash:
            raise_invalid_credentials()
        if not verify_password(password, user_row.password_hash):
            raise_invalid_credentials()
        return _user_from_row(user_row)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Renouvelle une session à partir d'un jeton de rafraîchissement valide."""

        subject = decode_token_subject(refresh_token, expected_type=TokenType.REFRESH)
        user = await self.get_user_by_id(_uuid_from_subject(subject))
        return create_token_pair(user)

    async def get_user_by_id(self, user_id: UUID) -> AuthenticatedUser:
        """Charge un utilisateur par identifiant pour une route privée."""

        result = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    email,
                    display_name,
                    locale,
                    timezone,
                    currency_default,
                    COALESCE(mfa_enabled, false) AS mfa_enabled,
                    COALESCE(passkey_enabled, false) AS passkey_enabled
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur introuvable.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _user_from_row(row)

    async def _fetch_user_by_email(self, email: str):
        result = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    email,
                    display_name,
                    locale,
                    timezone,
                    currency_default,
                    password_hash,
                    COALESCE(mfa_enabled, false) AS mfa_enabled,
                    COALESCE(passkey_enabled, false) AS passkey_enabled
                FROM users
                WHERE lower(email) = lower(:email)
                """
            ),
            {"email": email},
        )
        return result.mappings().first()


def create_token_pair(user: AuthenticatedUser) -> TokenPair:
    """Crée des jetons d'accès et de rafraîchissement avec claims MFA-ready."""

    settings = get_settings()
    access_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_expires = timedelta(minutes=settings.refresh_token_expire_minutes)
    common_claims = {
        "email": user.email,
        "mfa": user.mfa_enabled,
        "passkey": user.passkey_enabled,
    }
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_expires,
        additional_claims={"typ": TokenType.ACCESS.value, **common_claims},
    )
    refresh_token = create_access_token(
        subject=str(user.id),
        expires_delta=refresh_expires,
        additional_claims={"typ": TokenType.REFRESH.value, **common_claims},
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_expires.total_seconds()),
    )


def decode_token_subject(token: str, expected_type: TokenType) -> str:
    """Décode un JWT et vérifie son type applicatif."""

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        token_type = payload.get("typ")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not subject or token_type != expected_type.value:
        raise_invalid_credentials()
    return str(subject)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    """Construit le service d'authentification pour FastAPI."""

    return AuthService(session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    """Dépendance FastAPI protégeant les routes privées par jeton Bearer."""

    subject = decode_token_subject(token, expected_type=TokenType.ACCESS)
    return await auth_service.get_user_by_id(_uuid_from_subject(subject))


def _uuid_from_subject(subject: str) -> UUID:
    try:
        return UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def raise_invalid_credentials() -> None:
    """Retourne une erreur uniforme pour éviter l'énumération de comptes."""

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_row(row) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        locale=row.locale,
        timezone=row.timezone,
        currency_default=row.currency_default,
        mfa_enabled=bool(row.mfa_enabled),
        passkey_enabled=bool(row.passkey_enabled),
    )
