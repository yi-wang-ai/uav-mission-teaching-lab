import asyncio
from importlib import metadata, util
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

from uav_lab.config import MissionConfig
from uav_lab.geometry import Home, build_waypoints
from uav_lab.model import DemoClock, LabError, TelemetryNotReady
from uav_lab.px4 import MAVSDK_GRPC_VERSION, Px4Vehicle, SYSTEM_ADDRESS, make_mavsdk_plan


class FakeItem:
    CameraAction = NS(NONE="NONE")
    VehicleAction = NS(TAKEOFF="TAKEOFF", NONE="NONE")

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakePlan:
    def __init__(self, items):
        self.mission_items = items


class PlanTests(unittest.TestCase):
    def test_first_item_is_explicit_takeoff(self):
        points = build_waypoints(MissionConfig(), Home(47, 8, 400))
        plan = make_mavsdk_plan(points, FakeItem, FakePlan)
        self.assertEqual(len(plan.mission_items), 5)
        self.assertEqual(plan.mission_items[0].vehicle_action, "TAKEOFF")
        self.assertTrue(all(p.vehicle_action == "NONE" for p in plan.mission_items[1:]))
        self.assertEqual(plan.mission_items[0].relative_altitude_m, 10)

    def test_connection_is_loopback_only(self):
        self.assertEqual(SYSTEM_ADDRESS, "udpin://127.0.0.1:14540")

    def test_confirmation_required_before_import_or_connection(self):
        with self.assertRaisesRegex(LabError, "confirm-sitl"):
            Px4Vehicle(MissionConfig(), DemoClock())


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = DemoClock()
        self.system = NS(
            mission=NS(is_mission_finished=AsyncMock(return_value=False),
                       set_return_to_launch_after_mission=AsyncMock(), upload_mission=AsyncMock(),
                       start_mission=AsyncMock()),
            action=NS(arm=AsyncMock(), land=AsyncMock()),
            _stop_mavsdk_server=Mock(),
        )
        self.vehicle = Px4Vehicle(MissionConfig(), self.clock, confirm_sitl=True, _system=self.system)
        self.vehicle.cache.update({
            "connection": NS(is_connected=True),
            "position": NS(latitude_deg=47, longitude_deg=8, relative_altitude_m=0),
            "home": NS(latitude_deg=47, longitude_deg=8, absolute_altitude_m=488),
            "battery": NS(remaining_percent=0.9),
            "health": NS(is_global_position_ok=True, is_home_position_ok=True, is_armable=True),
            "in_air": False, "armed": False, "mode": NS(name="READY"),
        })
        self.vehicle.updated.update({k: 0 for k in self.vehicle.cache})

    async def test_snapshot_maps_expected_fields(self):
        s = await self.vehicle.snapshot()
        self.assertTrue(s.healthy)
        self.assertEqual(s.battery_fraction, 0.9)
        self.assertEqual(s.flight_mode, "READY")

    async def test_missing_stream_is_not_ready(self):
        del self.vehicle.cache["home"]
        with self.assertRaises(TelemetryNotReady):
            await self.vehicle.snapshot()

    async def test_state_change_streams_are_not_treated_as_stale(self):
        self.clock.t = 100
        self.vehicle.updated["position"] = 100
        self.vehicle.updated["battery"] = 100
        s = await self.vehicle.snapshot()
        self.assertTrue(s.healthy)

    async def test_periodic_stream_staleness_is_rejected(self):
        self.clock.t = 6
        with self.assertRaisesRegex(LabError, "stale"):
            await self.vehicle.snapshot()

    async def test_disconnection_is_failure(self):
        self.vehicle.cache["connection"] = NS(is_connected=False)
        with self.assertRaisesRegex(LabError, "lost"):
            await self.vehicle.snapshot()

    async def test_stream_errors_are_not_silent(self):
        self.vehicle.errors["position"] = "position RPC failed"
        with self.assertRaisesRegex(LabError, "RPC failed"):
            await self.vehicle.snapshot()

    async def test_previous_mission_not_queried_before_new_start(self):
        await self.vehicle.snapshot()
        self.system.mission.is_mission_finished.assert_not_awaited()

    async def test_completion_is_latched(self):
        self.vehicle.started = True
        self.system.mission.is_mission_finished.return_value = True
        self.assertTrue((await self.vehicle.snapshot()).mission_finished)
        self.assertTrue((await self.vehicle.snapshot()).mission_finished)
        self.system.mission.is_mission_finished.assert_awaited_once()

    async def test_freshness_is_checked_after_a_slow_rpc(self):
        self.vehicle.started = True
        async def delayed_result():
            self.clock.t = 10
            return False
        self.system.mission.is_mission_finished.side_effect = delayed_result
        with self.assertRaisesRegex(LabError, "stale"):
            await self.vehicle.snapshot()

    async def test_recovery_does_not_depend_on_mission_rpc(self):
        self.vehicle.started = True
        await self.vehicle.land()
        self.assertFalse(self.vehicle.started)
        await self.vehicle.snapshot()
        self.system.mission.is_mission_finished.assert_not_awaited()

    async def test_reported_home_used(self):
        self.assertEqual(await self.vehicle.get_home(), Home(47, 8, 488))

    async def test_upload_requests_rtl(self):
        route = build_waypoints(MissionConfig(), Home(47, 8, 488))
        sentinel = object()
        with patch("uav_lab.px4.make_mavsdk_plan", return_value=sentinel):
            await self.vehicle.upload(route)
        self.system.mission.set_return_to_launch_after_mission.assert_awaited_once_with(True)
        self.system.mission.upload_mission.assert_awaited_once_with(sentinel)

    async def test_wrong_airframe_is_rejected_before_commands(self):
        async def states():
            yield NS(is_connected=True)
        self.system.connect = AsyncMock()
        self.system.core = NS(connection_state=states)
        self.system.param = NS(get_param_int=AsyncMock(return_value=999))
        with self.assertRaisesRegex(LabError, "refusing airframe"):
            await self.vehicle.connect()
        self.system.action.arm.assert_not_awaited()
        self.system.connect.assert_awaited_once_with(system_address=SYSTEM_ADDRESS)

    async def test_stream_exception_is_captured(self):
        async def broken():
            yield NS(latitude_deg=47)
            raise RuntimeError("test RPC failure")
        await self.vehicle._watch("position", broken())
        self.assertIn("test RPC failure", self.vehicle.errors["position"])

    async def test_cleanup_stops_only_owned_sdk_server(self):
        async def waiting():
            while True:
                await asyncio.sleep(100)
                yield False
        task = asyncio.create_task(self.vehicle._watch("in_air", waiting()))
        self.vehicle.tasks.append(task)
        await asyncio.sleep(0)
        await self.vehicle.close()
        self.assertTrue(task.done())
        self.system._stop_mavsdk_server.assert_called_once()
        self.system.action.land.assert_not_awaited()


@unittest.skipUnless(util.find_spec("mavsdk_grpc") is not None,
                     "optional MAVSDK package not installed; not an integration test")
class InstalledMavsdkContractTests(unittest.TestCase):
    def test_pinned_library_accepts_mission_item_fields(self):
        self.assertEqual(metadata.version("mavsdk-grpc"), MAVSDK_GRPC_VERSION)
        route = build_waypoints(MissionConfig(), Home(47, 8, 488))
        plan = make_mavsdk_plan(route)
        self.assertEqual(len(plan.mission_items), 5)

    def test_pinned_library_has_cleanup_hook(self):
        from mavsdk_grpc import System
        self.assertTrue(callable(getattr(System, "_stop_mavsdk_server", None)))
