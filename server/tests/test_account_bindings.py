from __future__ import annotations

import pytest
from sqlalchemy import text


async def test_account_bindings_table_created_by_migration(engine):
    """Migration 003 creates account_bindings with expected columns."""
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='account_bindings'")
        )
        assert row.first() is not None, "account_bindings table should exist after migrations"


async def test_identify_with_account_id_creates_observed_binding(
    client, engine, sk_auth_headers,
):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    assert resp.status_code == 200
    visitor_id = resp.json()["visitorId"]

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT status, visitor_id, account_id "
                "FROM account_bindings "
                "WHERE visitor_id = :vid AND account_id = :aid"
            ),
            {"vid": visitor_id, "aid": "acct_1"},
        )
        binding = row.first()

    assert binding is not None, "binding should be created"
    assert binding[0] == "observed"


async def test_repeated_identify_updates_last_seen_not_status(
    client, engine, sk_auth_headers,
):
    resp1 = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    visitor_id = resp1.json()["visitorId"]

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT first_seen_at, last_seen_at FROM account_bindings "
                "WHERE visitor_id = :vid AND account_id = :aid"
            ),
            {"vid": visitor_id, "aid": "acct_1"},
        )
        first_binding = row.first()
    first_seen_original = first_binding[0]
    last_seen_original = first_binding[1]

    await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "visitorId": visitor_id, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT status, first_seen_at, last_seen_at FROM account_bindings "
                "WHERE visitor_id = :vid AND account_id = :aid"
            ),
            {"vid": visitor_id, "aid": "acct_1"},
        )
        updated = row.first()

    assert updated[0] == "observed", "status should remain observed"
    assert updated[1] == first_seen_original, "first_seen_at should not change"
    assert updated[2] >= last_seen_original, "last_seen_at should be updated"


async def test_verify_promotes_observed_to_verified(client, engine, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    visitor_id = resp.json()["visitorId"]

    verify_resp = await client.post(
        f"/accounts/acct_1/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["bindingStatus"] == "verified"
    assert data["accountId"] == "acct_1"
    assert data["visitorId"] == visitor_id
    assert "verifiedAt" in data

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT status, verified_at FROM account_bindings "
                "WHERE visitor_id = :vid AND account_id = :aid"
            ),
            {"vid": visitor_id, "aid": "acct_1"},
        )
        binding = row.first()

    assert binding[0] == "verified"
    assert binding[1] is not None


async def test_verify_returns_404_when_no_binding(client, sk_auth_headers):
    resp = await client.post(
        "/accounts/acct_999/visitors/vis_nonexistent/verify",
        headers=sk_auth_headers,
    )
    assert resp.status_code == 404


async def test_revoke_demotes_verified_to_observed(client, engine, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    visitor_id = resp.json()["visitorId"]

    await client.post(
        f"/accounts/acct_1/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )

    revoke_resp = await client.delete(
        f"/accounts/acct_1/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )
    assert revoke_resp.status_code == 200
    data = revoke_resp.json()
    assert data["bindingStatus"] == "observed"
    assert data["accountId"] == "acct_1"
    assert data["visitorId"] == visitor_id
    assert "revokedAt" in data

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT status, verified_at FROM account_bindings "
                "WHERE visitor_id = :vid AND account_id = :aid"
            ),
            {"vid": visitor_id, "aid": "acct_1"},
        )
        binding = row.first()

    assert binding[0] == "observed"
    assert binding[1] is None


async def test_revoke_returns_404_when_no_binding(client, sk_auth_headers):
    resp = await client.delete(
        "/accounts/acct_999/visitors/vis_nonexistent/verify",
        headers=sk_auth_headers,
    )
    assert resp.status_code == 404


async def test_is_known_visitor_true_for_verified_binding(client, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    visitor_id = resp.json()["visitorId"]

    await client.post(
        f"/accounts/acct_1/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )

    resp2 = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "visitorId": visitor_id, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    data = resp2.json()
    assert data["accountHistory"]["isKnownVisitorForAccount"] is True


async def test_is_known_visitor_false_for_observed_binding(client, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_1"},
        headers=sk_auth_headers,
    )
    data = resp.json()
    assert data["accountHistory"]["isKnownVisitorForAccount"] is False


async def test_full_lifecycle_observed_verify_revoke_reverify(
    client, engine, sk_auth_headers,
):
    """Full lifecycle: observed → verify → revoke → re-verify."""
    # Step 1: identify creates observed binding
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc"}, "accountId": "acct_lifecycle"},
        headers=sk_auth_headers,
    )
    assert resp.status_code == 200
    visitor_id = resp.json()["visitorId"]
    assert resp.json()["accountHistory"]["isKnownVisitorForAccount"] is False

    # Step 2: verify promotes to verified
    verify_resp = await client.post(
        f"/accounts/acct_lifecycle/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["bindingStatus"] == "verified"

    # Step 3: identify now returns isKnownVisitorForAccount=True
    resp2 = await client.post(
        "/identify",
        json={
            "signals": {"canvas": "abc"},
            "visitorId": visitor_id,
            "accountId": "acct_lifecycle",
        },
        headers=sk_auth_headers,
    )
    assert resp2.json()["accountHistory"]["isKnownVisitorForAccount"] is True

    # Step 4: revoke demotes back to observed
    revoke_resp = await client.delete(
        f"/accounts/acct_lifecycle/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["bindingStatus"] == "observed"

    # Step 5: identify now returns isKnownVisitorForAccount=False
    resp3 = await client.post(
        "/identify",
        json={
            "signals": {"canvas": "abc"},
            "visitorId": visitor_id,
            "accountId": "acct_lifecycle",
        },
        headers=sk_auth_headers,
    )
    assert resp3.json()["accountHistory"]["isKnownVisitorForAccount"] is False

    # Step 6: re-verify
    reverify_resp = await client.post(
        f"/accounts/acct_lifecycle/visitors/{visitor_id}/verify",
        headers=sk_auth_headers,
    )
    assert reverify_resp.status_code == 200
    assert reverify_resp.json()["bindingStatus"] == "verified"

    # Step 7: confirm re-verified
    resp4 = await client.post(
        "/identify",
        json={
            "signals": {"canvas": "abc"},
            "visitorId": visitor_id,
            "accountId": "acct_lifecycle",
        },
        headers=sk_auth_headers,
    )
    assert resp4.json()["accountHistory"]["isKnownVisitorForAccount"] is True
