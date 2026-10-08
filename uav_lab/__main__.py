"""CLI: python3 -m uav_lab doctor | demo | px4."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import sys

from . import __version__
from .config import load_config
from .demo import DemoVehicle, SCENARIOS
from .model import DemoClock, LabError, RealClock
from .runner import run_mission


def doctor() -> dict:
    packages = {}
    for name in ("mavsdk-grpc", "grpcio", "protobuf"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "project_version": __version__, "python_version": platform.python_version(),
        "python_executable": sys.executable, "operating_system": platform.system(),
        "os_release": platform.release(), "architecture": platform.machine(),
        "python_supported": sys.version_info >= (3, 10),
        "gazebo_command": shutil.which("gz"), "git_command": shutil.which("git"),
        "packages": packages,
        "note": "Read-only environment check. Does not connect, install, arm, or launch anything.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulation-only UAV mission teaching lab")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("doctor", help="read-only environment check")
    for name, help_text in (("demo", "offline software test double; NOT PX4"), ("px4", "connect to a local PX4/Gazebo x500 simulator")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--config", type=Path, help="mission JSON; defaults to the built-in 20 m square")
        p.add_argument("--output", type=Path, help="new output directory; existing directories are refused")
        if name == "demo":
            p.add_argument("--scenario", choices=SCENARIOS, default="normal")
        else:
            p.add_argument("--confirm-sitl", action="store_true", help="confirm dedicated simulator host with no real vehicle/bridge attached")
    args = parser.parse_args(argv)
    if args.mode == "doctor":
        print(json.dumps(doctor(), indent=2))
        return 0
    if args.mode == "px4" and not args.confirm_sitl:
        parser.error("px4 requires --confirm-sitl; read docs/PX4_SETUP.md first")
    try:
        config = load_config(args.config)
        clock = DemoClock() if args.mode == "demo" else RealClock()
        if args.mode == "demo":
            vehicle = DemoVehicle(config, clock, args.scenario)
            extra = {"scenario": args.scenario, "px4_executed": False}
        else:
            from .px4 import Px4Vehicle
            vehicle = Px4Vehicle(config, clock, confirm_sitl=args.confirm_sitl)
            extra = {"operator_confirmed_sitl": True, "px4_source_revision": "record separately from the simulator checkout"}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output or Path("runs") / f"{args.mode}-{stamp}"
        result = asyncio.run(run_mission(vehicle, config, output, clock, extra))
        print(f"Backend: {result['backend']}")
        if args.mode == "demo":
            print("SYNTHETIC SOFTWARE TEST DATA — not PX4 / Gazebo flight evidence")
        print(f"Status: {result['status']}")
        print(f"Telemetry samples: {result['recorded_samples']}")
        print(f"Report: {output / 'report.html'}")
        if result["error"]:
            print(f"Reason: {result['error']}")
        return 0 if result["status"] == "completed" else (130 if result["status"] == "cancelled" else 1)
    except (ValueError, OSError, LabError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted. Check simulator state; landing is NOT guaranteed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
