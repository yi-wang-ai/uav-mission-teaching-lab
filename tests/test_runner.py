import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from uav_lab.config import MissionConfig
from uav_lab.demo import DemoVehicle
from uav_lab.model import DemoClock, LabError
from uav_lab.runner import run_mission


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "run"
        self.clock = DemoClock()
        self.config = MissionConfig()

    async def run_case(self, scenario="normal", cls=DemoVehicle):
        self.vehicle = cls(self.config, self.clock, scenario)
        self.result = await run_mission(self.vehicle, self.config, self.output, self.clock)
        return self.result

    def events(self):
        return [json.loads(line)["event"] for line in (self.output / "events.jsonl").read_text().splitlines()]

    async def test_normal_mission_completes_and_lands(self):
        r = await self.run_case()
        self.assertEqual(r["status"], "completed")
        self.assertTrue(r["airborne_observed"])
        self.assertTrue(r["mission_finished_observed"])
        self.assertTrue(r["landing_observed"])
        self.assertEqual(self.vehicle.commands, ["connect", "upload", "arm", "start_mission"])
        self.assertTrue(self.vehicle.closed)

    async def test_low_battery_never_arms(self):
        r = await self.run_case("low-battery")
        self.assertEqual(r["status"], "failed")
        self.assertFalse(r["arm_attempted"])
        self.assertNotIn("arm", self.vehicle.commands)
        self.assertNotIn("land", self.vehicle.commands)

    async def test_stalled_mission_remains_failed_after_recovery(self):
        self.config = replace(self.config, mission_timeout_s=20)
        r = await self.run_case("mission-stall")
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["recovery"], "landing_observed")
        self.assertTrue(r["landing_observed"])
        self.assertFalse(r["mission_finished_observed"])
        self.assertIn("land", self.vehicle.commands)

    async def test_link_loss_never_claims_landed(self):
        r = await self.run_case("link-loss")
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["recovery"], "unconfirmed")
        self.assertFalse(r["landing_observed"])
        self.assertIn("recovery_unconfirmed", self.events())

    async def test_connect_failure_still_writes_report(self):
        class Broken(DemoVehicle):
            async def connect(self):
                raise LabError("connect failed")
        r = await self.run_case(cls=Broken)
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["recorded_samples"], 0)
        self.assertIsNone(r["observed_max_altitude_m"])
        self.assertTrue((self.output / "report.html").is_file())

    async def test_unhealthy_preflight_times_out(self):
        class Unhealthy(DemoVehicle):
            async def snapshot(self):
                return replace(await super().snapshot(), healthy=False)
        self.config = replace(self.config, ready_timeout_s=2)
        r = await self.run_case(cls=Unhealthy)
        self.assertFalse(r["arm_attempted"])
        self.assertIn("preflight timeout", r["error"])

    async def test_already_armed_vehicle_refused(self):
        class Armed(DemoVehicle):
            async def snapshot(self):
                return replace(await super().snapshot(), armed=True)
        r = await self.run_case(cls=Armed)
        self.assertFalse(r["arm_attempted"])
        self.assertNotIn("land", self.vehicle.commands)

    async def test_never_airborne_cannot_be_success(self):
        class NeverAir(DemoVehicle):
            async def snapshot(self):
                return replace(await super().snapshot(), in_air=False)
        self.config = replace(self.config, takeoff_timeout_s=2)
        r = await self.run_case(cls=NeverAir)
        self.assertEqual(r["status"], "failed")
        self.assertFalse(r["airborne_observed"])
        self.assertIn("takeoff timeout", r["error"])

    async def test_premature_landing_is_failure(self):
        class PrematureLanding(DemoVehicle):
            async def snapshot(self):
                s = await super().snapshot()
                if self.started_at is not None and self.clock.now() > 5:
                    return replace(s, in_air=False, armed=False, mission_finished=False)
                return s
        r = await self.run_case(cls=PrematureLanding)
        self.assertEqual(r["status"], "failed")
        self.assertIn("before mission completion", r["error"])

    async def test_stale_telemetry_refused(self):
        class Stale(DemoVehicle):
            async def snapshot(self):
                return replace(await super().snapshot(), position_age_s=20)
        r = await self.run_case(cls=Stale)
        self.assertIn("stale", r["error"])
        self.assertFalse(r["arm_attempted"])

    async def test_upload_does_not_bypass_second_readiness_check(self):
        class DegradingBattery(DemoVehicle):
            async def snapshot(self):
                s = await super().snapshot()
                return replace(s, battery_fraction=0.1) if self.uploaded else s
        r = await self.run_case(cls=DegradingBattery)
        self.assertIn("upload", self.vehicle.commands)
        self.assertNotIn("arm", self.vehicle.commands)
        self.assertFalse(r["arm_attempted"])

    async def test_ambiguous_arm_timeout_attempts_recovery(self):
        class SlowArm(DemoVehicle):
            async def arm(self):
                await super().arm()
                await asyncio.sleep(1)
        self.config = replace(self.config, command_timeout_s=0.1)
        r = await self.run_case(cls=SlowArm)
        self.assertTrue(r["arm_attempted"])
        self.assertIn("land", self.vehicle.commands)
        self.assertIn("uncertain", r["error"])

    async def test_cancellation_is_recorded_and_recovery_attempted(self):
        class Interrupted(DemoVehicle):
            async def start_mission(self):
                raise asyncio.CancelledError()
        r = await self.run_case(cls=Interrupted)
        self.assertEqual(r["status"], "cancelled")
        self.assertIn("land", self.vehicle.commands)
        self.assertTrue(self.vehicle.closed)

    async def test_existing_output_not_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("original")
        v = DemoVehicle(self.config, self.clock)
        with self.assertRaises(FileExistsError):
            await run_mission(v, self.config, self.output, self.clock)
        self.assertEqual(sentinel.read_text(), "original")
        self.assertEqual(v.commands, [])

    async def test_report_is_labelled_and_html_escaped(self):
        self.config = replace(self.config, name="<script>alert(1)</script>")
        await self.run_case()
        report = (self.output / "report.html").read_text()
        self.assertIn("OFFLINE DEMO", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertNotIn("<script>alert", report)

    async def test_all_evidence_hashes_match(self):
        await self.run_case()
        hashes = json.loads((self.output / "SHA256SUMS.json").read_text())
        for name, digest in hashes.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), digest)
        self.assertIn("resolved_mission.json", hashes)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["backend"], "offline-demo")
        self.assertEqual(manifest["time_basis"], "virtual demo seconds")
