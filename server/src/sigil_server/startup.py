"""Startup validation for the Sigil server."""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def validate_env() -> None:
    """Validate that all required environment variables are set.

    Raises RuntimeError with a clear message if anything is missing.
    """
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL environment variable is required but not set. "
            "Example: postgresql://user:pass@localhost:5432/sigil"
        )

    admin_token = os.environ.get("SIGIL_ADMIN_TOKEN")
    if not admin_token:
        raise RuntimeError(
            "SIGIL_ADMIN_TOKEN environment variable is required but not set. "
            "Generate one with: openssl rand -base64 32  or  "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    if len(admin_token) < 32:
        raise RuntimeError(
            f"SIGIL_ADMIN_TOKEN must be at least 32 characters (got {len(admin_token)}). "
            "Generate one with: openssl rand -base64 32  or  "
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    maxmind_path = os.environ.get("MAXMIND_DB_PATH")
    if not maxmind_path:
        logger.warning(
            "MAXMIND_DB_PATH is not set. Geolocation features will be unavailable."
        )


def validate_config(config_path: str) -> None:
    """Validate sigil-config.yaml if it exists.

    Checks that signal weights sum to 1.0.
    Raises RuntimeError with a clear message if validation fails.
    """
    path = Path(config_path)
    if not path.exists():
        return

    with open(path) as f:
        config = yaml.safe_load(f)

    if config is None:
        return

    weights = config.get("weights")
    if weights is None:
        return

    total = sum(weights.values())
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise RuntimeError(
            f"Signal weights in {config_path} must sum to 1.0, got {total:.4f}. "
            f"Current weights: {weights}"
        )


def load_weights(config_path: str) -> dict[str, float] | None:
    """Load weight overrides from sigil-config.yaml if present. Returns None if no overrides."""
    path = Path(config_path)
    if not path.exists():
        return None

    with open(path) as f:
        config = yaml.safe_load(f)

    if config is None:
        return None

    return config.get("weights")
