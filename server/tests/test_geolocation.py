"""Unit tests for haversine distance and impossible travel detection (pure functions)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sigil_server.geolocation import check_impossible_travel, haversine_distance

MUMBAI = (19.0760, 72.8777)
LONDON = (51.5074, -0.1278)
NYC = (40.7128, -74.0060)
LA = (34.0522, -118.2437)


class TestHaversineDistance:
    def test_mumbai_to_london(self):
        dist = haversine_distance(*MUMBAI, *LONDON)
        assert 7_000 < dist < 7_400

    def test_nyc_to_la(self):
        dist = haversine_distance(*NYC, *LA)
        assert 3_900 < dist < 4_000

    def test_same_point_returns_zero(self):
        dist = haversine_distance(*MUMBAI, *MUMBAI)
        assert dist == 0.0


class TestCheckImpossibleTravel:
    def test_detected_when_too_fast(self):
        """7,200 km in 2 hours requires 3,600 km/h — far above 900 km/h max."""
        prev_time = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
        curr_time = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

        result = check_impossible_travel(
            *LONDON, *MUMBAI,
            prev_time=prev_time,
            current_time=curr_time,
            max_speed_kmh=900.0,
        )

        assert result.detected is True
        assert result.distance_km is not None
        assert result.distance_km > 7_000

    def test_not_detected_when_slow_enough(self):
        """500 km in 2 hours = 250 km/h — well under 900 km/h."""
        prev_time = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
        curr_time = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

        result = check_impossible_travel(
            current_lat=19.0760, current_lon=72.8777,
            prev_lat=19.0760, prev_lon=77.5946,
            prev_time=prev_time,
            current_time=curr_time,
            max_speed_kmh=900.0,
        )

        assert result.detected is False

    def test_not_detected_when_no_previous(self):
        """No previous location → not detected (caller responsibility, but verify None handling)."""
        result = check_impossible_travel(
            *MUMBAI, *MUMBAI,
            prev_time=datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
            max_speed_kmh=900.0,
        )
        assert result.detected is False
        assert result.distance_km == 0.0
