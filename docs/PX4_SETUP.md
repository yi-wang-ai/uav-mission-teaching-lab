# M1: first actual PX4/Gazebo mission

**Status:** instructions and adapter prepared; no PX4/Gazebo run was performed
in the environment that generated this release. The optional MAVSDK dependency
was also unavailable there. Read `VALIDATION.md` before interpreting the tests.

## Selected environment

Use a clean Ubuntu **24.04** Linux environment with Python 3.12 for the initial
simulator baseline. PX4 also documents Ubuntu 22.04 support. Keep PX4, Gazebo and
the Python runner on the **same Linux host** for this first milestone; the runner
accepts only localhost MAVLink. Run the offline work natively on macOS, then use
a suitable Linux machine/VM for this step. This release does not provide or
validate an Apple-Silicon VM configuration.

The baseline is PX4 v1.17.0 at commit
`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`, Gazebo Harmonic, and
`mavsdk-grpc==4.0.5`. The top-level package is pinned; transitive Python and
system packages must be captured from the actual environment with `pip freeze`
and system-package records. This is not a complete binary environment lock.

## 1. Obtain the pinned PX4 source

From the project directory on Linux:

```bash
bash scripts/clone_px4.sh
```

The script downloads PX4 and its submodules to `vendor/PX4-Autopilot`, checks
the expected commit, and refuses to overwrite an existing directory. Internet
access and Git are required. PX4 is not bundled in the project ZIP.

## 2. Install the upstream simulator toolchain

Read the upstream setup script first. The following command changes system
packages, may request sudo, and downloads dependencies. Run it only in the
Linux environment selected for simulation, not in macOS Terminal:

```bash
bash vendor/PX4-Autopilot/Tools/setup/ubuntu.sh --no-nuttx
```

Restart the Linux environment after setup as directed by PX4. `--no-nuttx`
omits the hardware-target toolchain; it does not omit simulator dependencies.
The setup/launch scripts in this repository have been syntax-checked only.

## 3. Install the application's optional adapter dependency

Back in the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[px4]'
python3 -m unittest discover -s tests -v
```

The two package-contract tests should now run instead of skipping. They check
constructor fields and the pinned wrapper's cleanup hook, **not a flight**.
Stop and diagnose any installation/test error before continuing. Installing
`mavsdk` 4.x instead of `mavsdk-grpc` supplies a different API.

## 4. Start the simulator (Terminal A)

```bash
bash scripts/start_px4.sh
```

This runs `HEADLESS=1 make px4_sitl gz_x500` from the pinned checkout.
Headless means the simulator is running without its 3D window. For the graphical
version on a suitable Linux desktop, use `bash scripts/start_px4.sh --gui`.

Wait for PX4 to finish starting. At its `pxh>` console, inspect:

```text
param show SYS_AUTOSTART
param show RTL_RETURN_ALT
```

The first value must be 4001. The second explains why return-to-launch may
climb above the route altitude. Record the relevant parameter configuration;
the application does not disable arming checks or change battery/RC/data-link
failsafe settings.

## 5. Run a single baseline (Terminal B)

Confirm that no real aircraft, USB flight controller, radio or hardware bridge
is connected to this environment. With the simulated vehicle on the ground:

```bash
cd /path/to/uav-mission-teaching-lab
source .venv/bin/activate
python3 -m uav_lab px4 --confirm-sitl --config configs/square.json --output runs/px4-01
```

The runner connects, checks readiness, uploads the home-relative square, arms,
starts the mission, waits for airborne state, then mission completion and
landing/disarming. It requests PX4's configured return-to-launch behaviour.
Do not run a second mission controller at the same time.

A failure generates a report rather than an invented success. After a timeout,
interruption or link loss, inspect the simulator: a recovery command may not
have arrived. Stop a runaway test by stopping the **simulator**, not by adapting
this prototype for physical flight.

## 6. Save evidence before changing anything

```bash
python3 -m uav_lab doctor > runs/px4-01/environment.json
python3 -m pip freeze > runs/px4-01/python-packages.txt
git -C vendor/PX4-Autopilot rev-parse HEAD > runs/px4-01/px4-commit.txt
git -C vendor/PX4-Autopilot submodule status --recursive > runs/px4-01/px4-submodules.txt
git -C vendor/PX4-Autopilot status --short > runs/px4-01/px4-working-tree.txt
find vendor/PX4-Autopilot/build -type f -name '*.ulg'
```

Copy the correct ULog into a separately archived flight-evidence folder and
export the PX4 parameters using its console or QGroundControl. Save launch
settings and a short screen recording when a graphical environment is available.
The report's `SHA256SUMS.json` covers the files present when that report was
finalised; later-added files require their own archive checksums.

## Baseline acceptance gate

Repeat three times from a known simulator starting state, with a new run folder
each time. For **each** run, require observed airborne state, completed mission,
and observed landing plus disarming. Retain failures as well as successes.
Check the HTML report against the ULog; do not treat an ACK as proof of flight.

No low-battery, link-loss or GPS-failure flight experiment is part of this
milestone. Those come after a reliable baseline, with explicitly recorded
onboard failsafe configuration and independent observation.

## Troubleshooting boundaries

Connection timeout: check the simulator is running on the same host and that
no other MAVSDK client occupies port 14540. Readiness timeout: inspect PX4's
health/arming messages instead of disabling checks. Missing wheel: check the
Python version and architecture rather than silently changing dependencies.
An actual software incompatibility should become a recorded issue and test.

Primary setup and API references: [REFERENCES.md](REFERENCES.md).
