"""Mission orchestration with bounded waits, evidence logging and best-effort recovery."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .config import MissionConfig
from .geometry import build_waypoints
from .model import Clock, LabError, Snapshot, TelemetryNotReady, Vehicle
from .recording import Recorder, write_json


async def run_mission(vehicle: Vehicle, config: MissionConfig, output: Path,
                      clock: Clock, metadata: dict | None = None) -> dict:
    log = Recorder(output, config, vehicle.backend, metadata)
    armed_attempted = False
    airborne_observed = False
    landing_observed = False
    mission_finished_observed = False
    status, error, recovery = "failed", None, "not_needed"

    def event(kind: str, detail: str = "") -> None:
        log.event(clock.now(), kind, detail)

    async def command(coro, label: str) -> None:
        try:
            await asyncio.wait_for(coro, config.command_timeout_s)
        except asyncio.TimeoutError as exc:
            raise LabError(f"{label} timed out; acknowledgement / execution is uncertain") from exc

    async def wait_until(predicate: Callable[[Snapshot], bool], phase: str,
                         timeout_s: float, startup: bool = False) -> Snapshot:
        deadline = clock.now() + timeout_s
        while clock.now() < deadline:
            try:
                s = await asyncio.wait_for(vehicle.snapshot(), min(config.command_timeout_s, deadline - clock.now()))
                s.validate()
                if max(s.position_age_s, s.battery_age_s) > config.telemetry_max_age_s:
                    raise LabError("stale position or battery telemetry")
                log.sample(clock.now(), phase, s)
                if phase == "preflight":
                    if s.in_air or s.armed:
                        raise LabError("preflight refused: vehicle must start on the ground and disarmed")
                    if s.battery_fraction < config.min_battery_fraction:
                        raise LabError("preflight refused: battery below configured threshold")
                if phase == "mission" and not s.in_air and not s.mission_finished:
                    raise LabError("landing observed before mission completion")
                if predicate(s):
                    return s
            except TelemetryNotReady:
                if not startup:
                    raise
            except asyncio.TimeoutError as exc:
                raise LabError(f"{phase}: telemetry/RPC timeout") from exc
            await clock.sleep(config.poll_interval_s)
        raise LabError(f"{phase} timeout after {timeout_s:g} seconds")

    async def recover() -> str:
        nonlocal landing_observed
        # Never disarm / kill motors in the air. Never treat an ACK as a landing.
        event("recovery_land_requested", "Best effort only; not an onboard failsafe validation")
        try:
            await command(vehicle.land(), "recovery land")
            event("recovery_land_acknowledged")
            await wait_until(lambda s: not s.in_air and not s.armed,
                             "recovery", config.landing_timeout_s)
            landing_observed = True
            event("recovery_landing_observed")
            return "landing_observed"
        except Exception as exc:
            event("recovery_unconfirmed", f"{type(exc).__name__}: {exc}")
            return "unconfirmed"

    try:
        event("run_started", vehicle.backend)
        await asyncio.wait_for(vehicle.connect(), config.connect_timeout_s)
        event("connected")
        await wait_until(lambda s: s.healthy, "preflight", config.ready_timeout_s, startup=True)
        home = await asyncio.wait_for(vehicle.get_home(), config.command_timeout_s)
        route = build_waypoints(config, home)
        write_json(output / "resolved_mission.json", {"home": asdict(home), "waypoints": [asdict(w) for w in route]})
        event("preflight_passed")
        await command(vehicle.upload(route), "upload")
        event("mission_uploaded", f"{len(route)} waypoints; return-and-land requested")
        # Re-check after upload; readiness may have changed while commands were in flight.
        await wait_until(lambda s: s.healthy, "preflight", config.ready_timeout_s, startup=True)
        armed_attempted = True  # An arm timeout may still mean the arm command executed.
        event("arm_requested")
        await command(vehicle.arm(), "arm")
        event("arm_acknowledged")
        await command(vehicle.start_mission(), "start mission")
        event("mission_start_acknowledged")
        await wait_until(lambda s: s.in_air, "takeoff", config.takeoff_timeout_s)
        airborne_observed = True
        event("airborne_observed")
        await wait_until(lambda s: s.mission_finished, "mission", config.mission_timeout_s)
        mission_finished_observed = True
        event("mission_finished_observed")
        await wait_until(lambda s: not s.in_air and not s.armed, "landing", config.landing_timeout_s)
        landing_observed = True
        event("landing_and_disarm_observed")
        status = "completed"
    except asyncio.CancelledError:
        status, error = "cancelled", "operator interrupted the run"
        event("run_cancelled", error)
        if armed_attempted:
            recovery = await recover()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        event("run_failed", error)
        if armed_attempted:
            recovery = await recover()
    finally:
        try:
            await asyncio.wait_for(vehicle.close(), 5.0)
        except Exception as exc:
            event("cleanup_warning", f"{type(exc).__name__}: {exc}")
        event("run_finished", status)
    return log.finish({
        "status": status, "error": error, "elapsed_s": round(clock.now(), 6),
        "arm_attempted": armed_attempted, "airborne_observed": airborne_observed,
        "mission_finished_observed": mission_finished_observed,
        "landing_observed": landing_observed, "recovery": recovery,
    })
