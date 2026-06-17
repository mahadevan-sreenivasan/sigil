"""IP geolocation resolution and impossible travel detection."""
from __future__ import annotations

import math
import os
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Great-circle distance between two points on Earth in kilometers."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


@dataclass
class GeoResult:
    """Result of resolving an IP address to a geographic location."""
    country: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class GeoResolver(Protocol):
    """Abstraction over IP-to-location resolution (MaxMind in production, mock in tests)."""
    def resolve(self, ip: str) -> GeoResult | None: ...


class JsonHttpTransport(Protocol):
    """Tiny HTTP seam to keep resolver tests deterministic."""

    def get_json(self, url: str, timeout_seconds: float) -> dict[str, Any]: ...


class UrllibJsonHttpTransport:
    """Minimal stdlib transport for JSON GET requests."""

    def get_json(self, url: str, timeout_seconds: float) -> dict[str, Any]:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object response")
        return data


@dataclass
class IpApiProGeoResolver:
    """Resolve geolocation using explicit-IP lookups against ip-api Pro."""

    api_key: str
    timeout_seconds: float = 0.5
    base_url: str = "https://pro.ip-api.com"
    transport: JsonHttpTransport | None = None

    def resolve(self, ip: str) -> GeoResult | None:
        encoded_ip = urllib.parse.quote(ip, safe="")
        query = urllib.parse.urlencode({"key": self.api_key})
        url = f"{self.base_url.rstrip('/')}/json/{encoded_ip}?{query}"

        transport = self.transport or UrllibJsonHttpTransport()
        try:
            payload = transport.get_json(url, self.timeout_seconds)
        except (TimeoutError, OSError, ValueError, urllib.error.URLError):
            return None
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None

        if payload.get("status") != "success":
            return None

        latitude = _to_float(payload.get("lat"))
        longitude = _to_float(payload.get("lon"))
        country = _to_str(payload.get("countryCode"))
        city = _to_str(payload.get("city"))
        return GeoResult(
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
        )


@dataclass
class ImpossibleTravelResult:
    detected: bool
    distance_km: float | None = None


def check_impossible_travel(
    current_lat: float,
    current_lon: float,
    prev_lat: float,
    prev_lon: float,
    *,
    prev_time: datetime,
    current_time: datetime,
    max_speed_kmh: float = 900.0,
) -> ImpossibleTravelResult:
    """Return whether travel between two geo-points is physically impossible.

    Compares haversine distance against elapsed time at max_speed_kmh.
    """
    distance = haversine_distance(current_lat, current_lon, prev_lat, prev_lon)
    elapsed_seconds = (current_time - prev_time).total_seconds()

    if elapsed_seconds <= 0:
        detected = distance > 0
    else:
        elapsed_hours = elapsed_seconds / 3600.0
        required_speed = distance / elapsed_hours
        detected = required_speed > max_speed_kmh

    return ImpossibleTravelResult(
        detected=detected,
        distance_km=round(distance, 1),
    )


def extract_client_ip(headers: dict[str, str], client_host: str | None) -> str:
    """Read the real client IP from the trusted header, falling back to the connection IP."""
    header_name = os.environ.get("SIGIL_TRUSTED_IP_HEADER", "X-Forwarded-For")
    forwarded = headers.get(header_name.lower())
    if forwarded:
        return forwarded.split(",")[0].strip()
    return client_host or "0.0.0.0"


def _to_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _to_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
