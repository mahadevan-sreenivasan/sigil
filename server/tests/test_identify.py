from __future__ import annotations

import pytest
from sqlalchemy import text


async def test_new_visitor_gets_vis_prefixed_id(client, sk_auth_headers):
    response = await client.post(
        "/identify",
        json={"signals": {"canvas": "abc123hash"}},
        headers=sk_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["visitorId"].startswith("vis_")
    assert data["isNewVisitor"] is True
    assert data["serverReachable"] is True
    assert data["signalValidation"] == "new"
    assert data["fingerprintId"].startswith("fp_")


async def test_returning_visitor_is_not_new_and_appends_signal_set(
    client, engine, sk_auth_headers,
):
    first = await client.post(
        "/identify",
        json={"signals": {"canvas": "hash_v1"}},
        headers=sk_auth_headers,
    )
    visitor_id = first.json()["visitorId"]

    second = await client.post(
        "/identify",
        json={"signals": {"canvas": "hash_v2"}, "visitorId": visitor_id},
        headers=sk_auth_headers,
    )

    data = second.json()
    assert data["visitorId"] == visitor_id
    assert data["isNewVisitor"] is False
    assert data["serverReachable"] is True

    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT COUNT(*) FROM signal_sets WHERE visitor_id = :vid"),
            {"vid": visitor_id},
        )
        assert row.scalar() == 2


async def test_velocity_visitor_requests_last_10_min(client, sk_auth_headers):
    first = await client.post(
        "/identify",
        json={"signals": {"canvas": "vel_test"}},
        headers=sk_auth_headers,
    )
    visitor_id = first.json()["visitorId"]

    second = await client.post(
        "/identify",
        json={"signals": {"canvas": "vel_test"}, "visitorId": visitor_id},
        headers=sk_auth_headers,
    )
    data = second.json()

    assert data["velocity"]["visitorRequestsLast10Min"] == 2


async def test_velocity_account_distinct_visitors_last_1hr(client, sk_auth_headers):
    account_id = "acct_shared"

    await client.post(
        "/identify",
        json={"signals": {"canvas": "dev_A"}, "accountId": account_id},
        headers=sk_auth_headers,
    )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "dev_B"}, "accountId": account_id},
        headers=sk_auth_headers,
    )
    data = resp.json()

    assert data["velocity"]["accountDistinctVisitorsLast1Hr"] == 2


async def test_velocity_null_when_no_account_id(client, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "no_acct"}},
        headers=sk_auth_headers,
    )
    data = resp.json()

    assert data["velocity"]["visitorRequestsLast10Min"] == 1
    assert data["velocity"]["accountDistinctVisitorsLast1Hr"] is None
    assert data["velocity"]["ipDistinctAccountsLast1Hr"] == 0


async def test_velocity_ip_distinct_accounts_wired_up(client, sk_auth_headers):
    """ipDistinctAccountsLast1Hr counts distinct accounts from the same IP via geolocation_history."""
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "ip_test"}, "accountId": "acct_ip"},
        headers=sk_auth_headers,
    )
    data = resp.json()

    assert data["velocity"]["ipDistinctAccountsLast1Hr"] == 1
