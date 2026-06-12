"""Unit tests for the pure similarity scoring function."""
from __future__ import annotations

import pytest


class TestComputeSimilarityScoreFullMatch:
    def test_identical_signal_sets_score_one(self):
        from sigil_server.scoring import compute_similarity_score, DEFAULT_WEIGHTS

        signals = {
            "canvas": "abc123",
            "webglRenderer": "NVIDIA GTX 1080",
            "audioHash": "audio_xyz",
            "fontHash": "font_abc",
            "screenResolution": "1920x1080",
            "platform": "Win32",
            "timezone": "Asia/Kolkata",
            "hardwareConcurrency": "8",
            "deviceMemory": "16",
            "touchSupport": "false",
            "userAgent": "Mozilla/5.0",
        }

        score, matching, mismatched = compute_similarity_score(
            signals, signals, DEFAULT_WEIGHTS,
        )

        assert score == pytest.approx(1.0)
        assert len(mismatched) == 0
        assert set(matching) == set(DEFAULT_WEIGHTS.keys())


class TestComputeSimilarityScoreNoMatch:
    def test_completely_different_signals_score_zero(self):
        from sigil_server.scoring import compute_similarity_score, DEFAULT_WEIGHTS

        signals_a = {
            "canvas": "abc123",
            "webglRenderer": "NVIDIA GTX 1080",
            "audioHash": "audio_xyz",
            "fontHash": "font_abc",
            "screenResolution": "1920x1080",
            "platform": "Win32",
            "timezone": "Asia/Kolkata",
            "hardwareConcurrency": "8",
            "deviceMemory": "16",
            "touchSupport": "false",
            "userAgent": "Mozilla/5.0",
        }
        signals_b = {
            "canvas": "def456",
            "webglRenderer": "AMD Radeon",
            "audioHash": "audio_other",
            "fontHash": "font_other",
            "screenResolution": "1366x768",
            "platform": "MacIntel",
            "timezone": "America/New_York",
            "hardwareConcurrency": "4",
            "deviceMemory": "8",
            "touchSupport": "true",
            "userAgent": "Safari/16",
        }

        score, matching, mismatched = compute_similarity_score(
            signals_a, signals_b, DEFAULT_WEIGHTS,
        )

        assert score == pytest.approx(0.0)
        assert len(matching) == 0
        assert set(mismatched) == set(DEFAULT_WEIGHTS.keys())


class TestComputeSimilarityScorePartialMatch:
    def test_only_canvas_and_webgl_match(self):
        """canvas (0.20) + webglRenderer (0.15) = 0.35 out of 1.0 → 0.35."""
        from sigil_server.scoring import compute_similarity_score, DEFAULT_WEIGHTS

        signals_a = {
            "canvas": "same_hash",
            "webglRenderer": "same_renderer",
            "audioHash": "audio_a",
            "fontHash": "font_a",
            "screenResolution": "1920x1080",
            "platform": "Win32",
            "timezone": "Asia/Kolkata",
            "hardwareConcurrency": "8",
            "deviceMemory": "16",
            "touchSupport": "false",
            "userAgent": "Mozilla/5.0",
        }
        signals_b = {
            "canvas": "same_hash",
            "webglRenderer": "same_renderer",
            "audioHash": "audio_b",
            "fontHash": "font_b",
            "screenResolution": "1366x768",
            "platform": "MacIntel",
            "timezone": "America/New_York",
            "hardwareConcurrency": "4",
            "deviceMemory": "8",
            "touchSupport": "true",
            "userAgent": "Safari/16",
        }

        score, matching, mismatched = compute_similarity_score(
            signals_a, signals_b, DEFAULT_WEIGHTS,
        )

        assert score == pytest.approx(0.35)
        assert set(matching) == {"canvas", "webglRenderer"}
        assert len(mismatched) == 9


class TestComputeSimilarityScoreMissingSignals:
    def test_missing_signals_in_one_set_count_as_mismatch(self):
        """Signal present in A but absent from B → mismatch.
        canvas matches (0.20). webglRenderer missing from B → mismatch.
        Only these two are in the weight map, so active_weight = 0.35.
        Score = 0.20 / 0.35 ≈ 0.5714.
        """
        from sigil_server.scoring import compute_similarity_score

        weights = {"canvas": 0.20, "webglRenderer": 0.15}
        signals_a = {"canvas": "same", "webglRenderer": "renderer_a"}
        signals_b = {"canvas": "same"}

        score, matching, mismatched = compute_similarity_score(
            signals_a, signals_b, weights,
        )

        assert score == pytest.approx(0.20 / 0.35)
        assert matching == ["canvas"]
        assert mismatched == ["webglRenderer"]

    def test_signal_missing_from_both_sets_is_skipped(self):
        """Signal in weight map but absent from both sets → skipped entirely."""
        from sigil_server.scoring import compute_similarity_score

        weights = {"canvas": 0.50, "webglRenderer": 0.50}
        signals_a = {"canvas": "same"}
        signals_b = {"canvas": "same"}

        score, matching, mismatched = compute_similarity_score(
            signals_a, signals_b, weights,
        )

        assert score == pytest.approx(1.0)
        assert matching == ["canvas"]
        assert mismatched == []

    def test_both_sets_empty_returns_zero(self):
        from sigil_server.scoring import compute_similarity_score, DEFAULT_WEIGHTS

        score, matching, mismatched = compute_similarity_score(
            {}, {}, DEFAULT_WEIGHTS,
        )

        assert score == pytest.approx(0.0)
        assert matching == []
        assert mismatched == []


class TestComputeSimilarityScoreCustomWeights:
    def test_custom_weights_change_score(self):
        """With custom weights heavily favouring canvas (0.90),
        matching only canvas gives ~0.90 instead of ~0.35 with defaults.
        """
        from sigil_server.scoring import compute_similarity_score

        custom_weights = {
            "canvas": 0.90,
            "webglRenderer": 0.02,
            "audioHash": 0.02,
            "fontHash": 0.02,
            "screenResolution": 0.01,
            "platform": 0.01,
            "timezone": 0.01,
            "hardwareConcurrency": 0.005,
            "deviceMemory": 0.005,
            "touchSupport": 0.00,
            "userAgent": 0.00,
        }

        signals_a = {
            "canvas": "same",
            "webglRenderer": "a",
            "audioHash": "a",
            "fontHash": "a",
            "screenResolution": "a",
            "platform": "a",
            "timezone": "a",
            "hardwareConcurrency": "a",
            "deviceMemory": "a",
            "touchSupport": "a",
            "userAgent": "a",
        }
        signals_b = {
            "canvas": "same",
            "webglRenderer": "b",
            "audioHash": "b",
            "fontHash": "b",
            "screenResolution": "b",
            "platform": "b",
            "timezone": "b",
            "hardwareConcurrency": "b",
            "deviceMemory": "b",
            "touchSupport": "b",
            "userAgent": "b",
        }

        score, matching, mismatched = compute_similarity_score(
            signals_a, signals_b, custom_weights,
        )

        assert score == pytest.approx(0.90)
        assert matching == ["canvas"]
        assert len(mismatched) == 10
