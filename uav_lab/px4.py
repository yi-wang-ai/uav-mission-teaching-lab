"""PX4/Gazebo x500 adapter. End-to-end simulator validation is still required.

The localhost restriction and airframe check reduce accidental targeting; they
cannot prove that a local MAVLink bridge is not connected to physical hardware.
Use a dedicated simulator environment with no real vehicles or hardware bridges.
"""
from __future__ import annotations

import asyncio
from importlib import metadata
from typing import Any

from .config import MissionConfig
from .geometry import Home, Waypoint
from .model import Clock, LabError, Snapshot, TelemetryNotReady

MAVSDK_GRPC_VERSION = "4.0.5"
SYSTEM_ADDRESS = "udpin://127.0.0.1:14540"
EXPECTED_AUTOSTART = 4001  # PX4 Gazebo x500, not a physical-hardware identity proof.


def make_mavsdk_plan(waypoints: list[Waypoint], item_class=None, plan_class=None):
    if item_class is None or plan_class is None:
        from mavsdk_grpc.mission import MissionItem, MissionPlan
        item_class, plan_class = MissionItem, MissionPlan
    items = []
    for i, wp in enumerate(waypoints):
        items.append(item_class(
            latitude_deg=wp.latitude_deg, longitude_deg=wp.longitude_deg,
            relative_altitude_m=wp.relative_altitude_m, speed_m_s=wp.speed_m_s,
            is_fly_through=False, gimbal_pitch_deg=float("nan"), gimbal_yaw_deg=float("nan"),
            camera_action=item_class.CameraAction.NONE, loiter_time_s=0.0,
            camera_photo_interval_s=float("nan"), acceptance_radius_m=1.0,
            yaw_deg=float("nan"), camera_photo_distance_m=float("nan"),
            vehicle_action=item_class.VehicleAction.TAKEOFF if i == 0 else item_class.VehicleAction.NONE,
        ))
    return plan_class(items)


class Px4Vehicle:
    backend = "px4-sitl"

    def __init__(self, config: MissionConfig, clock: Clock, *, confirm_sitl: bool = False,
                 _system: Any = None) -> None:
        if not confirm_sitl:
            raise LabError("PX4 mode requires --confirm-sitl and a simulator-only host")
        self.config, self.clock = config, clock
        self.system = _system
        self.cache: dict[str, Any] = {}
        self.updated: dict[str, float] = {}
        self.errors: dict[str, str] = {}
        self.tasks: list[asyncio.Task] = []
        self.started = False
        self.finished = False

    async def _watch(self, name: str, stream) -> None:
        try:
            async for value in stream:
                self.cache[name] = value
                self.updated[name] = self.clock.now()
            self.errors[name] = f"{name} stream ended"
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.errors[name] = f"{name}: {type(exc).__name__}: {exc}"

    async def connect(self) -> None:
        if self.system is None:
            try:
                installed = metadata.version("mavsdk-grpc")
                if installed != MAVSDK_GRPC_VERSION:
                    raise LabError(f"expected mavsdk-grpc=={MAVSDK_GRPC_VERSION}, found {installed}")
                from mavsdk_grpc import System
            except (ImportError, metadata.PackageNotFoundError) as exc:
                raise LabError("install the optional PX4 dependency: python3 -m pip install -e '.[px4]'") from exc
            self.system = System()
        await self.system.connect(system_address=SYSTEM_ADDRESS)
        async for state in self.system.core.connection_state():
            if state.is_connected:
                self.cache["connection"] = state
                break
        else:
            raise LabError("connection stream ended before an autopilot appeared")
        autostart = await self.system.param.get_param_int("SYS_AUTOSTART")
        if autostart != EXPECTED_AUTOSTART:
            raise LabError(f"refusing airframe {autostart}; expected Gazebo x500 SYS_AUTOSTART=4001")
        streams = {
            "connection": self.system.core.connection_state(),
            "position": self.system.telemetry.position(), "home": self.system.telemetry.home(),
            "battery": self.system.telemetry.battery(), "health": self.system.telemetry.health(),
            "in_air": self.system.telemetry.in_air(), "armed": self.system.telemetry.armed(),
            "mode": self.system.telemetry.flight_mode(),
            "progress": self.system.mission.mission_progress(),
        }
        self.tasks = [asyncio.create_task(self._watch(name, stream), name=f"uav-{name}")
                      for name, stream in streams.items()]
        await self.system.telemetry.set_rate_position(5.0)
        await self.system.telemetry.set_rate_battery(1.0)

    async def get_home(self) -> Home:
        if "home" not in self.cache:
            raise TelemetryNotReady("waiting for home position")
        h = self.cache["home"]
        return Home(h.latitude_deg, h.longitude_deg, h.absolute_altitude_m)

    async def upload(self, waypoints: list[Waypoint]) -> None:
        plan = make_mavsdk_plan(waypoints)
        await self.system.mission.set_return_to_launch_after_mission(True)
        await self.system.mission.upload_mission(plan)
        self.started = self.finished = False

    async def arm(self) -> None:
        await self.system.action.arm()

    async def start_mission(self) -> None:
        await self.system.mission.start_mission()
        self.started = True

    def _require_streams(self) -> None:
        required = ("connection", "position", "home", "battery", "health", "in_air", "armed", "mode")
        for key in required:
            if key in self.errors:
                raise LabError(self.errors[key])
            if key not in self.cache:
                raise TelemetryNotReady(f"waiting for {key}")
        if not self.cache["connection"].is_connected:
            raise LabError("MAVLink connection lost")

    async def snapshot(self) -> Snapshot:
        self._require_streams()
        if self.started and not self.finished:
            self.finished = bool(await self.system.mission.is_mission_finished())
        # An RPC can take time. Re-check connection and freshness AFTER awaiting
        # it, and use the latest cached values rather than a pre-RPC snapshot.
        self._require_streams()
        p, b, h = self.cache["position"], self.cache["battery"], self.cache["health"]
        # Position/battery are periodic. State-change streams must NOT be aged out
        # simply because their values remained unchanged.
        pos_age = self.clock.now() - self.updated["position"]
        bat_age = self.clock.now() - self.updated["battery"]
        if max(pos_age, bat_age) > self.config.telemetry_max_age_s:
            raise LabError("stale position or battery telemetry")
        progress = self.cache.get("progress")
        mode = self.cache["mode"]
        snapshot = Snapshot(
            latitude_deg=p.latitude_deg, longitude_deg=p.longitude_deg,
            relative_altitude_m=p.relative_altitude_m, battery_fraction=b.remaining_percent,
            in_air=self.cache["in_air"], armed=self.cache["armed"],
            healthy=bool(h.is_global_position_ok and h.is_home_position_ok and h.is_armable),
            flight_mode=getattr(mode, "name", str(mode)),
            mission_current=int(progress.current) if progress else 0,
            mission_total=int(progress.total) if progress else 0,
            mission_finished=self.finished, position_age_s=pos_age, battery_age_s=bat_age,
        )
        snapshot.validate()
        return snapshot

    async def land(self) -> None:
        await self.system.action.land()
        # Recovery needs fresh landing/arming state, not a mission-completion RPC.
        self.started = False

    async def close(self) -> None:
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        if self.system is not None:
            # The pinned gRPC wrapper has no public async close method. This is
            # its own documented-in-source cleanup hook, not a vehicle command.
            # It stops only the client-owned mavsdk_server, not PX4/Gazebo.
            self.system._stop_mavsdk_server()
