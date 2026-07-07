"""Routes auth de l'API Life Pilot."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
