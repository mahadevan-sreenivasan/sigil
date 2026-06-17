"""Tests for startup validation behavior."""
from __future__ import annotations

import logging

import pytest

from sigil_server.geolocation import IpApiProGeoResolver
from sigil_server.main import create_app
from sigil_server.startup import validate_env


def test_missing_database_url_raises_clear_error(monkeypatch):
    """Startup validation fails fast with a clear message when DATABASE_URL is unset."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_env()


def test_database_url_present_passes(monkeypatch):
    """Startup validation passes when DATABASE_URL is set."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sigil")
    validate_env()


@pytest.mark.asyncio
async def test_lifespan_attaches_ip_api_resolver_when_key_present(monkeypatch):
    """App startup wires ip-api resolver onto app state when configured."""
    monkeypatch.setenv("IP_API_PRO_KEY", "pro-key-123")
    app = create_app(engine=object())

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.geo_resolver, IpApiProGeoResolver)
        assert app.state.geo_resolver.api_key == "pro-key-123"


@pytest.mark.asyncio
async def test_lifespan_leaves_geolocation_unavailable_without_key(
    monkeypatch, caplog,
):
    """App startup does not wire a resolver if IP_API_PRO_KEY is absent."""
    monkeypatch.delenv("IP_API_PRO_KEY", raising=False)
    app = create_app(engine=object())

    with caplog.at_level(logging.WARNING):
        async with app.router.lifespan_context(app):
            assert not hasattr(app.state, "geo_resolver")

    assert "IP_API_PRO_KEY is not set" in caplog.text
