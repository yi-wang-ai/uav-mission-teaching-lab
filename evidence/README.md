# Evidence included in this release

`validation.json`, `unit-tests.txt`, `build-environment.json`, and
`package-build.txt` record checks actually executed while creating this release.

Every `demo-*` folder contains **synthetic software-test-double data**. No PX4,
Gazebo or physical aircraft generated these records. Virtual demo seconds are
not real elapsed flight time and must not be used as UAV performance claims.

Each demo folder contains a labelled report, telemetry, event log, run manifest
and checksums. The source hash identifies the application code that generated
that run; the config hash identifies the effective configuration.

Do not replace these files with a successful-looking simulator result unless
that simulator experiment actually ran. Add genuine PX4 evidence separately.
