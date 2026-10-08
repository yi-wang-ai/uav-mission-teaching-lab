from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from uav_lab.config import MissionConfig, load_config
from uav_lab.geometry import Home, build_waypoints, global_to_offset, offset_to_global
from uav_lab.model import LabError, Snapshot


class ConfigTests(unittest.TestCase):
    def test_default_closed_square(self):
        c = MissionConfig()
        self.assertEqual(len(c.waypoints_ne_m), 5)
        self.assertEqual(sum(math.dist(a, b) for a, b in zip(c.waypoints_ne_m, c.waypoints_ne_m[1:])), 80)

    def test_round_trip_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.json"
            p.write_text(json.dumps(MissionConfig().to_dict()))
            self.assertEqual(load_config(p), MissionConfig())

    def test_unknown_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.json"
            p.write_text('{"altitdue_m": 12}')
            with self.assertRaisesRegex(ValueError, "unknown"):
                load_config(p)

    def test_nonobject_config_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.json"
            p.write_text('[]')
            with self.assertRaises(ValueError):
                load_config(p)

    def test_nonfinite_and_boolean_inputs_rejected(self):
        for value in (float("nan"), float("inf"), True, "10"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MissionConfig(altitude_m=value)

    def test_operating_bounds(self):
        for kwargs in ({"altitude_m": 31}, {"speed_m_s": 0}, {"min_battery_fraction": 0.1},
                       {"mission_timeout_s": 0}, {"poll_interval_s": 10}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MissionConfig(**kwargs)

    def test_far_waypoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "50 m"):
            MissionConfig(waypoints_ne_m=((0, 0), (50, 50), (0, 0)))

    def test_open_route_rejected(self):
        with self.assertRaisesRegex(ValueError, "first and last"):
            MissionConfig(waypoints_ne_m=((0, 0), (10, 0)))

    def test_degenerate_route_rejected(self):
        with self.assertRaisesRegex(ValueError, "length"):
            MissionConfig(waypoints_ne_m=((0, 0), (0, 0)))

    def test_wrong_coordinate_shape_rejected(self):
        for points in (None, [[0, 0], [1, 2, 3], [0, 0]], [[0, 0], [True, 2], [0, 0]]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                MissionConfig(waypoints_ne_m=points)


class GeometryTests(unittest.TestCase):
    def test_home_offset_is_home(self):
        h = Home(47.4, 8.5, 400)
        lat, lon = offset_to_global(h, 0, 0)
        self.assertAlmostEqual(lat, h.latitude_deg)
        self.assertAlmostEqual(lon, h.longitude_deg)

    def test_round_trip_offsets(self):
        for h in (Home(47.4, 8.5, 400), Home(-33.9, 151.2, 0), Home(0, 0, 0)):
            for n, e in ((20, 20), (-20, 10), (0, 0)):
                with self.subTest(home=h, point=(n, e)):
                    nn, ee = global_to_offset(h, *offset_to_global(h, n, e))
                    self.assertAlmostEqual(nn, n, places=5)
                    self.assertAlmostEqual(ee, e, places=5)

    def test_date_line_wrap(self):
        h = Home(0, 179.99999, 0)
        lat, lon = offset_to_global(h, 0, 20)
        self.assertLess(lon, 0)
        self.assertAlmostEqual(global_to_offset(h, lat, lon)[1], 20, places=5)

    def test_invalid_home_rejected(self):
        for args in ((89, 0, 0), (0, 181, 0), (float("nan"), 0, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Home(*args)

    def test_waypoint_altitude_is_relative(self):
        route = build_waypoints(MissionConfig(), Home(47.4, 8.5, 488))
        self.assertEqual(route[0].relative_altitude_m, 10)
        self.assertEqual(route[0].speed_m_s, 3)


class SnapshotTests(unittest.TestCase):
    def good(self):
        return Snapshot(47, 8, 0, 0.8, False, False, True, "READY")

    def test_valid_snapshot(self):
        self.good().validate()

    def test_missing_battery_rejected(self):
        for value in (-1.0, float("nan"), 1.1):
            with self.subTest(value=value), self.assertRaises(LabError):
                replace(self.good(), battery_fraction=value).validate()

    def test_negative_telemetry_age_rejected(self):
        with self.assertRaises(LabError):
            replace(self.good(), position_age_s=-1).validate()

    def test_nonboolean_state_rejected(self):
        with self.assertRaises(LabError):
            replace(self.good(), in_air="false").validate()
