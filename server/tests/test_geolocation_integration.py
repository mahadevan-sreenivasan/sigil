"""Integration tests for geolocation storage, impossible travel, and IP velocity."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigil_server.db import run_migrations


async def test_migration_creates_geolocation_history_table():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        await run_migrations(engine)
        async with engine.connect() as conn:
            tables = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            table_names = [row[0] for row in tables.fetchall()]
        assert "geolocation_history" in table_names
    finally:
        await engine.dispose()


async def test_identify_stores_geolocation_and_returns_it(client, engine, sk_auth_headers):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "geo_test"}},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )
    data = resp.json()

    assert data["geolocation"]["ip"] == "1.2.3.4"
    assert data["geolocation"]["country"] == "IN"
    assert data["geolocation"]["city"] == "Mumbai"
    assert data["geolocation"]["latitude"] == pytest.approx(19.076, abs=0.01)
    assert data["geolocation"]["longitude"] == pytest.approx(72.8777, abs=0.01)

    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT ip_address, country, city FROM geolocation_history LIMIT 1")
        )
        geo_row = row.first()
    assert geo_row is not None
    assert geo_row[0] == "1.2.3.4"
    assert geo_row[1] == "IN"
    assert geo_row[2] == "Mumbai"


async def test_impossible_travel_detected(client, engine, sk_auth_headers):
    """Two requests from Mumbai and London within seconds → impossible travel detected."""
    await client.post(
        "/identify",
        json={"signals": {"canvas": "it1"}, "accountId": "acct_travel"},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "it2"}, "accountId": "acct_travel"},
        headers={**sk_auth_headers, "X-Forwarded-For": "5.6.7.8"},
    )
    data = resp.json()

    assert data["impossibleTravel"]["detected"] is True
    assert data["impossibleTravel"]["distanceKm"] > 7_000
    assert data["impossibleTravel"]["previousLocation"]["city"] == "Mumbai"
    assert data["impossibleTravel"]["previousLocation"]["country"] == "IN"
    assert data["impossibleTravel"]["previousSeenAt"] is not None


async def test_impossible_travel_not_detected_with_enough_time(
    client, engine, sk_auth_headers,
):
    """After backdating the first record by 24h, travel is plausible."""
    await client.post(
        "/identify",
        json={"signals": {"canvas": "slow1"}, "accountId": "acct_slow"},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE geolocation_history "
                "SET captured_at = datetime('now', '-24 hours') "
                "WHERE account_id = 'acct_slow'"
            )
        )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "slow2"}, "accountId": "acct_slow"},
        headers={**sk_auth_headers, "X-Forwarded-For": "5.6.7.8"},
    )
    data = resp.json()

    assert data["impossibleTravel"]["detected"] is False
    assert data["impossibleTravel"]["distanceKm"] > 7_000
    assert data["impossibleTravel"]["previousLocation"]["city"] == "Mumbai"


async def test_impossible_travel_not_computed_without_account_id(
    client, sk_auth_headers,
):
    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "no_acct_geo"}},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )
    data = resp.json()

    assert data["impossibleTravel"]["detected"] is False
    assert data["impossibleTravel"]["previousLocation"] is None
    assert data["impossibleTravel"]["previousSeenAt"] is None
    assert data["impossibleTravel"]["distanceKm"] is None


async def test_ip_distinct_accounts_last_1hr(client, engine, sk_auth_headers):
    """Two different accounts from the same IP → ipDistinctAccountsLast1Hr = 2."""
    await client.post(
        "/identify",
        json={"signals": {"canvas": "ip_v1"}, "accountId": "acct_A"},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )

    resp = await client.post(
        "/identify",
        json={"signals": {"canvas": "ip_v2"}, "accountId": "acct_B"},
        headers={**sk_auth_headers, "X-Forwarded-For": "1.2.3.4"},
    )
    data = resp.json()

    assert data["velocity"]["ipDistinctAccountsLast1Hr"] == 2
