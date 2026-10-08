"""Deterministic software test double. NOT a flight-dynamics simulator."""
from __future__ import annotations

import math
from .config import MissionConfig
from .geometry import Home, Waypoint, offset_to_global
from .model import Clock, LabError, Snapshot

SCENARIOS = ("normal", "low-battery", "mission-stall", "link-loss")


class DemoVehicle:
    backend = "offline-demo"

    def __init__(self, config: MissionConfig, clock: Clock, scenario: str = "normal") -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown demo scenario: {scenario}")
        self.config, self.clock, self.scenario = config, clock, scenario
        self.home = Home(47.397742, 8.545594, 488.0)
        self.started_at: float | None = None
        self.land_at: float | None = None
        self.land_from = (0.0, 0.0, 0.0)
        self.armed = False
        self.commands: list[str] = []
        self.uploaded: list[Waypoint] = []
        self.closed = False

    async def connect(self) -> None:
        self.commands.append("connect")

    async def get_home(self) -> Home:
        return self.home

    async def upload(self, waypoints: list[Waypoint]) -> None:
        self.uploaded = list(waypoints)
        self.commands.append("upload")

    async def arm(self) -> None:
        if not self.uploaded:
            raise LabError("no mission uploaded")
        self.armed = True
        self.commands.append("arm")

    async def start_mission(self) -> None:
        if not self.armed:
            raise LabError("cannot start while disarmed")
        self.started_at = self.clock.now()
        self.commands.append("start_mission")

    def _state(self) -> tuple[float, float, float, int, bool, str]:
        """Return north, east, altitude, progress, finished, mode."""
        if self.land_at is not None:
            n, e, height = self.land_from
            altitude = max(0.0, height - (self.clock.now() - self.land_at))
            return n, e, altitude, 0, False, "LAND" if altitude else "READY"
        if self.started_at is None:
            return 0.0, 0.0, 0.0, 0, False, "READY"
        elapsed = self.clock.now() - self.started_at
        altitude = min(self.config.altitude_m, elapsed)
        if elapsed < self.config.altitude_m:
            return 0.0, 0.0, altitude, 0, False, "TAKEOFF"
        if self.scenario == "mission-stall":
            return 0.0, 0.0, altitude, 1, False, "HOLD"
        remaining = elapsed - self.config.altitude_m
        points = self.config.waypoints_ne_m
        for i, (a, b) in enumerate(zip(points, points[1:]), start=1):
            duration = math.dist(a, b) / self.config.speed_m_s
            if remaining < duration:
                ratio = remaining / duration if duration else 1.0
                n = a[0] + ratio * (b[0] - a[0])
                e = a[1] + ratio * (b[1] - a[1])
                return n, e, altitude, i, False, "MISSION"
            remaining -= duration
        altitude = max(0.0, self.config.altitude_m - remaining)
        return 0.0, 0.0, altitude, len(points), True, "RETURN_TO_LAUNCH" if altitude else "READY"

    def _link_lost(self) -> bool:
        return self.scenario == "link-loss" and self.started_at is not None and self.clock.now() - self.started_at >= 15

    async def snapshot(self) -> Snapshot:
        if self._link_lost():
            raise LabError("synthetic link loss: telemetry unavailable")
        n, e, alt, current, finished, mode = self._state()
        if (finished or self.land_at is not None) and alt == 0:
            self.armed = False
        battery = 0.10 if self.scenario == "low-battery" else max(0.5, 1.0 - 0.001 * self.clock.now())
        lat, lon = offset_to_global(self.home, n, e)
        return Snapshot(lat, lon, alt, battery, alt > 0, self.armed, True, mode,
                        current, len(self.uploaded), finished)

    async def land(self) -> None:
        self.commands.append("land")
        if self._link_lost():
            raise LabError("synthetic link loss: land command not delivered")
        n, e, alt, *_ = self._state()
        self.land_from = (n, e, alt)
        self.land_at = self.clock.now()

    async def close(self) -> None:
        self.closed = True
