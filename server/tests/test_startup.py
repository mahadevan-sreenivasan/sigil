"""Tests for startup validation behavior."""
from __future__ import annotations

import pytest

from sigil_server.startup import validate_env


def test_missing_database_url_raises_clear_error(monkeypatch):
    """Startup validation fails fast with a clear message when DATABASE_URL is unset."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_env()


def test_database_url_present_passes(monkeypatch):
    """Startup validation passes when DATABASE_URL is set."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sigil")
    monkeypatch.setenv("SIGIL_ADMIN_TOKEN", "a" * 32)
    validate_env()


def test_missing_admin_token_raises_clear_error(monkeypatch):
    """Startup validation fails fast when SIGIL_ADMIN_TOKEN is unset."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sigil")
    monkeypatch.delenv("SIGIL_ADMIN_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="SIGIL_ADMIN_TOKEN"):
        validate_env()


def test_short_admin_token_raises_clear_error(monkeypatch):
    """Startup validation rejects tokens shorter than 32 characters."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sigil")
    monkeypatch.setenv("SIGIL_ADMIN_TOKEN", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        validate_env()


def test_valid_admin_token_passes(monkeypatch):
    """Startup validation accepts a 32+ character admin token."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sigil")
    monkeypatch.setenv("SIGIL_ADMIN_TOKEN", "a" * 32)
    validate_env()
