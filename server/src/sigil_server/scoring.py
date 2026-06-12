"""Similarity scoring: pure scoring function and candidate-filtering query."""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

DEFAULT_WEIGHTS: dict[str, float] = {
    "canvas": 0.20,
    "webglRenderer": 0.15,
    "audioHash": 0.15,
    "fontHash": 0.15,
    "screenResolution": 0.08,
    "platform": 0.07,
    "timezone": 0.07,
    "hardwareConcurrency": 0.05,
    "deviceMemory": 0.04,
    "touchSupport": 0.02,
    "userAgent": 0.02,
}


def compute_similarity_score(
    signals_a: dict[str, str | None],
    signals_b: dict[str, str | None],
    weights: dict[str, float],
) -> tuple[float, list[str], list[str]]:
    """Compare two signal sets and return (score, matching_signals, mismatched_signals).

    Score is the weighted sum of matches, normalized to [0, 1].
    Signals present in the weight map but absent from *both* sets are skipped
    (they don't penalise or reward the score).
    A signal absent from only *one* set counts as a mismatch.
    """
    score = 0.0
    matching: list[str] = []
    mismatched: list[str] = []
    active_weight = 0.0

    for signal, weight in weights.items():
        val_a = signals_a.get(signal)
        val_b = signals_b.get(signal)

        if val_a is None and val_b is None:
            continue

        active_weight += weight

        if val_a is not None and val_b is not None and str(val_a) == str(val_b):
            score += weight
            matching.append(signal)
        else:
            mismatched.append(signal)

    if active_weight == 0.0:
        return 0.0, matching, mismatched

    normalized = score / active_weight
    return normalized, matching, mismatched


# Maps weight-key names to the DB indexed columns and the request signal names
_INDEXED_SIGNAL_TO_COL = {
    "canvas": "canvas_hash",
    "webglRenderer": "webgl_renderer",
    "audioHash": "audio_hash",
    "fontHash": "font_hash",
}

_EXTRA_SIGNAL_KEYS = [
    "screenResolution", "platform", "timezone",
    "hardwareConcurrency", "deviceMemory", "touchSupport", "userAgent",
]


def _row_to_signal_dict(row) -> dict[str, str | None]:
    """Convert a DB row (canvas_hash, webgl_renderer, ..., signals_extra) to a flat dict
    keyed by the weight-map signal names."""
    canvas_hash, webgl_renderer, audio_hash, font_hash, extra_raw = row
    signals: dict[str, str | None] = {
        "canvas": canvas_hash,
        "webglRenderer": webgl_renderer,
        "audioHash": audio_hash,
        "fontHash": font_hash,
    }
    extra = json.loads(extra_raw) if isinstance(extra_raw, str) else (extra_raw or {})
    # fonts → fontHash mapping: the request key is "fonts" but weight key is "fontHash"
    for key in _EXTRA_SIGNAL_KEYS:
        val = extra.get(key)
        if val is not None:
            signals[key] = str(val)
    return signals


def _incoming_to_scoring_dict(incoming: dict) -> dict[str, str | None]:
    """Normalise incoming request signals to weight-map keys."""
    result: dict[str, str | None] = {}
    result["canvas"] = incoming.get("canvas")
    result["webglRenderer"] = incoming.get("webglRenderer")
    result["audioHash"] = incoming.get("audioHash")
    result["fontHash"] = incoming.get("fonts")
    for key in _EXTRA_SIGNAL_KEYS:
        val = incoming.get(key)
        if val is not None:
            result[key] = str(val)
    return result


_CANDIDATE_SQL = """
SELECT DISTINCT ss.visitor_id, v.last_seen_at,
       ss.canvas_hash, ss.webgl_renderer, ss.audio_hash, ss.font_hash,
       ss.signals_extra
FROM signal_sets ss
JOIN visitors v ON v.visitor_id = ss.visitor_id
WHERE ss.visitor_id != :current_vid
  AND (
      ss.canvas_hash  = :canvas
   OR ss.webgl_renderer = :webgl
   OR ss.audio_hash   = :audio
   OR ss.font_hash    = :font
  )
"""


async def find_similar_visitors(
    engine: AsyncEngine,
    current_visitor_id: str,
    incoming_signals: dict,
    weights: dict[str, float],
    threshold: float,
    max_results: int,
) -> list[dict]:
    """Find and score similar visitors from the DB.

    1. Query candidates sharing at least one high-entropy indexed signal.
    2. Score each candidate against the incoming signals.
    3. Filter by threshold, sort descending, cap at max_results.
    """
    incoming_scoring = _incoming_to_scoring_dict(incoming_signals)

    canvas = incoming_signals.get("canvas")
    webgl = incoming_signals.get("webglRenderer")
    audio = incoming_signals.get("audioHash")
    font = incoming_signals.get("fonts")

    async with engine.connect() as conn:
        rows = await conn.execute(
            text(_CANDIDATE_SQL),
            {
                "current_vid": current_visitor_id,
                "canvas": canvas,
                "webgl": webgl,
                "audio": audio,
                "font": font,
            },
        )
        candidates = rows.fetchall()

    scored: list[dict] = []
    seen_visitors: set[str] = set()

    for row in candidates:
        vid = row[0]
        if vid in seen_visitors:
            continue
        seen_visitors.add(vid)

        last_seen_at = row[1]
        stored_signals = _row_to_signal_dict(row[2:])

        score, matching, mismatched = compute_similarity_score(
            incoming_scoring, stored_signals, weights,
        )

        if score < threshold:
            continue

        scored.append({
            "visitorId": vid,
            "similarityScore": round(score, 4),
            "lastSeenAt": str(last_seen_at) if last_seen_at else None,
            "matchingSignals": matching,
            "mismatchedSignals": mismatched,
        })

    scored.sort(key=lambda x: x["similarityScore"], reverse=True)
    return scored[:max_results]
