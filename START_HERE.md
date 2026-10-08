# First session: run the software on your Mac

The goal today is to verify the project on your computer and understand the
report. Installing PX4 is the next step, not a prerequisite for this session.

## 1. Extract and enter the folder

Extract `uav-mission-teaching-lab-v0.1.0.zip`. In Terminal, enter the extracted
`uav-mission-teaching-lab` directory. For example, when it is in Downloads:

```bash
cd ~/Downloads/uav-mission-teaching-lab
python3 --version
```

Python **3.10 or newer** is needed. Do not try the project with an older Python.
No packages need to be installed for the commands below.

## 2. Inspect the environment and run tests

```bash
python3 -m uav_lab doctor
python3 -m unittest discover -s tests -v
```

Two optional dependency-contract tests are skipped when `mavsdk-grpc` is absent.
That is expected for this session. The other tests should pass. The doctor
command is read-only; it does not connect to aircraft or change your machine.

## 3. Run the normal offline demonstration

```bash
python3 -m uav_lab demo --config configs/square.json --output runs/first-demo
open runs/first-demo/report.html
```

Expected console messages include `Backend: offline-demo`, the synthetic-data
warning, and `Status: completed`. The completion describes the software test
double, not a PX4 or physical flight.

On Linux, open the HTML file with your browser instead of the macOS `open`
command. The report needs no internet connection.

## 4. Inspect one controlled failure

```bash
python3 -m uav_lab demo --scenario low-battery --output runs/low-battery-demo
open runs/low-battery-demo/report.html
```

Expected result: `failed`, with `arm_attempted: false`. Exit code 1 is deliberate.
There should be no `arm_requested` event. This is an application preflight check,
not a test of PX4's in-flight battery failsafe.

For a repeat run, omit `--output` to create a new timestamped directory. Do not
remove previous evidence just to reuse its name.

## What to look at

Read `uav_lab/runner.py` alongside `events.jsonl`. Identify the difference between
an acknowledged command, an airborne observation and a confirmed landing.
Then change the square side from 20 to 15 in a copy of `configs/square.json` and
explain what changed. Keep the first and last point at `[0, 0]`.

## Next session

Use the `doctor` output to choose a suitable Linux simulator environment.
Do not assume a previous cloud machine still exists or purchase another one
just for this initial exercise. The detailed Linux instructions are in
`docs/PX4_SETUP.md`.
