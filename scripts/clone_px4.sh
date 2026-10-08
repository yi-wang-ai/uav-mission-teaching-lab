#!/usr/bin/env bash
# Downloads only; does not run an installer or create a cloud machine.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/vendor/PX4-Autopilot"
EXPECTED="d6f12ad1c4f70ad3230afd7d86e971421e02fef4"
command -v git >/dev/null || { echo "Git is required." >&2; exit 2; }
if [[ -e "$DEST" ]]; then
  echo "Refusing to overwrite $DEST. Inspect the existing checkout first." >&2
  exit 2
fi
mkdir -p "$ROOT/vendor"
git clone --branch v1.17.0 --depth 1 https://github.com/PX4/PX4-Autopilot.git "$DEST"
ACTUAL="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Unexpected source revision: $ACTUAL. Stop and investigate." >&2
  exit 2
fi
git -C "$DEST" submodule update --init --recursive --depth 1
printf 'Pinned PX4 source is ready: %s\nNo system packages were installed. Read docs/PX4_SETUP.md next.\n' "$ACTUAL"
