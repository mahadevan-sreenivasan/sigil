from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text


async def test_api_keys_table_created_by_migration(engine):
    """Migration 002 creates api_keys with expected columns."""
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
        )
        assert row.first() is not None, "api_keys table should exist after migrations"


async def test_create_api_key_pair(client, engine):
    """POST /admin/api-keys returns pk_live_ + sk_live_ key pair, stores hashes."""
    resp = await client.post("/admin/api-keys", json={
        "allowedOrigins": ["https://example.com"],
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["publishableKey"].startswith("pk_live_")
    assert data["secretKey"].startswith("sk_live_")

    pk_hash = hashlib.sha256(data["publishableKey"].encode()).hexdigest()
    sk_hash = hashlib.sha256(data["secretKey"].encode()).hexdigest()

    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT key_type, key_prefix FROM api_keys WHERE key_hash = :h"),
            {"h": pk_hash},
        )
        pk_row = row.first()
        assert pk_row is not None
        assert pk_row[0] == "publishable"
        assert pk_row[1] == "pk_live_"

        row = await conn.execute(
            text("SELECT key_type, key_prefix FROM api_keys WHERE key_hash = :h"),
            {"h": sk_hash},
        )
        sk_row = row.first()
        assert sk_row is not None
        assert sk_row[0] == "secret"
        assert sk_row[1] == "sk_live_"


async def _seed_keys(client):
    """Helper: create a key pair and return (publishable_key, secret_key)."""
    resp = await client.post("/admin/api-keys", json={
        "allowedOrigins": ["https://allowed.com"],
    })
    data = resp.json()
    return data["publishableKey"], data["secretKey"]


async def test_missing_auth_header_returns_401(client):
    """Requests without Authorization header get 401."""
    resp = await client.post("/identify", json={"signals": {"canvas": "x"}})
    assert resp.status_code == 401


async def test_invalid_api_key_returns_401(client):
    """Requests with a key not in the database get 401."""
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "x"}},
        headers={"Authorization": "Bearer pk_live_bogus_key_that_does_not_exist"},
    )
    assert resp.status_code == 401


async def test_publishable_key_on_non_identify_returns_403(client):
    """Publishable keys are rejected on endpoints other than POST /identify."""
    pk, _sk = await _seed_keys(client)
    resp = await client.get(
        "/visitors/vis_fake",
        headers={"Authorization": f"Bearer {pk}"},
    )
    assert resp.status_code == 403


async def test_secret_key_on_identify_returns_200(client):
    """Secret keys work on POST /identify."""
    _pk, sk = await _seed_keys(client)
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={"Authorization": f"Bearer {sk}"},
    )
    assert resp.status_code == 200


async def test_publishable_key_wrong_origin_returns_403(client):
    """Publishable key from an unregistered origin is rejected."""
    pk, _sk = await _seed_keys(client)
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={
            "Authorization": f"Bearer {pk}",
            "Origin": "https://evil.com",
        },
    )
    assert resp.status_code == 403


async def test_publishable_key_correct_origin_returns_200(client):
    """Publishable key from a registered origin succeeds."""
    pk, _sk = await _seed_keys(client)
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={
            "Authorization": f"Bearer {pk}",
            "Origin": "https://allowed.com",
        },
    )
    assert resp.status_code == 200


async def test_rate_limit_returns_429(client, monkeypatch):
    """Exceeding rate limit on publishable key returns 429."""
    monkeypatch.setenv("SIGIL_RATE_LIMIT_RPS", "3")

    pk, _sk = await _seed_keys(client)
    headers = {
        "Authorization": f"Bearer {pk}",
        "Origin": "https://allowed.com",
    }
    payload = {"signals": {"canvas": "abc"}}

    statuses = []
    for _ in range(5):
        resp = await client.post("/identify", json=payload, headers=headers)
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Expected at least one 429, got {statuses}"
    assert statuses.count(200) <= 3


async def test_publishable_key_omits_sensitive_fields(client):
    """Publishable key response omits accountIds from similarVisitors and accountHistory."""
    pk, _sk = await _seed_keys(client)
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={
            "Authorization": f"Bearer {pk}",
            "Origin": "https://allowed.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "accountHistory" not in data
    if data.get("similarVisitors"):
        for sv in data["similarVisitors"]:
            assert "accountIds" not in sv


async def test_secret_key_includes_all_fields(client):
    """Secret key response includes accountHistory and accountIds in similarVisitors."""
    _pk, sk = await _seed_keys(client)
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={"Authorization": f"Bearer {sk}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "accountHistory" in data
