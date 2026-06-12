"""Tests for investigation query endpoints (Issue #10)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


SIGNALS_A = {
    "canvas": "canvas_a",
    "webglRenderer": "webgl_a",
    "audioHash": "audio_a",
    "fonts": "fonts_a",
    "screenResolution": "1920x1080",
    "platform": "Win32",
}

SIGNALS_B = {
    "canvas": "canvas_b",
    "webglRenderer": "webgl_b",
    "audioHash": "audio_b",
    "fonts": "fonts_b",
    "screenResolution": "1440x900",
    "platform": "MacIntel",
}


async def _seed_visitor(client, headers, *, signals=None, visitor_id=None, account_id=None, ip="1.2.3.4"):
    """Create a visitor via POST /identify and return the response data."""
    body: dict = {"signals": signals or SIGNALS_A}
    if visitor_id:
        body["visitorId"] = visitor_id
    if account_id:
        body["accountId"] = account_id
    resp = await client.post(
        "/identify",
        json=body,
        headers={**headers, "X-Forwarded-For": ip},
    )
    assert resp.status_code == 200
    return resp.json()


# ── GET /visitors/{visitorId} ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_visitor_detail_returns_bindings_and_signals(client, sk_auth_headers):
    """Seed a visitor with an account binding and two signal sets, then query detail."""
    first = await _seed_visitor(client, sk_auth_headers, account_id="acct_1", ip="1.2.3.4")
    vid = first["visitorId"]

    await _seed_visitor(
        client, sk_auth_headers,
        visitor_id=vid, account_id="acct_1", signals=SIGNALS_B, ip="5.6.7.8",
    )

    resp = await client.get(f"/visitors/{vid}", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["visitorId"] == vid
    assert "firstSeenAt" in data
    assert "lastSeenAt" in data

    bindings = data["accountBindings"]
    assert len(bindings) == 1
    assert bindings[0]["accountId"] == "acct_1"
    assert bindings[0]["status"] in ("observed", "verified")
    assert "firstSeenAt" in bindings[0]
    assert "lastSeenAt" in bindings[0]

    signal_sets = data["recentSignalSets"]
    assert len(signal_sets) >= 2
    for ss in signal_sets:
        assert "capturedAt" in ss
        assert "signals" in ss
        assert "geolocation" in ss


@pytest.mark.asyncio
async def test_get_visitor_returns_404_for_unknown_visitor(client, sk_auth_headers):
    resp = await client.get("/visitors/vis_nonexistent", headers=sk_auth_headers)
    assert resp.status_code == 404
    assert "Visitor not found" in resp.json()["detail"]


# ── Auth tests for all investigation endpoints ───────────────────


@pytest.mark.asyncio
async def test_investigation_endpoints_reject_publishable_key(client, api_keys):
    pk, _sk = api_keys
    pk_headers = {"Authorization": f"Bearer {pk}"}

    endpoints = [
        "/visitors/vis_any",
        "/accounts/acct_any/visitors",
        "/accounts/acct_any/geolocations",
        "/ip/1.2.3.4/visitors",
    ]
    for path in endpoints:
        resp = await client.get(path, headers=pk_headers)
        assert resp.status_code == 403, f"Expected 403 for {path}, got {resp.status_code}"


@pytest.mark.asyncio
async def test_investigation_endpoints_reject_missing_auth(client):
    endpoints = [
        "/visitors/vis_any",
        "/accounts/acct_any/visitors",
        "/accounts/acct_any/geolocations",
        "/ip/1.2.3.4/visitors",
    ]
    for path in endpoints:
        resp = await client.get(path)
        assert resp.status_code == 401, f"Expected 401 for {path}, got {resp.status_code}"


# ── GET /accounts/{accountId}/visitors ───────────────────────────


@pytest.mark.asyncio
async def test_get_account_visitors_returns_devices_with_binding_and_geo(client, sk_auth_headers):
    """Two different visitors bound to the same account, each from different IPs."""
    first = await _seed_visitor(client, sk_auth_headers, account_id="acct_100", ip="1.2.3.4")
    vid1 = first["visitorId"]

    second = await _seed_visitor(client, sk_auth_headers, account_id="acct_100", ip="5.6.7.8")
    vid2 = second["visitorId"]

    resp = await client.get("/accounts/acct_100/visitors", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["accountId"] == "acct_100"
    visitors = data["visitors"]
    assert len(visitors) == 2

    vids = {v["visitorId"] for v in visitors}
    assert vid1 in vids
    assert vid2 in vids

    for v in visitors:
        assert v["bindingStatus"] in ("observed", "verified")
        assert "firstSeenAt" in v
        assert "lastSeenAt" in v
        assert "lastGeolocation" in v
        geo = v["lastGeolocation"]
        assert "country" in geo
        assert "city" in geo


@pytest.mark.asyncio
async def test_get_account_visitors_returns_empty_for_unknown_account(client, sk_auth_headers):
    resp = await client.get("/accounts/acct_unknown/visitors", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accountId"] == "acct_unknown"
    assert data["visitors"] == []


# ── GET /accounts/{accountId}/geolocations ───────────────────────


@pytest.mark.asyncio
async def test_get_account_geolocations_filtered_by_days(client, engine, sk_auth_headers):
    """Seed geolocations, back-date one beyond the window, verify filtering."""
    data = await _seed_visitor(client, sk_auth_headers, account_id="acct_geo", ip="1.2.3.4")
    vid = data["visitorId"]

    await _seed_visitor(client, sk_auth_headers, visitor_id=vid, account_id="acct_geo", ip="5.6.7.8")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE geolocation_history "
                "SET captured_at = datetime('now', '-60 days') "
                "WHERE account_id = 'acct_geo' AND ip_address = '1.2.3.4'"
            ),
        )

    resp = await client.get(
        "/accounts/acct_geo/geolocations",
        params={"days": 30},
        headers=sk_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accountId"] == "acct_geo"

    geos = data["geolocations"]
    assert len(geos) == 1
    assert geos[0]["ip"] == "5.6.7.8"
    assert geos[0]["country"] == "GB"
    assert geos[0]["city"] == "London"
    assert "capturedAt" in geos[0]
    assert "visitorId" in geos[0]
    assert "latitude" in geos[0]
    assert "longitude" in geos[0]


@pytest.mark.asyncio
async def test_get_account_geolocations_defaults_to_30_days(client, sk_auth_headers):
    """When days param is omitted, default is 30 days."""
    await _seed_visitor(client, sk_auth_headers, account_id="acct_default", ip="1.2.3.4")

    resp = await client.get("/accounts/acct_default/geolocations", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accountId"] == "acct_default"
    assert len(data["geolocations"]) == 1


@pytest.mark.asyncio
async def test_get_account_geolocations_empty_for_unknown_account(client, sk_auth_headers):
    resp = await client.get("/accounts/acct_nope/geolocations", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accountId"] == "acct_nope"
    assert data["geolocations"] == []


# ── GET /ip/{ipAddress}/visitors ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_ip_visitors_returns_visitors_with_accounts_and_counts(client, sk_auth_headers):
    """Two visitors from the same IP, one with an account binding."""
    first = await _seed_visitor(client, sk_auth_headers, account_id="acct_ip1", ip="9.10.11.12")
    vid1 = first["visitorId"]

    await _seed_visitor(client, sk_auth_headers, visitor_id=vid1, account_id="acct_ip1", ip="9.10.11.12")

    second = await _seed_visitor(client, sk_auth_headers, ip="9.10.11.12")
    vid2 = second["visitorId"]

    resp = await client.get("/ip/9.10.11.12/visitors", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ip"] == "9.10.11.12"
    visitors = data["visitors"]
    assert len(visitors) == 2

    by_vid = {v["visitorId"]: v for v in visitors}

    v1 = by_vid[vid1]
    assert "acct_ip1" in v1["accountIds"]
    assert v1["requestCount"] == 2
    assert "firstSeenFromIp" in v1
    assert "lastSeenFromIp" in v1

    v2 = by_vid[vid2]
    assert v2["accountIds"] == []
    assert v2["requestCount"] == 1


@pytest.mark.asyncio
async def test_get_ip_visitors_returns_empty_for_unknown_ip(client, sk_auth_headers):
    resp = await client.get("/ip/99.99.99.99/visitors", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ip"] == "99.99.99.99"
    assert data["visitors"] == []
