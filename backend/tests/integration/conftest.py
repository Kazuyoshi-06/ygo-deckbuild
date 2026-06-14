"""
Shared fixtures for integration tests against a real PostgreSQL database.

Set TEST_DATABASE_URL before running (or export it in your shell):
    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ygo_deckbuild_test

Tables are created once per session and truncated between each test.
"""
import os

import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Base  # noqa: F401 — registers all models with Base.metadata

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ygo_deckbuild_test",
)

_TRUNCATE_ALL = text(
    "TRUNCATE TABLE "
    "deck_cards, deck_submissions, decks, "
    "banlist_entries, banlists, "
    "card_images, cards, "
    "sync_runs, players, tournaments "
    "RESTART IDENTITY CASCADE"
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test DB tables once per test session, drop them at teardown."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(engine):
    """Truncate all tables after each test to guarantee isolation."""
    yield
    async with engine.begin() as conn:
        await conn.execute(_TRUNCATE_ALL)


@pytest_asyncio.fixture
async def db(engine):
    """Async session bound to the test engine, shared with the HTTP client."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    """HTTP client wired to the FastAPI app, using the test DB session and a mock user."""
    from app.main import app

    async def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: "test_user"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(db):
    """HTTP client that always returns 401 for auth-protected routes."""
    from app.main import app

    async def _get_db():
        yield db

    async def _deny():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _deny
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
