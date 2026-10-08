# UAV Mission Automation and Fault-Diagnosis Teaching Lab

**v0.1.0 — an executable software foundation, not a completed PX4 flight project.**

A small Python application for running a closed UAV waypoint mission, checking
readiness, recording telemetry and explaining failures through a practical lesson.
The default route is a 20 m square at 10 m relative altitude and 3 m/s.

## Latest local validation

Verified on macOS arm64 with Python 3.14.5 on 8 October 2026:

- 58 tests passed; 2 optional MAVSDK package-contract tests skipped.
- Normal offline demonstration completed with 99 telemetry samples.
- Low-battery demonstration correctly refused before arming.
- All demonstration data is synthetic. No PX4/Gazebo mission has been run.

See [Mac validation evidence](evidence/macos-local/VALIDATION.md).
The next milestone is an actual PX4/Gazebo baseline mission on Linux.

## Start here

Open [START_HERE.md](START_HERE.md). The first exercise needs only Python 3.10+;
no drone, simulator, Docker, network connection or third-party Python package is
required for the offline demo and core tests.

```bash
python3 -m uav_lab doctor
python3 -m unittest discover -s tests -v
python3 -m uav_lab demo --config configs/square.json --output runs/first-demo
```

Open `runs/first-demo/report.html` in a browser. Use a new output directory for
each run; existing directories are deliberately refused.

## What is implemented

| Component | Current evidence |
|---|---|
| Strict JSON mission configuration and local-to-global route conversion | Automated tests |
| Readiness checks, bounded commands, mission and landing observation | Offline test-double tests |
| Preflight low-battery refusal, mission stall and link-loss cases | Synthetic scenarios; **not PX4 failsafe experiments** |
| CSV telemetry, JSONL events, JSON summary, HTML report and source/config hashes | Generated and tested locally |
| MAVSDK gRPC adapter for PX4/Gazebo x500 | Implemented; mocked adapter tests; actual package and simulator validation pending |
| Introductory teaching exercise and worksheet | Written; not delivered to students |
| GitHub Actions workflow | Supplied; not executed on GitHub |

See [VALIDATION.md](VALIDATION.md) for actual test counts and environment evidence.
No real aircraft was used, and no simulator flight is claimed by this release.

## Two deliberately separate backends

`demo` uses a deterministic **software test double** with virtual time. It moves
through a prescribed route so the application can be tested without flight
software. It is not a physics simulator or a source of UAV performance results.
Every generated demo report is prominently labelled synthetic.

`px4` uses a local PX4/Gazebo simulator through `mavsdk-grpc==4.0.5`.
The old `from mavsdk import System` tutorials do not describe the new native
`mavsdk` 4.x API. This project explicitly uses the separately maintained gRPC
package and `from mavsdk_grpc import System`. See [references](docs/REFERENCES.md).

The selected simulator baseline is PX4 **v1.17.0**, commit
`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`, Gazebo Harmonic and Ubuntu 24.04.
This is a setup target, **not a stack already tested in this release**.

Follow [docs/PX4_SETUP.md](docs/PX4_SETUP.md) before using:

```bash
python3 -m uav_lab px4 --confirm-sitl --config configs/square.json
```

## Mission lifecycle

```text
Validate configuration
  -> connect to the selected backend
  -> confirm a healthy, disarmed vehicle on the ground
  -> anchor the route to the reported home position
  -> upload the route and request return/landing
  -> check readiness again
  -> arm and start the mission
  -> observe airborne state
  -> observe mission completion
  -> observe landing AND disarming
  -> write the result and report
```

A timeout or RPC error after an arm attempt triggers a best-effort `land`
request. A command acknowledgement is **not** a confirmed landing. Link loss
can prevent both delivery and observation. Recovery never converts a failed
mission into a successful one. The application never sends a motor-kill or
in-flight disarm command.

## Run outputs

Each run directory contains `config.json`, `manifest.json`, `telemetry.csv`,
`events.jsonl`, `summary.json`, `report.html`, and `SHA256SUMS.json`.
After a route has been resolved, `resolved_mission.json` is also present.

The manifest records the backend, time basis, Python/platform details, available
package versions, source hash and configuration hash. For an actual PX4 run,
archive the simulator's revision, parameter export and ULog separately.
Host-receipt telemetry is not time-synchronised ground truth; no trajectory-error
benchmark is computed from it.

Exit codes: `0` completed; `1` mission refused/failed; `2` invalid invocation or
configuration; `130` interrupted. An intentional fault-demo returning `1` is
expected behaviour, not evidence that the unit-test suite failed.

## Layout

```text
uav_lab/               Mission logic, demo backend, PX4 adapter and reporting
configs/square.json    Editable closed-route configuration
tests/                 Standard-library unit and mocked-adapter tests
docs/                  Setup, lesson, worksheet, roadmap and references
scripts/               Pinned PX4 checkout and simulator launch helpers
evidence/              Actual local validation and clearly labelled demo runs
.github/workflows/     Proposed CI workflow
```

## Simulation-only boundary

Do not connect real aircraft, USB flight controllers, serial telemetry radios,
or hardware bridges. PX4 mode requires explicit consent, binds to loopback only,
and checks `SYS_AUTOSTART=4001`. These checks **cannot prove** that a local bridge
is disconnected from physical hardware. Use a dedicated simulator environment.

Configuration limits constrain the requested route; they are not an onboard
geofence. In particular, PX4's configured return altitude can exceed the route's
10 m altitude. Do not disable safety or arming checks to make a test pass.

## Authorship and portfolio use

This is an AI-assisted starter implementation for Yi Wang to review, run and
extend. The project-specific work is the application, tests, evidence structure
and lesson materials—not the PX4 flight controller or MAVSDK itself.
Credit those upstream projects. Do not claim independent flight-control
algorithm development, delivered teaching, a merged PR, actual flight hours,
or completed PX4 failsafe validation from the supplied files.

A useful next milestone is **three recorded baseline missions on the same pinned
PX4 setup**, starting from a known simulator state. See [the roadmap](docs/ROADMAP.md).
