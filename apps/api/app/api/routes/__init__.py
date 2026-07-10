"""Agrégation des routeurs HTTP Life Pilot."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    accounts,
    assets,
    assistant,
    auth,
    contracts,
    dashboard,
    documents,
    health,
    internal,
    reminders,
    settings,
    transactions,
    vehicles,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(internal.router)
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(documents.router)
api_router.include_router(contracts.router)
api_router.include_router(dashboard.router)
api_router.include_router(vehicles.router)
api_router.include_router(assets.router)
api_router.include_router(reminders.router)
api_router.include_router(settings.router)
api_router.include_router(assistant.router)
