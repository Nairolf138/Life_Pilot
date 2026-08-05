"""Contrôles de sécurité de l'API Life Pilot."""

from __future__ import annotations

import logging
import subprocess
import sys
from io import StringIO
from pathlib import Path

from fastapi.routing import APIRoute

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.api.routes import api_router
from app.connectors.assets import BinanceAssetConnector, EtoroAssetConnector
from app.core.logging import JsonFormatter, SensitiveDataFilter
from app.schemas.asset import AssetResponse
from app.schemas.document import DocumentResponse
from app.schemas.transaction import TransactionResponse
from app.services.auth_service import get_current_user
from app.services.document_service import DocumentService

REPO_ROOT = Path(__file__).resolve().parents[4]
PRIVATE_GET_ROUTES = (
    "/accounts",
    "/transactions",
    "/documents",
    "/documents/{id}",
    "/documents/{id}/download",
    "/contracts",
    "/dashboard/monthly-summary?month=2026-07",
    "/vehicles",
    "/assets",
    "/assets/summary",
    "/reminders",
    "/settings",
    "/tax/year-files",
    "/auth/me",
)
SECRET_RESPONSE_FIELDS = {
    "access_token",
    "refresh_token",
    "token",
    "password",
    "password_hash",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "raw_data_json",
    "file_path",
    "file_hash",
    "extracted_text",
}
READ_ONLY_METHODS = {
    "list_positions",
    "get_balances",
    "get_price_snapshot",
    "sync_history",
}
FORBIDDEN_CONNECTOR_METHODS = {
    "buy",
    "sell",
    "trade",
    "transfer",
    "withdraw",
    "deposit",
    "place_order",
    "create_order",
    "cancel_order",
}
KNOWN_SECRET_VALUES = (
    "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret.payload",
    "sk-test-known-secret",
    "refresh-token-known-secret",
    "password=known-password",
    "api_key=known-api-key",
)


def public_callables(connector_cls: type) -> set[str]:
    """Retourne les méthodes publiques exposées par une classe de connecteur."""

    return {
        name
        for name in dir(connector_cls)
        if not name.startswith("_") and callable(getattr(connector_cls, name))
    }


def collect_api_routes(routes) -> list[APIRoute]:
    """Aplatit les routeurs inclus selon la version FastAPI installée."""

    collected: list[APIRoute] = []
    for route in routes:
        if isinstance(route, APIRoute):
            collected.append(route)
        elif hasattr(route, "original_router"):
            collected.extend(collect_api_routes(route.original_router.routes))
        elif hasattr(route, "routes"):
            collected.extend(collect_api_routes(route.routes))
    return collected


def route_requires_current_user(route: APIRoute) -> bool:
    """Indique si une route FastAPI dépend explicitement de get_current_user."""

    dependencies = list(route.dependant.dependencies)
    while dependencies:
        dependency = dependencies.pop()
        if dependency.call is get_current_user:
            return True
        dependencies.extend(dependency.dependencies)
    return False


def test_private_routes_require_authentication_dependency() -> None:
    """Les routes privées doivent exiger la dépendance bearer get_current_user."""

    routes_by_path = {
        route.path: route
        for route in collect_api_routes(api_router.routes)
        if "GET" in route.methods
    }

    for route_path in PRIVATE_GET_ROUTES:
        normalized_path = route_path.split("?", 1)[0]
        route = routes_by_path.get(normalized_path)

        assert route is not None, route_path
        assert route_requires_current_user(route), route_path


def test_api_response_schemas_do_not_expose_secret_fields() -> None:
    """Les réponses métier ne doivent pas exposer secrets ou données internes."""

    response_models = (DocumentResponse, TransactionResponse, AssetResponse)

    for model in response_models:
        exposed_fields = set(model.model_fields)

        assert exposed_fields.isdisjoint(SECRET_RESPONSE_FIELDS), model.__name__


def test_document_routes_require_authentication_dependency() -> None:
    """Les métadonnées et le téléchargement documentaire exigent l'authentification."""

    document_routes = {
        route.path: route
        for route in collect_api_routes(api_router.routes)
        if route.path.startswith("/documents/{id}")
    }

    for route_path in ("/documents/{id}", "/documents/{id}/download"):
        assert route_path in document_routes
        assert route_requires_current_user(document_routes[route_path])


def test_document_service_queries_are_scoped_to_authenticated_user() -> None:
    """Les accès documentaires doivent filtrer par l'utilisateur courant."""

    source = Path(DocumentService.__module__.replace(".", "/") + ".py")
    service_path = REPO_ROOT / "apps" / "api" / source
    service_source = service_path.read_text(encoding="utf-8")

    document_access_patterns = (
        "WHERE user_id = :user_id",
        "AND user_id = :user_id",
    )

    assert all(pattern in service_source for pattern in document_access_patterns)
    assert "WHERE id = :document_id" not in service_source.replace(
        "WHERE id = :document_id\n                  AND user_id = :user_id", ""
    )


def test_test_logs_redact_known_tokens_and_secrets() -> None:
    """Les logs de test ne doivent contenir aucun token ou secret connu."""

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SensitiveDataFilter())
    logger = logging.getLogger("lifepilot.security-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info(
        "payload=%s",
        {
            "authorization": KNOWN_SECRET_VALUES[0],
            "llm_api_key": KNOWN_SECRET_VALUES[1],
            "refresh_token": KNOWN_SECRET_VALUES[2],
            "message": f"{KNOWN_SECRET_VALUES[3]} {KNOWN_SECRET_VALUES[4]}",
        },
    )

    output = stream.getvalue()
    for secret in KNOWN_SECRET_VALUES:
        assert secret not in output


def test_real_env_file_is_not_versioned() -> None:
    """Le vrai .env ne doit pas être suivi par Git."""

    git_dir = REPO_ROOT / ".git"
    tracked_files = (REPO_ROOT / ".gitignore").exists() or git_dir.exists()
    assert tracked_files

    result = subprocess.run(
        ["git", "ls-files", "--", ".env", "apps/api/.env"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert result.stdout.strip() == ""


def test_financial_asset_connectors_expose_read_only_api_only() -> None:
    """Les connecteurs financiers doivent rester strictement en lecture seule."""

    for connector_cls in (BinanceAssetConnector, EtoroAssetConnector):
        exposed_methods = public_callables(connector_cls)

        assert READ_ONLY_METHODS.issubset(exposed_methods)
        assert exposed_methods.isdisjoint(FORBIDDEN_CONNECTOR_METHODS)
