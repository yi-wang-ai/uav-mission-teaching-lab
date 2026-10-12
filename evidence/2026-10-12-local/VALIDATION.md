# Local validation — 12 October 2026

Environment: macOS ARM64; exact Python/package versions in installed-doctor.json
and packages.txt. This is local software validation, not a simulator-flight result.

- Original suite before dependency installation: 58 passed, 2 skipped.
- Installed `mavsdk-grpc==4.0.5`: original 60 tests passed, no skips.
- Enhanced suite: 70 passed, no skips, including rejection of synthetic data,
  altered/incomplete manifests, duplicate runs, unknown arming states and missing
  mission-completion samples.
- NumPy-backed state samples were checked for JSON serialisability with pyulog's
  installed dependencies. This is a synthetic software check, not a ULog flight.
- Linux baseline harness refuses to launch on macOS (macos-sitl-refusal.txt).
- Python compilation and shell helper syntax checks passed.

The manual Ubuntu workflow, PX4 build, three actual simulator missions and ULog
cross-check of actual project flights have NOT been executed. No actual flight,
classroom delivery, failsafe validation or GitHub CI success is claimed.

The new harness retains failed attempts and stops instead of weakening readiness
checks. Its application gate cannot convert offline-demo records into PX4 proof.
Hashes provide integrity checks, not proof of authenticity or authorship.
