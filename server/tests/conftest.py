from __future__ import annotations

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

from sigil_server.db import run_migrations
from sigil_server.geolocation import GeoResult
from sigil_server.main import _rate_limit_buckets

MOCK_GEO_DB: dict[str, GeoResult] = {
    "1.2.3.4": GeoResult(country="IN", city="Mumbai", latitude=19.0760, longitude=72.8777),
    "5.6.7.8": GeoResult(country="GB", city="London", latitude=51.5074, longitude=-0.1278),
    "9.10.11.12": GeoResult(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
}


class MockGeoResolver:
    """Deterministic geo resolver for tests — maps known IPs to fixed locations."""

    def resolve(self, ip: str) -> GeoResult | None:
        return MOCK_GEO_DB.get(ip)


@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(e.sync_engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

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
    app.state.geo_resolver = MockGeoResolver()
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
