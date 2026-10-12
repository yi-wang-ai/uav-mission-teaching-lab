"""Reject misleading evidence, altered files and incomplete baseline sets."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from uav_lab.config import MissionConfig
from uav_lab.demo import DemoVehicle
from uav_lab.evidence import audit_run, audit_baseline
from uav_lab.model import DemoClock
from uav_lab.runner import run_mission


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'run'
        config, clock = MissionConfig(), DemoClock()
        asyncio.run(run_mission(DemoVehicle(config, clock, 'normal'), config, self.path, clock))

    def test_offline_success_cannot_be_presented_as_px4(self):
        result = audit_run(self.path)
        self.assertFalse(result['accepted'])
        self.assertIn('Synthetic/offline data cannot satisfy the PX4 gate', result['errors'])

    def test_altered_summary_fails_integrity(self):
        path = self.path / 'summary.json'
        path.write_text(path.read_text() + ' ')
        self.assertIn('Checksum mismatch: summary.json', audit_run(self.path)['errors'])

    def test_missing_manifest_entry_is_rejected(self):
        path = self.path / 'SHA256SUMS.json'
        data = json.loads(path.read_text())
        del data['telemetry.csv']
        path.write_text(json.dumps(data))
        self.assertFalse(audit_run(self.path)['accepted'])

    def test_duplicate_runs_are_not_three_baselines(self):
        result = audit_baseline([self.path] * 3)
        self.assertFalse(result['accepted'])
        self.assertIn('Exactly three distinct run directories are required', result['errors'])

    def test_missing_run_is_structured_failure(self):
        self.assertFalse(audit_run(self.path / 'missing')['accepted'])

    def test_path_traversal_is_rejected(self):
        path = self.path / 'SHA256SUMS.json'
        data = json.loads(path.read_text())
        data['../outside'] = '0' * 64
        path.write_text(json.dumps(data))
        self.assertFalse(audit_run(self.path)['accepted'])


class ULogSampleTests(unittest.TestCase):
    def test_completed_flight_states(self):
        from uav_lab.evidence import audit_flight_samples
        self.assertTrue(all(audit_flight_samples([1, 0, 1], [1, 2, 1], [0, 1], 4001).values()))

    def test_unknown_arming_state_is_not_disarmed(self):
        from uav_lab.evidence import audit_flight_samples
        self.assertFalse(audit_flight_samples([1, 0, 1], [1, 2, 0], [0, 1], 4001)['disarmed_at_end'])

    def test_landing_without_mission_completion_fails(self):
        from uav_lab.evidence import audit_flight_samples
        self.assertFalse(all(audit_flight_samples([1, 0, 1], [1, 2, 1], [0], 4001).values()))

    def test_empty_ulog_topics_fail(self):
        from uav_lab.evidence import audit_flight_samples
        self.assertFalse(all(audit_flight_samples([], [], [], 4001).values()))
