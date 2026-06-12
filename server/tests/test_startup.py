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
    validate_env()
