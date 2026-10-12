Latest local update: [12 October 2026](evidence/2026-10-12-local/VALIDATION.md).
The record below is historical.

# Validation record — v0.1.0

**Executed on 8 October 2026, using Python 3.13.5 on Linux x86_64.**

## Actual local results

| Check | Result |
|---|---|
| Unit / mocked-adapter / CLI tests | **58 passed, 2 skipped, 0 failed** (60 discovered) |
| Python compilation | Passed |
| Bash helper-script syntax | Passed; the download/install/launch operations were not executed |
| Python wheel build without network dependencies | Passed |
| Four offline CLI scenarios | All returned the expected exit codes |

The two skipped tests require the optional `mavsdk-grpc` package. Its actual
mission-item constructor and cleanup hook have **not** been validated by an
installed-package test here. The PX4 adapter's other tests use injected mocks.

Raw evidence is in `evidence/unit-tests.txt`, `evidence/validation.json`,
`evidence/build-environment.json` and `evidence/package-build.txt`.

## Offline scenario observations

All data below comes from the deterministic software test double. It is **not**
PX4 flight evidence, a dynamics benchmark, or a measure of physical flight time.

| Scenario | Outcome | Recovery / landing evidence |
|---|---|---|
| Normal | Completed; 99 recorded samples | Airborne, mission completion and landing observed in the test double |
| Low battery | Refused before arming | No arm or recovery-land command |
| Mission stall | Mission failed | Recovery landing observed; original mission remains failed |
| Link loss | Mission failed | Recovery unconfirmed; no landing claim |

The generated reports and full records are in `evidence/demo-*`. These are
executable examples of the reporting format, not sample data borrowed from a
real flight or an upstream PX4 run.

## Not yet executed or verified

- PX4 build, Gazebo launch, actual MAVSDK package tests, or a PX4 mission.
- A physical UAV flight or onboard PX4 failsafe experiment.
- Tests on macOS or the owner's own machine.
- The supplied GitHub Actions workflow.
- A delivered lesson, recorded demonstration video or accessibility user test.

The application wheel was built successfully. HTML content is generated and
checked by unit tests for key labels and escaping. Browser rendering could not
be checked because no Chromium executable was installed in the validation
container; no visual-rendering pass is claimed.

## Next acceptance gate

Run the local checks on the owner's machine, then follow `docs/PX4_SETUP.md` for
the first actual simulator mission. Archive three baseline runs with their
ULogs, parameter exports, source revisions and environment records before
claiming PX4 reproduction. Retain any failures and explain them.
