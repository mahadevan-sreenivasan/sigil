from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .db import create_engine, run_migrations
from .models import IdentifyRequest, IdentifyResponse


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

            if is_new:
                await conn.execute(
                    text("INSERT INTO visitors (visitor_id) VALUES (:vid)"),
                    {"vid": visitor_id},
                )

            signals_extra = {
                k: v
                for k, v in body.signals.items()
                if k not in ("canvas", "webglRenderer", "audioHash", "fonts")
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
            isNewVisitor=is_new,
            serverReachable=True,
        )


app = create_app()
