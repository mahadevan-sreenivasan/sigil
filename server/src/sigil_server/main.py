from __future__ import annotations

import hashlib
import json
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .db import create_engine, run_migrations
from .models import IdentifyRequest, IdentifyResponse

TOP_STABLE_SIGNALS = ("canvas", "webglRenderer", "audioHash", "fonts")
INDEXED_SIGNAL_MAP = {
    "canvas": "canvas_hash",
    "webglRenderer": "webgl_renderer",
    "audioHash": "audio_hash",
    "fonts": "font_hash",
}


def _compute_fingerprint_id(signals: dict) -> str:
    parts = [str(signals.get(k, "")) for k in TOP_STABLE_SIGNALS]
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"fp_{digest}"


def _validate_signals(
    incoming: dict, stored_canvas: str | None, stored_webgl: str | None,
    stored_audio: str | None, stored_font: str | None,
) -> str:
    stored = {
        "canvas": stored_canvas,
        "webglRenderer": stored_webgl,
        "audioHash": stored_audio,
        "fonts": stored_font,
    }
    matches = 0
    total = 0
    for key in TOP_STABLE_SIGNALS:
        s = stored.get(key)
        i = incoming.get(key)
        if s is None and i is None:
            continue
        total += 1
        if s == i:
            matches += 1

    if total == 0:
        return "match"
    return "match" if matches >= (total / 2) else "mismatch"


def create_app(engine: AsyncEngine | None = None) -> FastAPI:
    owns_engine = engine is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal engine
        if engine is None:
            engine = create_engine(os.environ["DATABASE_URL"])
            await run_migrations(engine)
        app.state.engine = engine
        yield
        if owns_engine and engine is not None:
            await engine.dispose()

    app = FastAPI(title="Sigil Identification Server", lifespan=lifespan)
    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:
    @app.post("/identify", response_model=IdentifyResponse)
    async def identify(body: IdentifyRequest, request: Request) -> IdentifyResponse:
        engine: AsyncEngine = request.app.state.engine
        visitor_id = body.visitorId
        is_new = True
        signal_validation: str = "new"

        fingerprint_id = _compute_fingerprint_id(body.signals)

        if visitor_id is None:
            visitor_id = f"vis_{uuid.uuid4().hex[:12]}"

        async with engine.begin() as conn:
            if body.visitorId is not None:
                row = await conn.execute(
                    text("SELECT visitor_id FROM visitors WHERE visitor_id = :vid"),
                    {"vid": visitor_id},
                )
                if row.first() is not None:
                    is_new = False
                    await conn.execute(
                        text(
                            "UPDATE visitors SET last_seen_at = CURRENT_TIMESTAMP "
                            "WHERE visitor_id = :vid"
                        ),
                        {"vid": visitor_id},
                    )

                    latest = await conn.execute(
                        text(
                            "SELECT canvas_hash, webgl_renderer, audio_hash, font_hash "
                            "FROM signal_sets WHERE visitor_id = :vid "
                            "ORDER BY captured_at DESC LIMIT 1"
                        ),
                        {"vid": visitor_id},
                    )
                    stored_row = latest.first()
                    if stored_row is not None:
                        signal_validation = _validate_signals(
                            body.signals,
                            stored_row[0], stored_row[1],
                            stored_row[2], stored_row[3],
                        )
                    else:
                        signal_validation = "match"

            if is_new:
                await conn.execute(
                    text("INSERT INTO visitors (visitor_id) VALUES (:vid)"),
                    {"vid": visitor_id},
                )

            signals_extra = {
                k: v
                for k, v in body.signals.items()
                if k not in INDEXED_SIGNAL_MAP
            }
            await conn.execute(
                text(
                    "INSERT INTO signal_sets "
                    "(visitor_id, canvas_hash, webgl_renderer, audio_hash, font_hash, signals_extra) "
                    "VALUES (:vid, :canvas, :webgl, :audio, :font, :extra)"
                ),
                {
                    "vid": visitor_id,
                    "canvas": body.signals.get("canvas"),
                    "webgl": body.signals.get("webglRenderer"),
                    "audio": body.signals.get("audioHash"),
                    "font": body.signals.get("fonts"),
                    "extra": json.dumps(signals_extra),
                },
            )

        return IdentifyResponse(
            visitorId=visitor_id,
            fingerprintId=fingerprint_id,
            isNewVisitor=is_new,
            signalValidation=signal_validation,
            serverReachable=True,
        )


app = create_app()
