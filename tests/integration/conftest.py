"""Fixtures d'intégration FastAPI/PostgreSQL.

Ces tests ciblent une vraie base PostgreSQL. Démarrage local recommandé :

    docker compose -f docker-compose.test.yml up -d postgres-test
    TEST_DATABASE_URL=postgresql+asyncpg://lifepilot:lifepilot@localhost:55432/lifepilot_test \
      PYTHONPATH=apps/api pytest tests/integration
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

try:
    import pytest_asyncio
except ModuleNotFoundError:  # pragma: no cover - environnement sans dépendances dev
    async_fixture = pytest.fixture
else:
    async_fixture = pytest_asyncio.fixture

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

pytestmark = pytest.mark.integration


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: tests requiring PostgreSQL")
    config.addinivalue_line("markers", "asyncio: async integration tests")


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL absent. Lancez PostgreSQL avec "
            "docker compose -f docker-compose.test.yml up -d postgres-test."
        )
    return url


@async_fixture(scope="session")
async def db_engine(test_database_url: str):
    engine = create_async_engine(test_database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        for migration in sorted((REPO_ROOT / "database" / "migrations").glob("*.sql")):
            await conn.execute(text(migration.read_text(encoding="utf-8")))
        await conn.execute(
            text(
                (REPO_ROOT / "database" / "seeds" / "001_system_categories.sql")
                .read_text(encoding="utf-8")
            )
        )
    yield engine
    await engine.dispose()


@async_fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session:
        yield session


@async_fixture
async def client(db_engine, tmp_path, monkeypatch):
    httpx = pytest.importorskip("httpx")
    monkeypatch.setenv("DATABASE_URL", str(db_engine.url))
    monkeypatch.setenv("SECRET_KEY", "integration-test-secret")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "documents"))
    monkeypatch.setenv("STORAGE_BACKEND", "local")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.db.session as db_session_module

    db_session_module.engine = db_engine
    db_session_module.AsyncSessionLocal = async_sessionmaker(
        bind=db_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    from app.main import create_app

    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as async_client:
        yield async_client
