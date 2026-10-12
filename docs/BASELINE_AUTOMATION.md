# Reproducible PX4 baseline

This adds execution tooling, not a claim that a simulator mission has passed.
No physical aircraft belongs in this workflow. Keep the existing pinned PX4,
Gazebo and MAVSDK setup in [PX4_SETUP.md](PX4_SETUP.md).

## Local evidence already checked

On 12 October 2026, macOS ARM64: the actual `mavsdk-grpc==4.0.5` package
installed successfully and all original 60 tests passed without skips.
Additional evidence-gate tests were added; see the dated validation record.
Package-contract tests are not simulator flights.

## GitHub Actions route

The new **PX4 baseline (manual, simulation only)** workflow is manual only.
After the changes have been published to GitHub, choose Actions, select that
workflow and choose Run workflow. Check available Actions minutes first.
This workflow has not been executed by this local validation session.

It uses a fresh Ubuntu 24.04 runner, installs the pinned Python adapter,
checks its API contract, fetches the exact PX4 commit, installs the upstream
simulator toolchain, builds without flying, then attempts three missions.
Each attempt restarts the simulator process. Default parameters persist
between restarts; parameter snapshots are retained for comparison. This is
not a guarantee that all hidden simulator state has been reset.

Failure stops the sequence. The artifact-upload step runs even on failure.
Download its `px4-baseline-...` artifact before the 14-day retention expires.
A red workflow with retained logs is useful diagnostic evidence, not a success.

## Existing dedicated Linux host

After completing setup and installed-package checks in PX4_SETUP.md:

```bash
python -m pip install pyulog==1.2.4
cd vendor/PX4-Autopilot
DONT_RUN=1 make px4_sitl gz_x500
cd ../..
python scripts/run_sitl_baseline.py --confirm-sitl --output runs/baseline-01
```

The harness refuses macOS, a changed PX4 revision, modified tracked PX4 files,
and uninitialised or changed submodules. It waits for the simulator's readiness
message, then lets the application enforce its own readiness and freshness checks.
It does not alter arming checks, RTL altitude, or failsafe settings.

## Acceptance and evidence

Each run retains application records, simulator/runner output, PX4 and application
revisions, ULog, ULog-derived initial parameters, observation checks and checksums.
The ULog reader checks airborne state, arming, mission completion and final
landing/disarming independently of application summary flags. These sampled
checks support a baseline demonstration; they do not establish flight safety,
tracking accuracy, or onboard failsafe behaviour.

The read-only application gate can also run separately:

```bash
python scripts/check_baseline.py runs/baseline-01/run-01/mission \
  runs/baseline-01/run-02/mission runs/baseline-01/run-03/mission
```

That command checks application files only. The full harness additionally checks
ULogs. A checksum detects accidental changes, not fabricated data or authorship.
Offline demos are explicitly rejected as PX4 evidence. Recovery landing does not
turn a failed mission into an accepted baseline. No fault-injection milestone
starts before the three baseline runs pass.
