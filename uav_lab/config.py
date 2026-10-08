"""Strict mission configuration. Invalid or surprising input fails before arming."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MissionConfig:
    name: str = "square-20m"
    altitude_m: float = 10.0
    speed_m_s: float = 3.0
    waypoints_ne_m: tuple[tuple[float, float], ...] = (
        (0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0), (0.0, 0.0)
    )
    min_battery_fraction: float = 0.4
    connect_timeout_s: float = 30.0
    ready_timeout_s: float = 60.0
    takeoff_timeout_s: float = 40.0
    mission_timeout_s: float = 180.0
    landing_timeout_s: float = 120.0
    command_timeout_s: float = 10.0
    poll_interval_s: float = 0.5
    telemetry_max_age_s: float = 5.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 80:
            raise ValueError("name must be a nonempty string of at most 80 characters")
        ranges = {
            "altitude_m": (2, 30), "speed_m_s": (0.5, 5),
            "min_battery_fraction": (0.2, 1), "poll_interval_s": (0.05, 2),
            "telemetry_max_age_s": (1, 15),
        }
        for f in fields(self):
            if f.name.endswith("timeout_s"):
                ranges[f.name] = (0.1, 900)
        for name, (lo, hi) in ranges.items():
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"{name} must be a finite number")
            if not lo <= v <= hi:
                raise ValueError(f"{name} must be between {lo} and {hi}")
        points = self.waypoints_ne_m
        if not isinstance(points, (tuple, list)) or not 2 <= len(points) <= 20:
            raise ValueError("waypoints_ne_m must contain 2 to 20 [north, east] points")
        normalised = []
        for p in points:
            if not isinstance(p, (tuple, list)) or len(p) != 2:
                raise ValueError("each waypoint must contain exactly [north_m, east_m]")
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in p):
                raise ValueError("waypoint coordinates must be finite numbers")
            if math.hypot(*p) > 50:
                raise ValueError("each waypoint must be within 50 m of home")
            normalised.append((float(p[0]), float(p[1])))
        if normalised[0] != (0.0, 0.0) or normalised[-1] != (0.0, 0.0):
            raise ValueError("the first and last waypoint must be [0, 0] (home)")
        distance = sum(math.dist(a, b) for a, b in zip(normalised, normalised[1:]))
        if not 1 <= distance <= 250:
            raise ValueError("horizontal route length must be between 1 and 250 m")
        object.__setattr__(self, "waypoints_ne_m", tuple(normalised))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path | None = None) -> MissionConfig:
    if path is None:
        return MissionConfig()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("mission configuration must be a JSON object")
    unknown = set(data) - {f.name for f in fields(MissionConfig)}
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
    return MissionConfig(**data)
