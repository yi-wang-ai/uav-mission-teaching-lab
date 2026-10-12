"""Read-only acceptance checks. Hashes detect accidental changes, not fabrication."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

PIN = 'd6f12ad1c4f70ad3230afd7d86e971421e02fef4'
REQUIRED = {'config.json', 'manifest.json', 'summary.json', 'telemetry.csv', 'events.jsonl', 'resolved_mission.json', 'report.html'}


def audit_run(folder: Path) -> dict:
    errors = []
    report = {'run': str(folder), 'accepted': False, 'errors': errors,
              'scope': 'application evidence gate; independent ULog review still required'}
    try:
        hashes = json.loads((folder / 'SHA256SUMS.json').read_text())
        if not isinstance(hashes, dict) or not REQUIRED.issubset(hashes):
            raise ValueError('Incomplete evidence checksum manifest')
        for name, expected in hashes.items():
            if Path(name).name != name or (folder / name).is_symlink():
                raise ValueError('Unsafe evidence filename')
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                errors.append(f'Checksum mismatch: {name}')
        manifest = json.loads((folder / 'manifest.json').read_text())
        summary = json.loads((folder / 'summary.json').read_text())
        report['backend'] = manifest.get('backend')
        report['started_utc'] = manifest.get('started_utc')
        report['source_sha256'] = manifest.get('source_sha256')
        report['config_sha256'] = manifest.get('config_sha256')
        if manifest.get('backend') != 'px4-sitl' or summary.get('backend') != 'px4-sitl':
            errors.append('Synthetic/offline data cannot satisfy the PX4 gate')
        for key in ('source_sha256', 'config_sha256'):
            if not isinstance(manifest.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', manifest[key]):
                errors.append(f'Missing or invalid provenance: {key}')
        if datetime.fromisoformat(manifest.get('started_utc', '')).tzinfo is None:
            errors.append('Start time must include timezone')
        if summary.get('status') != 'completed' or summary.get('recovery') != 'not_needed' or summary.get('error') is not None:
            errors.append('Mission failed or required recovery')
        for flag in ('airborne_observed', 'mission_finished_observed', 'landing_observed'):
            if summary.get(flag) is not True:
                errors.append(f'Missing observed outcome: {flag}')
        events = [json.loads(line)['event'] for line in (folder / 'events.jsonl').read_text().splitlines()]
        required_events = ['airborne_observed', 'mission_finished_observed', 'landing_and_disarm_observed']
        if not all(event in events for event in required_events):
            errors.append('Missing observation events')
        elif [events.index(e) for e in required_events] != sorted(events.index(e) for e in required_events):
            errors.append('Observation events are out of order')
        with (folder / 'telemetry.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != summary.get('recorded_samples') or not rows:
            errors.append('Telemetry count is inconsistent')
        else:
            if not any(r['in_air'] == 'True' for r in rows):
                errors.append('No airborne telemetry')
            if not any(r['mission_finished'] == 'True' for r in rows):
                errors.append('No mission completion telemetry')
            if rows[-1]['in_air'] != 'False' or rows[-1]['armed'] != 'False':
                errors.append('Final telemetry does not confirm landing and disarming')
        config = json.loads((folder / 'config.json').read_text())
        actual = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        if actual != manifest.get('config_sha256'):
            errors.append('Configuration provenance mismatch')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'Incomplete or invalid evidence: {exc}')
    report['accepted'] = not errors
    return report


def audit_baseline(folders: list[Path]) -> dict:
    runs = [audit_run(p) for p in folders]
    errors = []
    if len(folders) != 3 or len({p.resolve() for p in folders}) != 3:
        errors.append('Exactly three distinct run directories are required')
    for key in ('source_sha256', 'config_sha256'):
        values = {r.get(key) for r in runs}
        if len(values) != 1 or None in values:
            errors.append(f'Runs must share a recorded {key}')
    if len({r.get('started_utc') for r in runs}) != 3 or any(not r.get('started_utc') for r in runs):
        errors.append('Three independently recorded start times are required')
    return {'accepted': not errors and all(r['accepted'] for r in runs), 'errors': errors,
            'runs': runs, 'physical_flight_claim': False,
            'limitation': 'Checks application records only. Review matching PX4 ULogs, revision and parameters separately.'}


def audit_flight_samples(landed, arming, finished, autostart) -> dict:
    """PX4 v1.17 VehicleStatus uses DISARMED=1 and ARMED=2.

    These are sampled state checks, not full trajectory or failsafe validation.
    """
    landed, arming, finished = list(landed), list(arming), list(finished)
    return {
        'airborne_recorded': 0 in landed,
        'landed_at_end': bool(landed and landed[-1] == 1),
        'armed_recorded': 2 in arming,
        'disarmed_at_end': bool(arming and arming[-1] == 1),
        'mission_finished_recorded': 1 in finished,
        'x500_parameters': autostart == 4001,
    }
