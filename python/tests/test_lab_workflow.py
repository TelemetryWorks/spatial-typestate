"""Example tests: import native code only from the installed wheel, even with -I."""
from array import array
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "lab_workflow.py"
spec = importlib.util.spec_from_file_location("lab_workflow", EXAMPLE)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
FIXTURE = EXAMPLE.with_name("data") / "synthetic_sensor_100hz.csv"


class LabWorkflowTests(unittest.TestCase):
    def test_all_samples_against_independent_analytic_oracle(self):
        times, values = lab.load_csv(FIXTURE)
        self.assertEqual(len(times), 201)
        self.assertEqual(list(times), [i / 100 for i in range(201)])
        report, result, restored, _, _ = lab.analyze(times, values)
        actual, roundtrip = result.view(), restored.view()
        self.assertTrue(actual.readonly)
        self.assertIs(actual.obj, result.view().obj)
        for i in range(201):
            # Algebra, not the implementation's matrix: Rz90 then Rx90.
            x, y, z = 30 + .02 * i, -2 + .005 * i, 3 + .001 * i
            expected = (11 - .3048 * y, 17 - .3048 * z, 32 + .3048 * x)
            for axis in range(3):
                self.assertAlmostEqual(actual[3*i + axis], expected[axis], delta=1e-10)
                self.assertAlmostEqual(roundtrip[3*i + axis], .3048 * (x, y, z)[axis], delta=1e-10)
        for actual, expected in zip(report["world_first_m"], (11.6096, 16.0856, 41.144)):
            self.assertAlmostEqual(actual, expected, delta=1e-10)
        for actual, expected in zip(report["world_last_m"], (11.3048, 16.02464, 42.3632)):
            self.assertAlmostEqual(actual, expected, delta=1e-10)
        for actual, expected in zip(report["world_sensor_x_direction"], (0., 0., 1.)):
            self.assertAlmostEqual(actual, expected, delta=1e-12)

    def test_real_errors_first_row_and_fresh_input_readback(self):
        _, _, _, mapping, sensor = lab.analyze(array("d", [0.]), array("d", [0., 0., 0.]))
        diagnostics = lab.demonstrate_errors(mapping, sensor)
        self.assertEqual([line.split(":")[0] for line in diagnostics], [
            "FrameMismatch index=None", "UnitMismatch index=None",
            "NonFinite index=1", "NonFinite index=1"])

    def test_cli_outside_checkout_and_help(self):
        with tempfile.TemporaryDirectory() as cwd:
            run = subprocess.run([sys.executable, "-I", str(EXAMPLE), "--demonstrate-errors"],
                                 cwd=cwd, capture_output=True, text=True, check=True)
            report = json.JSONDecoder().raw_decode(run.stdout)[0]
            self.assertEqual(report["samples"], 201)
            self.assertIn("synthetic", report["data"])
            self.assertIn("NonFinite index=1", run.stdout)
            help_run = subprocess.run([sys.executable, "-I", str(EXAMPLE), "--help"],
                                      cwd=cwd, capture_output=True, text=True, check=True)
            self.assertIn("SYNTHETIC", help_run.stdout)

    def test_invalid_csv_and_actionable_cli_error(self):
        for text in ["wrong,header\n", "time_s,x_ft,y_ft,z_ft\n", "time_s,x_ft,y_ft,z_ft\n0,1,2\n",
                     "time_s,x_ft,y_ft,z_ft\n0,one,2,3\n", "time_s,x_ft,y_ft,z_ft\n0,1_0,2,3\n",
                     "time_s,x_ft,y_ft,z_ft\ninf,1,2,3\n",
                     "time_s,x_ft,y_ft,z_ft\n0,1,2,3\n0,1,2,3\n"]:
            with tempfile.TemporaryDirectory() as cwd:
                path = Path(cwd) / "bad.csv"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    lab.load_csv(path)
        with tempfile.TemporaryDirectory() as cwd:
            path = Path(cwd) / "nonfinite.csv"
            path.write_text("time_s,x_ft,y_ft,z_ft\n0,1,2,3\n.01,nan,2,3\n", encoding="utf-8")
            run = subprocess.run([sys.executable, "-I", str(EXAMPLE), "--input", str(path)],
                                 cwd=cwd, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("NonFinite, row=1", run.stderr)
            self.assertIn("CSV line=3", run.stderr)
            self.assertNotIn("Traceback", run.stderr)
            self.assertEqual(run.stdout, "")
        with tempfile.TemporaryDirectory() as cwd:
            path = Path(cwd) / "user.csv"
            path.write_text("time_s,x_ft,y_ft,z_ft\n0,1,2,3\n", encoding="utf-8")
            run = subprocess.run([sys.executable, "-I", str(EXAMPLE), "--input", str(path)],
                                 cwd=cwd, capture_output=True, text=True, check=True)
            self.assertIn("illustrative constants, not calibration", json.loads(run.stdout)["data"])
            path.write_text("time_s,x_ft,y_ft,z_ft\n0,1,2,3\n", encoding="utf-8-sig")
            self.assertEqual(list(lab.load_csv(path)[1]), [1., 2., 3.])
            path.write_text("time_s,x_ft,y_ft,z_ft\n0," + "1" * 140000 + ",2,3\n", encoding="utf-8")
            run = subprocess.run([sys.executable, "-I", str(EXAMPLE), "--input", str(path)],
                                 cwd=cwd, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn("Traceback", run.stderr)
            self.assertEqual(run.stdout, "")


if __name__ == "__main__":
    unittest.main()
