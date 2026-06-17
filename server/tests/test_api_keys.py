from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text

ADMIN_TOKEN = "test-admin-token-that-is-long-enough-for-validation"


async def test_api_keys_table_created_by_migration(engine):
    """Migration 002 creates api_keys with expected columns."""
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
        )
        assert row.first() is not None, "api_keys table should exist after migrations"


async def test_create_api_key_pair(client, engine):
    """POST /admin/api-keys returns pk_live_ + sk_live_ key pair, stores hashes."""
    resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": ["https://example.com"]},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
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
        assert len(pk_row[1]) == 14
        assert pk_row[1].startswith("pk_live_")

        row = await conn.execute(
            text("SELECT key_type, key_prefix FROM api_keys WHERE key_hash = :h"),
            {"h": sk_hash},
        )
        sk_row = row.first()
        assert sk_row is not None
        assert sk_row[0] == "secret"
        assert len(sk_row[1]) == 14
        assert sk_row[1].startswith("sk_live_")


async def _seed_keys(client):
    """Helper: create a key pair and return (publishable_key, secret_key)."""
    resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": ["https://allowed.com"]},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
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


async def test_admin_endpoint_without_auth_returns_401(client):
    """POST /admin/api-keys without an Authorization header returns 401."""
    resp = await client.post("/admin/api-keys", json={"allowedOrigins": []})
    assert resp.status_code == 401


async def test_admin_endpoint_with_wrong_token_returns_401(client):
    """POST /admin/api-keys with an incorrect admin token returns 401."""
    resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": []},
        headers={"Authorization": "Bearer wrong-token-value-that-is-long-enough"},
    )
    assert resp.status_code == 401


async def test_admin_endpoint_with_api_key_returns_401(client):
    """POST /admin/api-keys with a secret API key (not admin token) returns 401."""
    _pk, sk = await _seed_keys(client)
    resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": []},
        headers={"Authorization": f"Bearer {sk}"},
    )
    assert resp.status_code == 401


async def test_admin_endpoint_with_correct_token_returns_200(client):
    """POST /admin/api-keys with the correct admin token succeeds."""
    resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": ["https://example.com"]},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["publishableKey"].startswith("pk_live_")
    assert data["secretKey"].startswith("sk_live_")


async def test_list_api_keys_returns_metadata(client):
    """GET /admin/api-keys returns key metadata without exposing full keys or hashes."""
    create_resp = await client.post(
        "/admin/api-keys",
        json={"allowedOrigins": ["https://example.com"]},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    created = create_resp.json()

    resp = await client.get(
        "/admin/api-keys",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) >= 2

    prefixes = {k["keyPrefix"] for k in keys}
    assert created["publishableKey"][:14] in prefixes
    assert created["secretKey"][:14] in prefixes

    for key in keys:
        assert "keyPrefix" in key
        assert "keyType" in key
        assert "allowedOrigins" in key
        assert "createdAt" in key
        assert "revokedAt" in key
        assert "keyHash" not in key
        assert "key_hash" not in key
        assert len(key["keyPrefix"]) == 14


async def test_revoke_api_key_returns_metadata_with_revoked_at(client):
    """DELETE /admin/api-keys/{prefix} revokes key and returns metadata with revokedAt."""
    pk, _sk = await _seed_keys(client)
    pk_prefix = pk[:14]

    resp = await client.delete(
        f"/admin/api-keys/{pk_prefix}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["keyPrefix"] == pk_prefix
    assert data["revokedAt"] is not None
    assert data["keyType"] == "publishable"


async def test_revoke_nonexistent_prefix_returns_404(client):
    """DELETE /admin/api-keys/{prefix} returns 404 for unknown prefix."""
    resp = await client.delete(
        "/admin/api-keys/pk_live_XXXXXX",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 404


async def test_revoked_key_returns_401_on_subsequent_use(client):
    """After revoking a secret key, requests using it get 401."""
    _pk, sk = await _seed_keys(client)
    sk_prefix = sk[:14]

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={"Authorization": f"Bearer {sk}"},
    )
    assert resp.status_code == 200

    await client.delete(
        f"/admin/api-keys/{sk_prefix}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={"Authorization": f"Bearer {sk}"},
    )
    assert resp.status_code == 401


async def test_revoking_one_key_does_not_affect_the_other(client):
    """Revoking a secret key does not affect the publishable key from the same pair."""
    pk, sk = await _seed_keys(client)
    sk_prefix = sk[:14]

    await client.delete(
        f"/admin/api-keys/{sk_prefix}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}},
        headers={
            "Authorization": f"Bearer {pk}",
            "Origin": "https://allowed.com",
        },
    )
    assert resp.status_code == 200
