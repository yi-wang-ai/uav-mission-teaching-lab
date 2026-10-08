from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from uav_lab.__main__ import main


class CliTests(unittest.TestCase):
    def test_doctor_is_read_only_and_returns_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["doctor"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out.getvalue())["python_supported"])

    def test_demo_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as out:
            code = main(["demo", "--output", str(Path(tmp) / "normal")])
            self.assertEqual(code, 0)
            self.assertIn("SYNTHETIC", out.getvalue())

    def test_expected_fault_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            code = main(["demo", "--scenario", "low-battery", "--output", str(Path(tmp) / "low")])
            self.assertEqual(code, 1)

    def test_px4_requires_explicit_confirmation(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(["px4"])
        self.assertEqual(exc.exception.code, 2)

    def test_bad_config_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            p = Path(tmp) / "bad.json"
            p.write_text('{"speed_m_s": -10}')
            self.assertEqual(main(["demo", "--config", str(p)]), 2)
