"""Read-only gate for three application run folders; never launches a vehicle."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uav_lab.evidence import audit_baseline

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('runs', nargs=3, type=Path)
args = parser.parse_args()
result = audit_baseline(args.runs)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['accepted'] else 1)
