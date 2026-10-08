# Primary sources checked on 8 October 2026

These sources informed the integration target and setup notes. They do not
constitute evidence that this project has run PX4 successfully.

1. **PX4 v1.17.0 release and source pin**
   https://github.com/PX4/PX4-Autopilot/releases/tag/v1.17.0
   The annotated tag resolves to commit
   `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`.
   Tag object checked through GitHub:
   https://api.github.com/repos/PX4/PX4-Autopilot/git/tags/a5eb12d2ab591251faa009f76b2685b8cc64405d

2. **PX4 v1.17 Ubuntu development environment**
   https://docs.px4.io/v1.17/en/dev_setup/dev_env_linux_ubuntu
   Source for Ubuntu 22.04/24.04 setup and the `--no-nuttx` option.

3. **PX4 v1.17 Gazebo simulation**
   https://docs.px4.io/v1.17/en/sim_gazebo_gz/
   Source for the x500 target, airframe 4001 and headless launch.

4. **MAVSDK gRPC package and rename notice**
   https://pypi.org/project/mavsdk-grpc/4.0.5/
   The gRPC wrapper is installed as `mavsdk-grpc` and imported as
   `mavsdk_grpc`. The package named `mavsdk` now uses a different native API.
   Main dependencies are version-pinned in `pyproject.toml`.

5. **Official gRPC mission example and generated API**
   https://github.com/mavlink/MAVSDK-Python/blob/main/examples/mission.py
   https://github.com/mavlink/MAVSDK-Python/blob/main/mavsdk/mission.py
   https://github.com/mavlink/MAVSDK-Python/blob/main/mavsdk/system.py
   Checked mission-item fields, connection interface and SDK server cleanup.
   Source files were inspected; the optional Python package was not installed
   in this release's validation environment. Source-file inspection is not an
   installed-package compatibility test.

6. **PX4 v1.17 failsafe simulation guidance**
   https://docs.px4.io/v1.17/en/simulation/failsafes
   Reference for future onboard failsafe work; the current synthetic scenarios
   do not execute these PX4 experiments.

PX4, MAVSDK and Gazebo remain their upstream authors' work and retain their
respective licences. No upstream repository or binary is bundled here.
