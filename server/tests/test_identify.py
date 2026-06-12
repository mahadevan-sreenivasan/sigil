from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_new_visitor_gets_vis_prefixed_id(client):
    response = await client.post("/identify", json={
        "signals": {"canvas": "abc123hash"},
    })

    assert response.status_code == 200
    data = response.json()
    assert data["visitorId"].startswith("vis_")
    assert data["isNewVisitor"] is True
    assert data["serverReachable"] is True


@pytest.mark.asyncio
async def test_returning_visitor_is_not_new_and_appends_signal_set(client, engine):
    first = await client.post("/identify", json={
        "signals": {"canvas": "hash_v1"},
    })
    visitor_id = first.json()["visitorId"]

    second = await client.post("/identify", json={
        "signals": {"canvas": "hash_v2"},
        "visitorId": visitor_id,
    })

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
