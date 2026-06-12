"""Tests for the GET /health endpoint."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_healthy_when_db_connected(client):
    """GET /health returns 200 with {"status": "healthy"} when DB is reachable."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_health_does_not_require_auth(client):
    """GET /health should NOT require an Authorization header."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "detail" not in resp.json()
