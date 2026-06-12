from __future__ import annotations

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigil_server.db import run_migrations
from sigil_server.main import _rate_limit_buckets


@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    await run_migrations(e)
    yield e
    await e.dispose()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    _rate_limit_buckets.clear()
    yield
    _rate_limit_buckets.clear()


@pytest.fixture
async def client(engine):
    from sigil_server.main import create_app

    app = create_app(engine=engine)
    app.state.engine = engine
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def api_keys(client):
    """Create a key pair and return (publishable_key, secret_key)."""
    resp = await client.post("/admin/api-keys", json={
        "allowedOrigins": ["https://test.com"],
    })
    data = resp.json()
    return data["publishableKey"], data["secretKey"]


@pytest.fixture
def sk_auth_headers(api_keys):
    """Authorization headers using the secret key."""
    _pk, sk = api_keys
    return {"Authorization": f"Bearer {sk}"}
