"""Small local routes anchored to the connected simulator's reported home."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .config import MissionConfig

EARTH_RADIUS_M = 6_378_137.0


@dataclass(frozen=True)
class Home:
    latitude_deg: float
    longitude_deg: float
    absolute_altitude_m: float

    def __post_init__(self) -> None:
        for value in (self.latitude_deg, self.longitude_deg, self.absolute_altitude_m):
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError("home coordinates and altitude must be finite")
        if not -85 <= self.latitude_deg <= 85 or not -180 <= self.longitude_deg <= 180:
            raise ValueError("invalid home coordinates; this local approximation excludes polar regions")


@dataclass(frozen=True)
class Waypoint:
    latitude_deg: float
    longitude_deg: float
    relative_altitude_m: float
    speed_m_s: float


def offset_to_global(home: Home, north_m: float, east_m: float) -> tuple[float, float]:
    """First-order spherical conversion, intended only for this <=50 m lab."""
    lat = home.latitude_deg + math.degrees(north_m / EARTH_RADIUS_M)
    lon = home.longitude_deg + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(home.latitude_deg))))
    return lat, (lon + 180.0) % 360.0 - 180.0


def global_to_offset(home: Home, lat: float, lon: float) -> tuple[float, float]:
    north = math.radians(lat - home.latitude_deg) * EARTH_RADIUS_M
    dlon = (lon - home.longitude_deg + 180.0) % 360.0 - 180.0
    east = math.radians(dlon) * EARTH_RADIUS_M * math.cos(math.radians(home.latitude_deg))
    return north, east


def build_waypoints(config: MissionConfig, home: Home) -> list[Waypoint]:
    return [Waypoint(*offset_to_global(home, n, e), config.altitude_m, config.speed_m_s)
            for n, e in config.waypoints_ne_m]
