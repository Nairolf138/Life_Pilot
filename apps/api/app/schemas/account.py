"""Schémas Pydantic pour les comptes financiers."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountBase(BaseModel):
    """Champs communs modifiables d'un compte."""

    provider: str = Field(min_length=1, max_length=120)
    account_type: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    balance_current: Decimal | None = Field(
        default=None,
        max_digits=18,
        decimal_places=2,
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalise le code devise ISO 4217 en majuscules."""

        return value.upper()


class ManualAccountCreate(AccountBase):
    """Données nécessaires à la création manuelle d'un compte."""

    iban: str | None = Field(default=None, min_length=5, max_length=34)


class AccountUpdate(BaseModel):
    """Champs modifiables d'un compte existant."""

    provider: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    balance_current: Decimal | None = Field(
        default=None,
        max_digits=18,
        decimal_places=2,
    )
    iban: str | None = Field(default=None, min_length=5, max_length=34)
    is_active: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        """Normalise le code devise ISO 4217 en majuscules."""

        return value.upper() if value else value


class AccountResponse(BaseModel):
    """Représentation publique d'un compte financier."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    account_type: str
    name: str
    iban_masked: str | None
    currency: str
    balance_current: Decimal | None
    is_active: bool
