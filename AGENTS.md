# Continuation instructions for a coding assistant

The owner is building a small UAV-instructor portfolio project, not a new flight
controller. Read README.md, VALIDATION.md and docs/PX4_SETUP.md first.

1. Inspect the existing files; do not regenerate or overwrite the whole project.
2. Run `python3 -m uav_lab doctor` and the unittest suite. Preserve the outputs.
3. Keep `offline-demo` visibly labelled synthetic in every derived report.
4. The next milestone is one actual PX4/Gazebo x500 baseline mission on a
   suitable Linux environment, then repeat it three times. Do not jump to ROS,
   SLAM, reinforcement learning, drone swarms or physical aircraft.
5. Confirm OS, architecture and available simulator environment before installing.
   Do not assume the owner's old DigitalOcean instance still exists. Do not
   rent infrastructure, spend money or publish externally without authorisation.
6. Keep the package pin and PX4 revision unless a demonstrated issue justifies a
   documented change. Run the installed-package tests before sending commands.
7. Never remove readiness/freshness checks to make a run succeed. Keep hardware
   bridges disconnected. Localhost and SYS_AUTOSTART checks are not hardware
   identity verification. No physical-flight adaptation belongs in this project.
8. Record failures, source revisions, ULogs and parameter configuration. A sent
   command is not an observed outcome; recovery success is not mission success.
9. Do not claim simulator success, merged PRs, delivered teaching, flight hours
   or licensing from generated starter files or mocked tests.
10. Report exactly what was executed, what passed, what failed and what remains
    untested. Stop after the requested milestone rather than expanding scope.
