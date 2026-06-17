"""Startup validation for the Sigil server."""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path

import yaml

from .geolocation import IpApiProGeoResolver

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


def build_geo_resolver() -> IpApiProGeoResolver | None:
    """Create an ip-api resolver from environment, or return None (fail-open)."""
    api_key = os.environ.get("IP_API_PRO_KEY")
    if not api_key:
        logger.warning(
            "IP_API_PRO_KEY is not set. Geolocation enrichment will be unavailable."
        )
        return None
    return IpApiProGeoResolver(api_key=api_key)


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
