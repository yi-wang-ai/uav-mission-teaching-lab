"""Interfaces shared by the offline test double and the real PX4 adapter."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import time
from typing import Protocol

from .geometry import Home, Waypoint


class LabError(RuntimeError):
    """Expected mission, configuration or telemetry error."""


class TelemetryNotReady(LabError):
    """Required streams have not produced their first values yet."""


@dataclass(frozen=True)
class Snapshot:
    latitude_deg: float
    longitude_deg: float
    relative_altitude_m: float
    battery_fraction: float
    in_air: bool
    armed: bool
    healthy: bool
    flight_mode: str
    mission_current: int = 0
    mission_total: int = 0
    mission_finished: bool = False
    position_age_s: float = 0.0
    battery_age_s: float = 0.0

    def validate(self) -> None:
        values = (self.latitude_deg, self.longitude_deg, self.relative_altitude_m,
                  self.battery_fraction, self.position_age_s, self.battery_age_s)
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
            raise LabError("invalid / nonfinite telemetry")
        if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180:
            raise LabError("invalid telemetry coordinates")
        if not 0 <= self.battery_fraction <= 1:
            raise LabError("battery telemetry is unavailable or outside [0, 1]")
        if self.position_age_s < 0 or self.battery_age_s < 0:
            raise LabError("negative telemetry age")
        if any(not isinstance(v, bool) for v in (self.in_air, self.armed, self.healthy, self.mission_finished)):
            raise LabError("telemetry flags must be booleans")


class Clock(Protocol):
    def now(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...


class RealClock:
    def __init__(self) -> None:
        self.start = time.monotonic()

    def now(self) -> float:
        return time.monotonic() - self.start

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class DemoClock:
    """Virtual test time; not PX4 or Gazebo simulation time."""
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += seconds
        await asyncio.sleep(0)


class Vehicle(Protocol):
    backend: str
    async def connect(self) -> None: ...
    async def get_home(self) -> Home: ...
    async def upload(self, waypoints: list[Waypoint]) -> None: ...
    async def arm(self) -> None: ...
    async def start_mission(self) -> None: ...
    async def snapshot(self) -> Snapshot: ...
    async def land(self) -> None: ...
    async def close(self) -> None: ...
