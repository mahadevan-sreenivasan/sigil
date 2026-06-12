"""Tests for GDPR erasure and data retention pruning (Issue #11)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from sigil_server.retention import prune_expired_data


SIGNALS_A = {
    "canvas": "canvas_a",
    "webglRenderer": "webgl_a",
    "audioHash": "audio_a",
    "fonts": "fonts_a",
    "screenResolution": "1920x1080",
    "platform": "Win32",
}


async def _seed_visitor(client, headers, *, signals=None, visitor_id=None, account_id=None, ip="1.2.3.4"):
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


# ── DELETE /visitors/{visitorId} ─────────────────────────────────


@pytest.mark.asyncio
async def test_delete_visitor_removes_all_data_and_returns_counts(client, sk_auth_headers):
    """Seed a visitor with signal sets, an account binding, and geolocation,
    then DELETE and verify response includes correct counts."""
    first = await _seed_visitor(client, sk_auth_headers, account_id="acct_del", ip="1.2.3.4")
    vid = first["visitorId"]

    await _seed_visitor(client, sk_auth_headers, visitor_id=vid, account_id="acct_del", ip="5.6.7.8")

    resp = await client.delete(f"/visitors/{vid}", headers=sk_auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["visitorId"] == vid
    assert data["deleted"] is True
    assert data["recordsRemoved"]["signalSets"] == 2
    assert data["recordsRemoved"]["accountBindings"] == 1
    assert data["recordsRemoved"]["geolocations"] == 2


@pytest.mark.asyncio
async def test_delete_visitor_returns_404_for_unknown(client, sk_auth_headers):
    resp = await client.delete("/visitors/vis_nonexistent", headers=sk_auth_headers)
    assert resp.status_code == 404
    assert "Visitor not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_visitor_rejects_publishable_key(client, api_keys):
    pk, _sk = api_keys
    resp = await client.delete("/visitors/vis_any", headers={"Authorization": f"Bearer {pk}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_visitor_rejects_missing_auth(client):
    resp = await client.delete("/visitors/vis_any")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_visitor_cascades_to_all_related_tables(client, engine, sk_auth_headers):
    """After DELETE, signal_sets, account_bindings, and geolocation_history
    should contain zero rows for the deleted visitor."""
    first = await _seed_visitor(client, sk_auth_headers, account_id="acct_cascade", ip="1.2.3.4")
    vid = first["visitorId"]
    await _seed_visitor(client, sk_auth_headers, visitor_id=vid, account_id="acct_cascade", ip="5.6.7.8")

    resp = await client.delete(f"/visitors/{vid}", headers=sk_auth_headers)
    assert resp.status_code == 200

    async with engine.connect() as conn:
        vis = await conn.execute(text("SELECT COUNT(*) FROM visitors WHERE visitor_id = :vid"), {"vid": vid})
        assert vis.scalar() == 0

        sigs = await conn.execute(text("SELECT COUNT(*) FROM signal_sets WHERE visitor_id = :vid"), {"vid": vid})
        assert sigs.scalar() == 0

        binds = await conn.execute(text("SELECT COUNT(*) FROM account_bindings WHERE visitor_id = :vid"), {"vid": vid})
        assert binds.scalar() == 0

        geos = await conn.execute(text("SELECT COUNT(*) FROM geolocation_history WHERE visitor_id = :vid"), {"vid": vid})
        assert geos.scalar() == 0


# ── Data retention pruning ───────────────────────────────────────


@pytest.mark.asyncio
async def test_prune_deletes_old_signal_sets_keeps_fresh(client, engine, sk_auth_headers):
    """Signal sets older than retention_days are pruned; recent ones survive."""
    data = await _seed_visitor(client, sk_auth_headers, ip="1.2.3.4")
    vid = data["visitorId"]

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO signal_sets (visitor_id, canvas_hash, captured_at) "
                "VALUES (:vid, 'old_canvas', datetime('now', '-200 days'))"
            ),
            {"vid": vid},
        )

    result = await prune_expired_data(engine, retention_days=180)

    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT COUNT(*) FROM signal_sets WHERE visitor_id = :vid"),
            {"vid": vid},
        )
        assert rows.scalar() == 1, "Only the fresh signal set should remain"

    assert result["signal_sets"] >= 1


@pytest.mark.asyncio
async def test_prune_deletes_old_geolocations_keeps_fresh(client, engine, sk_auth_headers):
    """Geolocation entries older than retention_days are pruned; recent ones survive."""
    data = await _seed_visitor(client, sk_auth_headers, account_id="acct_geo_prune", ip="1.2.3.4")
    vid = data["visitorId"]

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO geolocation_history "
                "(visitor_id, account_id, ip_address, country, captured_at) "
                "VALUES (:vid, 'acct_geo_prune', '1.2.3.4', 'OLD', datetime('now', '-200 days'))"
            ),
            {"vid": vid},
        )

    result = await prune_expired_data(engine, retention_days=180)

    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT COUNT(*) FROM geolocation_history WHERE visitor_id = :vid"),
            {"vid": vid},
        )
        assert rows.scalar() == 1, "Only the fresh geolocation should remain"

    assert result["geolocations"] >= 1


@pytest.mark.asyncio
async def test_prune_removes_orphaned_visitors(engine):
    """A visitor with no signal sets and no bindings is removed after pruning."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO visitors (visitor_id) VALUES ('vis_orphan')")
        )

    result = await prune_expired_data(engine, retention_days=180)

    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT COUNT(*) FROM visitors WHERE visitor_id = 'vis_orphan'")
        )
        assert row.scalar() == 0

    assert result["visitors"] >= 1


@pytest.mark.asyncio
async def test_prune_keeps_visitor_with_remaining_bindings(engine):
    """A visitor whose signal sets are all expired but still has an account
    binding should NOT be deleted."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO visitors (visitor_id) VALUES ('vis_bound')")
        )
        await conn.execute(
            text(
                "INSERT INTO signal_sets (visitor_id, canvas_hash, captured_at) "
                "VALUES ('vis_bound', 'old', datetime('now', '-200 days'))"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO account_bindings (visitor_id, account_id) "
                "VALUES ('vis_bound', 'acct_keep')"
            )
        )

    result = await prune_expired_data(engine, retention_days=180)
    assert result["signal_sets"] >= 1

    async with engine.connect() as conn:
        vis = await conn.execute(
            text("SELECT COUNT(*) FROM visitors WHERE visitor_id = 'vis_bound'")
        )
        assert vis.scalar() == 1, "Visitor with binding should be kept"

        sigs = await conn.execute(
            text("SELECT COUNT(*) FROM signal_sets WHERE visitor_id = 'vis_bound'")
        )
        assert sigs.scalar() == 0, "Old signal sets should still be pruned"


@pytest.mark.asyncio
async def test_prune_does_not_delete_account_bindings(engine):
    """Account bindings are retained indefinitely — pruning must never touch them."""
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO visitors (visitor_id) VALUES ('vis_binding_safe')")
        )
        await conn.execute(
            text(
                "INSERT INTO account_bindings "
                "(visitor_id, account_id, first_seen_at, last_seen_at) "
                "VALUES ('vis_binding_safe', 'acct_old', "
                "datetime('now', '-400 days'), datetime('now', '-400 days'))"
            )
        )

    await prune_expired_data(engine, retention_days=180)

    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT COUNT(*) FROM account_bindings "
                "WHERE visitor_id = 'vis_binding_safe'"
            )
        )
        assert row.scalar() == 1, "Account bindings must never be pruned"
