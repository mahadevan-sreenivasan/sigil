"""Behavior tests for the ip-api Pro geolocation resolver."""
from __future__ import annotations

from dataclasses import dataclass, field

from sigil_server.geolocation import GeoResult, IpApiProGeoResolver


@dataclass
class FakeJsonTransport:
    payload: dict[str, object]
    calls: list[tuple[str, float]] = field(default_factory=list)

    def get_json(self, url: str, timeout_seconds: float) -> dict[str, object]:
        self.calls.append((url, timeout_seconds))
        return self.payload


@dataclass
class TimeoutTransport:
    calls: list[tuple[str, float]] = field(default_factory=list)

    def get_json(self, url: str, timeout_seconds: float) -> dict[str, object]:
        self.calls.append((url, timeout_seconds))
        raise TimeoutError("timed out")


@dataclass
class ErrorTransport:
    calls: list[tuple[str, float]] = field(default_factory=list)

    def get_json(self, url: str, timeout_seconds: float) -> dict[str, object]:
        self.calls.append((url, timeout_seconds))
        raise RuntimeError("provider exploded")


def test_resolve_uses_explicit_ip_path_and_key_query_param():
    transport = FakeJsonTransport(
        payload={
            "status": "success",
            "countryCode": "IN",
            "city": "Mumbai",
            "lat": 19.0760,
            "lon": 72.8777,
        }
    )
    resolver = IpApiProGeoResolver(
        api_key="test-key",
        timeout_seconds=0.2,
        transport=transport,
    )

    _ = resolver.resolve("1.2.3.4")

    assert transport.calls == [
        ("https://pro.ip-api.com/json/1.2.3.4?key=test-key", 0.2),
    ]


def test_resolve_maps_success_payload_to_existing_georesult_fields_only():
    transport = FakeJsonTransport(
        payload={
            "status": "success",
            "countryCode": "GB",
            "city": "London",
            "lat": 51.5074,
            "lon": -0.1278,
            "regionName": "England",
            "timezone": "Europe/London",
            "isp": "Example ISP",
        }
    )
    resolver = IpApiProGeoResolver(api_key="test-key", transport=transport)

    result = resolver.resolve("5.6.7.8")

    assert result == GeoResult(
        country="GB",
        city="London",
        latitude=51.5074,
        longitude=-0.1278,
    )


def test_resolve_fast_fails_on_timeout_without_retries():
    transport = TimeoutTransport()
    resolver = IpApiProGeoResolver(
        api_key="test-key",
        timeout_seconds=0.15,
        transport=transport,
    )

    result = resolver.resolve("9.10.11.12")

    assert result is None
    assert transport.calls == [
        ("https://pro.ip-api.com/json/9.10.11.12?key=test-key", 0.15),
    ]


def test_resolve_returns_none_when_provider_payload_is_not_success():
    transport = FakeJsonTransport(
        payload={
            "status": "fail",
            "message": "private range",
        }
    )
    resolver = IpApiProGeoResolver(api_key="test-key", transport=transport)

    result = resolver.resolve("10.0.0.1")

    assert result is None


def test_resolve_returns_none_on_provider_error_without_raising():
    transport = ErrorTransport()
    resolver = IpApiProGeoResolver(
        api_key="test-key",
        timeout_seconds=0.25,
        transport=transport,
    )

    result = resolver.resolve("8.8.4.4")

    assert result is None
    assert transport.calls == [
        ("https://pro.ip-api.com/json/8.8.4.4?key=test-key", 0.25),
    ]
