"""Integration tests for similarity scoring (candidate filtering + scoring + identify)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text


FULL_SIGNALS = {
    "canvas": "canvas_SHARED",
    "webglRenderer": "NVIDIA GTX 1080",
    "audioHash": "audio_abc",
    "fonts": "font_abc",
    "screenResolution": "1920x1080",
    "platform": "Win32",
    "timezone": "Asia/Kolkata",
    "hardwareConcurrency": "8",
    "deviceMemory": "16",
    "touchSupport": "false",
    "userAgent": "Mozilla/5.0",
}


async def _seed_visitor(engine, visitor_id: str, signals: dict) -> None:
    """Seed a visitor + signal_set directly into the DB."""
    indexed = {
        "canvas": "canvas_hash",
        "webglRenderer": "webgl_renderer",
        "audioHash": "audio_hash",
        "fonts": "font_hash",
    }
    extra = {k: v for k, v in signals.items() if k not in indexed}
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT OR IGNORE INTO visitors (visitor_id) VALUES (:vid)"),
            {"vid": visitor_id},
        )
        await conn.execute(
            text(
                "INSERT INTO signal_sets "
                "(visitor_id, canvas_hash, webgl_renderer, audio_hash, font_hash, signals_extra) "
                "VALUES (:vid, :canvas, :webgl, :audio, :font, :extra)"
            ),
            {
                "vid": visitor_id,
                "canvas": signals.get("canvas"),
                "webgl": signals.get("webglRenderer"),
                "audio": signals.get("audioHash"),
                "font": signals.get("fonts"),
                "extra": json.dumps(extra),
            },
        )


class TestCandidateFiltering:
    async def test_finds_candidate_with_matching_canvas_hash(self, engine):
        from sigil_server.scoring import find_similar_visitors, DEFAULT_WEIGHTS

        await _seed_visitor(engine, "vis_existing", {
            **FULL_SIGNALS,
            "canvas": "canvas_SHARED",
        })

        incoming = {**FULL_SIGNALS, "canvas": "canvas_SHARED"}
        results = await find_similar_visitors(
            engine, "vis_new", incoming, DEFAULT_WEIGHTS,
            threshold=0.0, max_results=10,
        )

        assert len(results) == 1
        assert results[0]["visitorId"] == "vis_existing"

    async def test_no_candidates_when_no_high_entropy_signals_match(self, engine):
        from sigil_server.scoring import find_similar_visitors, DEFAULT_WEIGHTS

        await _seed_visitor(engine, "vis_existing", FULL_SIGNALS)

        incoming = {
            **FULL_SIGNALS,
            "canvas": "totally_different",
            "webglRenderer": "totally_different",
            "audioHash": "totally_different",
            "fonts": "totally_different",
        }
        results = await find_similar_visitors(
            engine, "vis_new", incoming, DEFAULT_WEIGHTS,
            threshold=0.0, max_results=10,
        )

        assert len(results) == 0


class TestIdentifyWithSimilarVisitors:
    async def test_identify_returns_similar_visitors(self, client, engine, sk_auth_headers):
        await _seed_visitor(engine, "vis_existing", FULL_SIGNALS)

        resp = await client.post(
            "/identify",
            json={"signals": FULL_SIGNALS},
            headers=sk_auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        similar = data["similarVisitors"]
        assert len(similar) >= 1

        entry = similar[0]
        assert entry["visitorId"] == "vis_existing"
        assert entry["similarityScore"] > 0.4
        assert "lastSeenAt" in entry
        assert isinstance(entry["matchingSignals"], list)
        assert isinstance(entry["mismatchedSignals"], list)

    async def test_threshold_filters_low_scores(self, client, engine, sk_auth_headers):
        """Seed a visitor that only shares one low-weight signal → below threshold."""
        await _seed_visitor(engine, "vis_lowscore", {
            "canvas": "unique_canvas",
            "webglRenderer": "unique_webgl",
            "audioHash": "unique_audio",
            "fonts": "unique_font",
            "screenResolution": "1920x1080",
            "platform": "Linux",
            "timezone": "America/New_York",
            "hardwareConcurrency": "2",
            "deviceMemory": "4",
            "touchSupport": "true",
            "userAgent": "curl/7.0",
        })

        incoming = {
            **FULL_SIGNALS,
            "canvas": "unique_canvas",
        }
        resp = await client.post(
            "/identify",
            json={"signals": incoming},
            headers=sk_auth_headers,
        )

        data = resp.json()
        for sv in data["similarVisitors"]:
            assert sv["similarityScore"] >= 0.4

    async def test_max_results_cap(self, client, engine, sk_auth_headers):
        for i in range(15):
            await _seed_visitor(engine, f"vis_bulk_{i}", {
                **FULL_SIGNALS,
                "userAgent": f"Agent/{i}",
            })

        resp = await client.post(
            "/identify",
            json={"signals": FULL_SIGNALS},
            headers=sk_auth_headers,
        )

        data = resp.json()
        assert len(data["similarVisitors"]) <= 10
