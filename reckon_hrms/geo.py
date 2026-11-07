"""Geofence rule for check-in and check-out. No Frappe import, so it is unit-testable."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0
DEFAULT_RADIUS_M = 150.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def within_geofence(lat: float | None, lon: float | None, office_lat: float, office_lon: float,
                    radius_m: float | None) -> tuple[bool, float]:
    """(inside, distance). A missing position is never inside a fence."""
    if lat is None or lon is None:
        return False, float("inf")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False, float("inf")
    d = distance_m(lat, lon, office_lat, office_lon)
    return d <= (radius_m or DEFAULT_RADIUS_M), d
