# macOS local validation

Executed on 8 October 2026 on macOS arm64 with Python 3.14.5.

- Unit suite: 60 discovered, 58 passed, 2 optional MAVSDK dependency tests skipped.
- Normal offline demo: completed, 99 telemetry samples.
- Low-battery offline demo: refused before arming; expected exit code 1.
- Both demos use synthetic software-test data, not PX4/Gazebo flight evidence.
- Docker client exists; daemon connection failed because its socket is absent.
- Gazebo and mavsdk-grpc were not found. No simulator flight or installation was performed.

Raw outputs: doctor.json and unit-tests.txt. Generated Mac reports remain local under runs/ and are excluded from Git. A portable synthetic example is included in evidence/demo-normal/.
