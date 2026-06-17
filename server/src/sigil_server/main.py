from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Query, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .db import create_engine, run_migrations
from .geolocation import (
    GeoResolver,
    check_impossible_travel,
    extract_client_ip,
)
from .models import (
    AccountHistory,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    Geolocation,
    IdentifyRequest,
    IdentifyResponse,
    ImpossibleTravel,
    PreviousLocation,
    SimilarVisitor,
    Velocity,
)
from .scoring import DEFAULT_WEIGHTS, find_similar_visitors
from .startup import build_geo_resolver, load_weights, validate_config, validate_env

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
        config_path = os.environ.get("SIGIL_CONFIG_PATH", "sigil-config.yaml")
        if engine is None:
            validate_env()
            validate_config(config_path)
            engine = create_engine(os.environ["DATABASE_URL"])
            await run_migrations(engine)
        app.state.engine = engine
        custom_weights = load_weights(config_path)
        app.state.scoring_weights = custom_weights if custom_weights else DEFAULT_WEIGHTS
        geo_resolver = build_geo_resolver()
        if geo_resolver is not None:
            app.state.geo_resolver = geo_resolver
        yield
        if owns_engine and engine is not None:
            await engine.dispose()

    app = FastAPI(title="Sigil Identification Server", lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    _register_routes(app)
    return app


_AUTH_EXEMPT_PATHS = {"/admin/api-keys", "/docs", "/openapi.json", "/health"}

_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key_hash: str) -> bool:
    """Return True if the request is within the rate limit, False if exceeded."""
    rps = int(os.environ.get("SIGIL_RATE_LIMIT_RPS", "20"))
    now = time.monotonic()
    window = _rate_limit_buckets[key_hash]
    cutoff = now - 1.0
    _rate_limit_buckets[key_hash] = [t for t in window if t > cutoff]
    if len(_rate_limit_buckets[key_hash]) >= rps:
        return False
    _rate_limit_buckets[key_hash].append(now)
    return True


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _AUTH_EXEMPT_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Missing or invalid Authorization header"}',
                status_code=401,
                media_type="application/json",
            )

        raw_key = auth_header[7:]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        engine: AsyncEngine = request.app.state.engine

        async with engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT key_type, allowed_origins, revoked_at "
                    "FROM api_keys WHERE key_hash = :h"
                ),
                {"h": key_hash},
            )
            key_row = row.first()

        if key_row is None:
            return Response(
                content='{"detail":"Invalid API key"}',
                status_code=401,
                media_type="application/json",
            )

        key_type, allowed_origins_raw, revoked_at = key_row
        if revoked_at is not None:
            return Response(
                content='{"detail":"API key has been revoked"}',
                status_code=401,
                media_type="application/json",
            )

        if key_type == "publishable" and request.url.path != "/identify":
            return Response(
                content='{"detail":"Publishable keys can only access POST /identify"}',
                status_code=403,
                media_type="application/json",
            )

        if key_type == "publishable" and request.url.path == "/identify":
            origins = json.loads(allowed_origins_raw) if allowed_origins_raw else []
            origin = request.headers.get("origin", "")
            if origins and origin not in origins:
                return Response(
                    content='{"detail":"Origin not allowed"}',
                    status_code=403,
                    media_type="application/json",
                )

            if not _check_rate_limit(key_hash):
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                )

        request.state.key_type = key_type
        return await call_next(request)


def _generate_raw_key(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def _register_routes(app: FastAPI) -> None:
    @app.get("/health")
    async def health(request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    @app.post("/admin/api-keys", response_model=CreateApiKeyResponse)
    async def create_api_key(
        body: CreateApiKeyRequest, request: Request,
    ) -> CreateApiKeyResponse:
        engine: AsyncEngine = request.app.state.engine
        pk_raw = _generate_raw_key("pk_live_")
        sk_raw = _generate_raw_key("sk_live_")
        pk_hash = hashlib.sha256(pk_raw.encode()).hexdigest()
        sk_hash = hashlib.sha256(sk_raw.encode()).hexdigest()
        origins_json = json.dumps(body.allowedOrigins)

        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO api_keys (key_type, key_hash, key_prefix, allowed_origins) "
                    "VALUES (:kt, :kh, :kp, :ao)"
                ),
                {"kt": "publishable", "kh": pk_hash, "kp": "pk_live_", "ao": origins_json},
            )
            await conn.execute(
                text(
                    "INSERT INTO api_keys (key_type, key_hash, key_prefix, allowed_origins) "
                    "VALUES (:kt, :kh, :kp, :ao)"
                ),
                {"kt": "secret", "kh": sk_hash, "kp": "sk_live_", "ao": origins_json},
            )

        return CreateApiKeyResponse(publishableKey=pk_raw, secretKey=sk_raw)

    @app.post("/identify")
    async def identify(body: IdentifyRequest, request: Request):
        engine: AsyncEngine = request.app.state.engine
        visitor_id = body.visitorId
        is_new = True
        signal_validation: str = "new"

        fingerprint_id = _compute_fingerprint_id(body.signals)

        if visitor_id is None:
            visitor_id = f"vis_{uuid.uuid4().hex[:12]}"

        # --- IP geolocation ---
        client_ip = extract_client_ip(
            {k.lower(): v for k, v in request.headers.items()},
            request.client.host if request.client else None,
        )

        geo_resolver: GeoResolver | None = getattr(request.app.state, "geo_resolver", None)
        geo_result = geo_resolver.resolve(client_ip) if geo_resolver else None

        geolocation = Geolocation(
            ip=client_ip,
            country=geo_result.country if geo_result else None,
            city=geo_result.city if geo_result else None,
            latitude=geo_result.latitude if geo_result else None,
            longitude=geo_result.longitude if geo_result else None,
        )

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

            if body.accountId is not None:
                existing = await conn.execute(
                    text(
                        "SELECT 1 FROM account_bindings "
                        "WHERE visitor_id = :vid AND account_id = :aid"
                    ),
                    {"vid": visitor_id, "aid": body.accountId},
                )
                if existing.first() is None:
                    await conn.execute(
                        text(
                            "INSERT INTO account_bindings (visitor_id, account_id) "
                            "VALUES (:vid, :aid)"
                        ),
                        {"vid": visitor_id, "aid": body.accountId},
                    )
                else:
                    await conn.execute(
                        text(
                            "UPDATE account_bindings SET last_seen_at = CURRENT_TIMESTAMP "
                            "WHERE visitor_id = :vid AND account_id = :aid"
                        ),
                        {"vid": visitor_id, "aid": body.accountId},
                    )

            # --- Impossible travel: query previous record BEFORE inserting current ---
            prev_geo_row = None
            if body.accountId and geolocation.latitude is not None:
                prev_result = await conn.execute(
                    text(
                        "SELECT latitude, longitude, country, city, captured_at "
                        "FROM geolocation_history "
                        "WHERE account_id = :aid "
                        "ORDER BY captured_at DESC LIMIT 1"
                    ),
                    {"aid": body.accountId},
                )
                prev_geo_row = prev_result.first()

            # --- Store geolocation ---
            await conn.execute(
                text(
                    "INSERT INTO geolocation_history "
                    "(visitor_id, account_id, ip_address, latitude, longitude, country, city) "
                    "VALUES (:vid, :aid, :ip, :lat, :lon, :country, :city)"
                ),
                {
                    "vid": visitor_id,
                    "aid": body.accountId,
                    "ip": client_ip,
                    "lat": geolocation.latitude,
                    "lon": geolocation.longitude,
                    "country": geolocation.country,
                    "city": geolocation.city,
                },
            )

        # --- Compute impossible travel ---
        impossible_travel = ImpossibleTravel()
        if (
            body.accountId
            and prev_geo_row is not None
            and prev_geo_row[0] is not None
            and prev_geo_row[1] is not None
            and geolocation.latitude is not None
            and geolocation.longitude is not None
        ):
            prev_captured_at_str = str(prev_geo_row[4])
            try:
                prev_time = datetime.fromisoformat(prev_captured_at_str)
            except ValueError:
                prev_time = datetime.strptime(prev_captured_at_str, "%Y-%m-%d %H:%M:%S")
            if prev_time.tzinfo is None:
                prev_time = prev_time.replace(tzinfo=timezone.utc)

            max_speed = float(os.environ.get("SIGIL_IMPOSSIBLE_TRAVEL_MAX_SPEED_KMH", "900"))
            travel = check_impossible_travel(
                geolocation.latitude, geolocation.longitude,
                prev_geo_row[0], prev_geo_row[1],
                prev_time=prev_time,
                current_time=datetime.now(timezone.utc),
                max_speed_kmh=max_speed,
            )
            impossible_travel = ImpossibleTravel(
                detected=travel.detected,
                previousLocation=PreviousLocation(
                    country=prev_geo_row[2],
                    city=prev_geo_row[3],
                    latitude=prev_geo_row[0],
                    longitude=prev_geo_row[1],
                ),
                previousSeenAt=prev_captured_at_str,
                distanceKm=travel.distance_km,
            )

        account_history = AccountHistory()
        if body.accountId is not None:
            async with engine.connect() as conn:
                row = await conn.execute(
                    text(
                        "SELECT status FROM account_bindings "
                        "WHERE visitor_id = :vid AND account_id = :aid"
                    ),
                    {"vid": visitor_id, "aid": body.accountId},
                )
                binding = row.first()
                if binding is not None:
                    account_history.isKnownVisitorForAccount = binding[0] == "verified"

                count_row = await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM account_bindings "
                        "WHERE account_id = :aid AND status = 'verified'"
                    ),
                    {"aid": body.accountId},
                )
                account_history.knownVisitorCount = count_row.scalar() or 0

        cutoff_10m = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        async with engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM signal_sets "
                    "WHERE visitor_id = :vid "
                    "AND captured_at >= :cutoff"
                ),
                {"vid": visitor_id, "cutoff": cutoff_10m},
            )
            visitor_req_count = row.scalar() or 0

        acct_distinct_visitors = None
        if body.accountId is not None:
            cutoff_1h = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            async with engine.connect() as conn:
                row = await conn.execute(
                    text(
                        "SELECT COUNT(DISTINCT visitor_id) FROM account_bindings "
                        "WHERE account_id = :aid "
                        "AND first_seen_at >= :cutoff"
                    ),
                    {"aid": body.accountId, "cutoff": cutoff_1h},
                )
                acct_distinct_visitors = row.scalar() or 0

        # --- IP velocity: distinct accounts from this IP in the last hour ---
        cutoff_1h_ip = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        async with engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT COUNT(DISTINCT account_id) FROM geolocation_history "
                    "WHERE ip_address = :ip "
                    "AND captured_at >= :cutoff "
                    "AND account_id IS NOT NULL"
                ),
                {"ip": client_ip, "cutoff": cutoff_1h_ip},
            )
            ip_distinct_accounts = row.scalar() or 0

        velocity = Velocity(
            visitorRequestsLast10Min=visitor_req_count,
            accountDistinctVisitorsLast1Hr=acct_distinct_visitors,
            ipDistinctAccountsLast1Hr=ip_distinct_accounts,
        )

        sim_threshold = float(os.environ.get("SIGIL_SIMILARITY_THRESHOLD", "0.4"))
        sim_max = int(os.environ.get("SIGIL_SIMILARITY_MAX_RESULTS", "10"))
        weights = getattr(request.app.state, "scoring_weights", DEFAULT_WEIGHTS)

        similar_raw = await find_similar_visitors(
            engine, visitor_id, body.signals, weights,
            threshold=sim_threshold, max_results=sim_max,
        )
        similar_visitors = [SimilarVisitor(**sv) for sv in similar_raw]

        key_type = getattr(request.state, "key_type", None)
        result = IdentifyResponse(
            visitorId=visitor_id,
            fingerprintId=fingerprint_id,
            isNewVisitor=is_new,
            signalValidation=signal_validation,
            serverReachable=True,
            geolocation=geolocation,
            impossibleTravel=impossible_travel,
            similarVisitors=similar_visitors,
            accountHistory=account_history,
            velocity=velocity,
        )

        if key_type == "publishable":
            data = result.model_dump()
            data.pop("accountHistory", None)
            for sv in data.get("similarVisitors", []):
                sv.pop("accountIds", None)
            return data

        return result

    @app.get("/visitors/{visitor_id}")
    async def get_visitor_detail(visitor_id: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.connect() as conn:
            row = await conn.execute(
                text("SELECT visitor_id, first_seen_at, last_seen_at FROM visitors WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )
            visitor = row.first()
            if visitor is None:
                return Response(
                    content='{"detail":"Visitor not found"}',
                    status_code=404,
                    media_type="application/json",
                )

            bindings_result = await conn.execute(
                text(
                    "SELECT account_id, status, first_seen_at, last_seen_at "
                    "FROM account_bindings WHERE visitor_id = :vid"
                ),
                {"vid": visitor_id},
            )
            account_bindings = [
                {
                    "accountId": b[0],
                    "status": b[1],
                    "firstSeenAt": str(b[2]),
                    "lastSeenAt": str(b[3]),
                }
                for b in bindings_result.fetchall()
            ]

            signal_result = await conn.execute(
                text(
                    "SELECT id, captured_at, canvas_hash, webgl_renderer, audio_hash, font_hash, signals_extra "
                    "FROM signal_sets WHERE visitor_id = :vid "
                    "ORDER BY captured_at DESC LIMIT 50"
                ),
                {"vid": visitor_id},
            )
            signal_rows = signal_result.fetchall()

            geo_result = await conn.execute(
                text(
                    "SELECT ip_address, country, city "
                    "FROM geolocation_history "
                    "WHERE visitor_id = :vid ORDER BY captured_at DESC LIMIT 50"
                ),
                {"vid": visitor_id},
            )
            geo_rows = geo_result.fetchall()

            recent_signal_sets = []
            for idx, sr in enumerate(signal_rows):
                ss_id, captured_at, canvas, webgl, audio, font, extra_raw = sr
                signals = {}
                if canvas:
                    signals["canvas"] = canvas
                if webgl:
                    signals["webglRenderer"] = webgl
                if audio:
                    signals["audioHash"] = audio
                if font:
                    signals["fonts"] = font
                extra = json.loads(extra_raw) if extra_raw else {}
                signals.update(extra)

                geolocation = None
                if idx < len(geo_rows):
                    g = geo_rows[idx]
                    geolocation = {"ip": g[0], "country": g[1], "city": g[2]}

                recent_signal_sets.append({
                    "capturedAt": str(captured_at),
                    "signals": signals,
                    "geolocation": geolocation,
                })

        return {
            "visitorId": visitor[0],
            "firstSeenAt": str(visitor[1]),
            "lastSeenAt": str(visitor[2]),
            "accountBindings": account_bindings,
            "recentSignalSets": recent_signal_sets,
        }

    @app.get("/accounts/{account_id}/visitors")
    async def get_account_visitors(account_id: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.connect() as conn:
            bindings = await conn.execute(
                text(
                    "SELECT ab.visitor_id, ab.status, ab.first_seen_at, ab.last_seen_at "
                    "FROM account_bindings ab "
                    "WHERE ab.account_id = :aid"
                ),
                {"aid": account_id},
            )
            rows = bindings.fetchall()

            visitors = []
            for row in rows:
                vid, status, first_seen, last_seen = row

                geo_row = await conn.execute(
                    text(
                        "SELECT country, city FROM geolocation_history "
                        "WHERE visitor_id = :vid "
                        "ORDER BY captured_at DESC LIMIT 1"
                    ),
                    {"vid": vid},
                )
                geo = geo_row.first()
                last_geo = {"country": geo[0], "city": geo[1]} if geo else {"country": None, "city": None}

                visitors.append({
                    "visitorId": vid,
                    "bindingStatus": status,
                    "firstSeenAt": str(first_seen),
                    "lastSeenAt": str(last_seen),
                    "lastGeolocation": last_geo,
                })

        return {"accountId": account_id, "visitors": visitors}

    @app.get("/accounts/{account_id}/geolocations")
    async def get_account_geolocations(
        account_id: str, request: Request, days: int = Query(default=30),
    ):
        engine: AsyncEngine = request.app.state.engine
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT visitor_id, ip_address, country, city, latitude, longitude, captured_at "
                    "FROM geolocation_history "
                    "WHERE account_id = :aid AND captured_at >= :cutoff "
                    "ORDER BY captured_at DESC"
                ),
                {"aid": account_id, "cutoff": cutoff},
            )
            rows = result.fetchall()

        geolocations = [
            {
                "visitorId": r[0],
                "ip": r[1],
                "country": r[2],
                "city": r[3],
                "latitude": r[4],
                "longitude": r[5],
                "capturedAt": str(r[6]),
            }
            for r in rows
        ]
        return {"accountId": account_id, "geolocations": geolocations}

    @app.get("/ip/{ip_address:path}/visitors")
    async def get_ip_visitors(ip_address: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT visitor_id, MIN(captured_at) as first_seen, "
                    "MAX(captured_at) as last_seen, COUNT(*) as req_count "
                    "FROM geolocation_history "
                    "WHERE ip_address = :ip "
                    "GROUP BY visitor_id"
                ),
                {"ip": ip_address},
            )
            rows = result.fetchall()

            visitors = []
            for row in rows:
                vid, first_seen, last_seen, req_count = row

                acct_result = await conn.execute(
                    text(
                        "SELECT DISTINCT account_id FROM geolocation_history "
                        "WHERE visitor_id = :vid AND account_id IS NOT NULL"
                    ),
                    {"vid": vid},
                )
                account_ids = [a[0] for a in acct_result.fetchall()]

                visitors.append({
                    "visitorId": vid,
                    "accountIds": account_ids,
                    "firstSeenFromIp": str(first_seen),
                    "lastSeenFromIp": str(last_seen),
                    "requestCount": req_count,
                })

        return {"ip": ip_address, "visitors": visitors}

    @app.post("/accounts/{account_id}/visitors/{visitor_id}/verify")
    async def verify_binding(account_id: str, visitor_id: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.begin() as conn:
            row = await conn.execute(
                text(
                    "SELECT status FROM account_bindings "
                    "WHERE visitor_id = :vid AND account_id = :aid"
                ),
                {"vid": visitor_id, "aid": account_id},
            )
            if row.first() is None:
                return Response(
                    content='{"detail":"Binding not found"}',
                    status_code=404,
                    media_type="application/json",
                )

            now = datetime.now(timezone.utc).isoformat()
            await conn.execute(
                text(
                    "UPDATE account_bindings "
                    "SET status = 'verified', verified_at = :now "
                    "WHERE visitor_id = :vid AND account_id = :aid"
                ),
                {"vid": visitor_id, "aid": account_id, "now": now},
            )

        return {
            "accountId": account_id,
            "visitorId": visitor_id,
            "bindingStatus": "verified",
            "verifiedAt": now,
        }

    @app.delete("/visitors/{visitor_id}")
    async def delete_visitor(visitor_id: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.begin() as conn:
            row = await conn.execute(
                text("SELECT visitor_id FROM visitors WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )
            if row.first() is None:
                return Response(
                    content='{"detail":"Visitor not found"}',
                    status_code=404,
                    media_type="application/json",
                )

            bindings_del = await conn.execute(
                text("DELETE FROM account_bindings WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )
            bindings_count = bindings_del.rowcount

            geo_del = await conn.execute(
                text("DELETE FROM geolocation_history WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )
            geo_count = geo_del.rowcount

            signal_count_row = await conn.execute(
                text("SELECT COUNT(*) FROM signal_sets WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )
            signal_count = signal_count_row.scalar() or 0

            await conn.execute(
                text("DELETE FROM visitors WHERE visitor_id = :vid"),
                {"vid": visitor_id},
            )

        return {
            "visitorId": visitor_id,
            "deleted": True,
            "recordsRemoved": {
                "signalSets": signal_count,
                "accountBindings": bindings_count,
                "geolocations": geo_count,
            },
        }

    @app.delete("/accounts/{account_id}/visitors/{visitor_id}/verify")
    async def revoke_binding(account_id: str, visitor_id: str, request: Request):
        engine: AsyncEngine = request.app.state.engine
        async with engine.begin() as conn:
            row = await conn.execute(
                text(
                    "SELECT status FROM account_bindings "
                    "WHERE visitor_id = :vid AND account_id = :aid"
                ),
                {"vid": visitor_id, "aid": account_id},
            )
            if row.first() is None:
                return Response(
                    content='{"detail":"Binding not found"}',
                    status_code=404,
                    media_type="application/json",
                )

            now = datetime.now(timezone.utc).isoformat()
            await conn.execute(
                text(
                    "UPDATE account_bindings "
                    "SET status = 'observed', verified_at = NULL "
                    "WHERE visitor_id = :vid AND account_id = :aid"
                ),
                {"vid": visitor_id, "aid": account_id},
            )

        return {
            "accountId": account_id,
            "visitorId": visitor_id,
            "bindingStatus": "observed",
            "revokedAt": now,
        }


app = create_app()
