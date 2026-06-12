from __future__ import annotations

import pytest


FULL_SIGNALS = {
    "canvas": "canvas_hash_abc",
    "webglRenderer": "ANGLE (NVIDIA GeForce GTX 1080)",
    "webglVendor": "Google Inc. (NVIDIA)",
    "audioHash": "audio_hash_def",
    "fonts": "font_hash_ghi",
    "screenResolution": "1920x1080",
    "colorDepth": 24,
    "platform": "Win32",
    "hardwareConcurrency": 8,
    "deviceMemory": 16,
    "touchSupport": False,
    "maxTouchPoints": 0,
    "timezone": "Asia/Kolkata",
    "userAgent": "Mozilla/5.0 Test",
}


async def test_signal_validation_new_when_no_visitor_id(client, sk_auth_headers):
    """POST without visitorId should return signalValidation='new'."""
    response = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["signalValidation"] == "new"
    assert data["visitorId"].startswith("vis_")
    assert data["isNewVisitor"] is True


async def test_signal_validation_match_when_signals_consistent(client, sk_auth_headers):
    """POST with matching signals for an existing visitorId → 'match'."""
    first = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )
    visitor_id = first.json()["visitorId"]

    second = await client.post(
        "/identify",
        json={"signals": FULL_SIGNALS, "visitorId": visitor_id},
        headers=sk_auth_headers,
    )

    data = second.json()
    assert data["signalValidation"] == "match"
    assert data["visitorId"] == visitor_id
    assert data["isNewVisitor"] is False


async def test_signal_validation_mismatch_when_signals_diverge(client, sk_auth_headers):
    """POST with different top signals for an existing visitorId → 'mismatch'."""
    first = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )
    visitor_id = first.json()["visitorId"]

    different_signals = {
        **FULL_SIGNALS,
        "canvas": "totally_different_canvas",
        "webglRenderer": "Different Renderer",
        "audioHash": "different_audio",
        "fonts": "different_fonts",
    }
    second = await client.post(
        "/identify",
        json={"signals": different_signals, "visitorId": visitor_id},
        headers=sk_auth_headers,
    )

    data = second.json()
    assert data["signalValidation"] == "mismatch"
    assert data["visitorId"] == visitor_id


async def test_fingerprint_id_is_returned(client, sk_auth_headers):
    """Response should include a fingerprintId derived from top stable signals."""
    response = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )

    data = response.json()
    assert "fingerprintId" in data
    assert data["fingerprintId"].startswith("fp_")
    assert len(data["fingerprintId"]) > 3


async def test_fingerprint_id_is_deterministic(client, sk_auth_headers):
    """Same top signals should produce the same fingerprintId."""
    first = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )
    second = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )

    assert first.json()["fingerprintId"] == second.json()["fingerprintId"]


async def test_fingerprint_id_changes_with_different_signals(client, sk_auth_headers):
    """Different top signals should produce a different fingerprintId."""
    first = await client.post(
        "/identify", json={"signals": FULL_SIGNALS}, headers=sk_auth_headers,
    )

    different = {**FULL_SIGNALS, "canvas": "different_canvas"}
    second = await client.post(
        "/identify", json={"signals": different}, headers=sk_auth_headers,
    )

    assert first.json()["fingerprintId"] != second.json()["fingerprintId"]
