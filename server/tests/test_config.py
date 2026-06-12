"""Tests for sigil-config.yaml validation."""
from __future__ import annotations

import pytest

from sigil_server.startup import validate_config


def test_valid_config_weights_sum_to_one(tmp_path):
    """Config with weights summing to 1.0 passes validation."""
    config_file = tmp_path / "sigil-config.yaml"
    config_file.write_text(
        "weights:\n"
        "  canvas: 0.4\n"
        "  webglRenderer: 0.3\n"
        "  audioHash: 0.2\n"
        "  fonts: 0.1\n"
    )
    validate_config(str(config_file))


def test_invalid_config_weights_not_summing_to_one(tmp_path):
    """Config with weights NOT summing to 1.0 raises RuntimeError."""
    config_file = tmp_path / "sigil-config.yaml"
    config_file.write_text(
        "weights:\n"
        "  canvas: 0.5\n"
        "  webglRenderer: 0.3\n"
        "  audioHash: 0.2\n"
        "  fonts: 0.2\n"
    )
    with pytest.raises(RuntimeError, match="sum to 1.0"):
        validate_config(str(config_file))


def test_missing_config_file_is_not_an_error():
    """If no config file exists, validation passes silently."""
    validate_config("/nonexistent/sigil-config.yaml")
