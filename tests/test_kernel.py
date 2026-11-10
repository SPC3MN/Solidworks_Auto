"""The geometry kernel beyond swlib (revolve, tilted planes, loft, helix, chamfer, edge selection)
and the closed-form volumes the specs use.

    python3 -m unittest tests.test_kernel -v

HandCalc needs nothing. Kernel builds each op in FreeCADCmd (tests/fc_kernel_checks.py, one start,
about 5 s) and compares it with the hand value; it is skipped when FreeCAD is not found.
"""
import json
import math
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import freecad_run  # noqa: E402
import handcalc as hc  # noqa: E402


class HandCalc(unittest.TestCase):
    def test_revolve_is_pappus(self):
        self.assertAlmostEqual(hc.revolve_volume([(0, 0), (10, 0), (10, 20), (0, 20)]), math.pi * 100 * 20)
        self.assertAlmostEqual(hc.revolve_volume([(5, 0), (10, 0), (10, 4), (5, 4)], 90), math.pi * 75 * 4 / 4)
        self.assertAlmostEqual(hc.revolve_volume([(0, 0), (6, 0), (0, 9)]), math.pi * 36 * 9 / 3)   # a cone, either winding
        self.assertAlmostEqual(hc.revolve_volume([(0, 9), (6, 0), (0, 0)]), math.pi * 36 * 9 / 3)

    def test_lofts(self):
        self.assertAlmostEqual(hc.frustum(40, 20, 30), math.pi * 30 / 3 * (400 + 200 + 100))
        self.assertAlmostEqual(hc.prismatoid(1600, 900, 400, 30), 28000)
        self.assertAlmostEqual(hc.prismatoid(100, 100, 100, 7), 700)

    def test_edges(self):
        self.assertAlmostEqual(hc.fillet_edge(3, 10), (1 - math.pi / 4) * 90)
        self.assertAlmostEqual(hc.chamfer_edge(2, 40), 80)
        # a chamfered rim is a cone frustum less than the cylinder it came from
        self.assertAlmostEqual(hc.chamfer_rim(2, 10), math.pi * 100 * 2 - hc.frustum(20, 16, 2))
        self.assertAlmostEqual(hc.chamfer_rim(2, 10, outside=False), hc.frustum(20, 24, 2) - math.pi * 100 * 2)
        self.assertAlmostEqual(hc.fillet_rim(2, 10), 51.5258, places=4)

    def test_helix_and_tilt(self):
        self.assertAlmostEqual(hc.helix_length(10, 4, 20), 5 * math.hypot(20 * math.pi, 4))
        self.assertAlmostEqual(hc.tilted_hole(8, 20, 0), math.pi * 16 * 20)


@unittest.skipUnless(freecad_run.freecad_cmd(), "FreeCAD not found")
class Kernel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = pathlib.Path(tempfile.mkdtemp(prefix="fckernel_")) / "kernel.json"
        proc, _ = freecad_run.run(ROOT / "tests" / "fc_kernel_checks.py", "FC_JOB", str(out))
        if not out.exists():
            raise RuntimeError(proc.stdout[-2000:] + proc.stderr[-2000:])
        cls.results = json.loads(out.read_text())

    def test_no_error(self):
        self.assertNotIn("error", self.results, self.results.get("error", [""])[0])

    def test_every_op_matches_its_hand_value(self):
        self.assertGreater(len(self.results), 25)
        for name, (got, want) in self.results.items():
            with self.subTest(name):
                if isinstance(want, float) or isinstance(got, float) and not isinstance(want, bool):
                    self.assertAlmostEqual(got, want, delta=max(2e-5 * abs(want), 1e-6), msg=name)
                else:
                    self.assertEqual(got, want, name)


if __name__ == "__main__":
    unittest.main()
