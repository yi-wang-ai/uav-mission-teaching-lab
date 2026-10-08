#!/usr/bin/env bash
# Launches only the locally checked-out software simulator, never hardware.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4="$ROOT/vendor/PX4-Autopilot"
EXPECTED="d6f12ad1c4f70ad3230afd7d86e971421e02fef4"
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This launch recipe targets Linux. Use the offline demo on macOS." >&2
  exit 2
fi
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--gui" ) ]]; then
  echo "Usage: bash scripts/start_px4.sh [--gui]" >&2
  exit 2
fi
[[ -d "$PX4/.git" ]] || { echo "Run scripts/clone_px4.sh first." >&2; exit 2; }
ACTUAL="$(git -C "$PX4" rev-parse HEAD)"
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo "Unexpected PX4 revision $ACTUAL." >&2; exit 2; }
if [[ -n "$(git -C "$PX4" status --porcelain --untracked-files=no)" ]]; then
  echo "PX4 checkout is modified. Record/review the change before baseline testing." >&2
  exit 2
fi
cd "$PX4"
echo "Starting a local Gazebo x500 SOFTWARE SIMULATOR. Keep all real hardware disconnected."
if [[ "${1:-}" == "--gui" ]]; then
  unset HEADLESS
else
  export HEADLESS=1
fi
exec make px4_sitl gz_x500
