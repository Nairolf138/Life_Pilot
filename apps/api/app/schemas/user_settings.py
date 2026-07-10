"""Schémas des préférences utilisateur."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserSettingsResponse(BaseModel):
    """Préférences utilisateur exposées par l'API."""

    model_config = ConfigDict(from_attributes=True)

    ignored_document_category_ids: list[UUID] = Field(default_factory=list)


class UserSettingsPatch(BaseModel):
    """Mise à jour partielle des préférences utilisateur."""

    ignored_document_category_ids: list[UUID] = Field(default_factory=list)
