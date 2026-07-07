"""Schémas de réponse pour les routes de supervision."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Réponse standard de l'endpoint GET /health."""

    status: str
    service: str
