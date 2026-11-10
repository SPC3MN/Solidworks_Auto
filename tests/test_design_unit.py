"""Fast checks of the drafting phase's pure-Python parts (no FreeCAD, no Blender), on the
example product products/example_pi_zero_case.

    python3 -m unittest tests.test_design_unit -v
"""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import design_board  # noqa: E402
import design_cli  # noqa: E402
import draft_lib as D  # noqa: E402
import sketch  # noqa: E402

EXAMPLE = ROOT / "products" / "example_pi_zero_case"
ROUND1 = EXAMPLE / "draft" / "round_1"


class Expressions(unittest.TestCase):
    def test_arithmetic(self):
        self.assertAlmostEqual(D.evaluate("a + 2*b - max(a, 3)/2", {"a": 4, "b": 1.5}), 5.0)
        self.assertAlmostEqual(D.evaluate(7, {}), 7.0)

    def test_rejects_code(self):
        for bad in ("__import__('os')", "a.real", "[1][0]", "open('x')", "unknown + 1", "1/0", "True"):
            with self.assertRaises(D.DraftError, msg=bad):
                D.evaluate(bad, {"a": 1})

    def test_params_any_order_and_cycle(self):
        p = D.resolve_params({"c": "a + b", "a": {"value": 2, "src": "given"}, "b": "a * 3", "_note": "ignored"})
        self.assertEqual((p["c"]["value"], p["a"]["src"], p["b"]["src"]), (8.0, "given", "chosen"))
        with self.assertRaises(D.DraftError):
            D.resolve_params({"a": "b", "b": "a"})


class Geometry(unittest.TestCase):
    def body(self, **b):
        return D.resolve_body(b, {}, "test")

    def test_bored_cylinder_section_is_two_walls(self):
        tube = self.body(type="cyl", d=20, h=30, bore=10, at=[0, 0, 5])
        walls = D.section(tube, 0)
        self.assertEqual([s[0][1] for s in walls], [[(-10, 5), (-5, 5), (-5, 35), (-10, 35)], [(5, 5), (10, 5), (10, 35), (5, 35)]])
        self.assertEqual(len(D.section(tube, 6)), 1)   # past the bore: one chord
        self.assertIsNone(D.section(tube, 10))         # tangent: nothing cut

    def test_revolve(self):
        cup = self.body(type="revolve", profile=[[0, 0], [10, 0], [10, 20], [8, 20], [8, 2], [0, 2]])
        self.assertEqual(D.bbox3(cup), ([-10, -10, 0], [10, 10, 20]))
        self.assertEqual(len(D.section(cup, 0)), 2)    # the profile and its mirror
        self.assertIsNone(D.section(cup, 3))           # off the axis: drawn as an outline
        sil, steps = D.outline(cup, "y")
        self.assertEqual({round(abs(u), 6) for u, _ in sil[0][1]}, {10.0})  # the silhouette is the outer wall
        top, hidden = D.outline(cup, "z")
        self.assertEqual((top[0][0], top[0][2], hidden), ("circle", 10, []))

    def test_prism_section_strips(self):
        u = self.body(type="prism", axis="z", h=4, profile=[[0, 0], [30, 0], [30, 10], [20, 10], [20, 3], [10, 3], [10, 10], [0, 10]])
        strips = D.section(u, 5)                       # across the two legs of the U
        self.assertEqual([(s[0][1][0][0], s[0][1][1][0]) for s in strips], [(0, 10), (20, 30)])
        self.assertEqual(len(D.section(u, 1)), 1)

    def test_box_rules(self):
        with self.assertRaises(D.DraftError):
            self.body(type="box", size=[10, 4, 2], r=3)


class ExampleRound(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = D.load_brief(EXAMPLE)
        cls.opts = [D.load_option(ROUND1 / o) for o in "ABC"]
        cls.reqs = {o["id"]: D.requirement_results(cls.brief, o) for o in cls.opts}

    def test_scorecards(self):
        a, b, c = (o["scorecard"] for o in self.opts)
        self.assertEqual((a["parts_total"], b["parts_total"], c["parts_total"], c["fasteners"]), (2, 3, 7, 4))
        self.assertEqual([round(v, 3) for v in self.opts[0]["bbox"][1]], [32.65, 16.9, 8.7])

    def test_round_is_ready(self):
        self.assertEqual(design_cli.round_problems(self.brief, self.opts, self.reqs), [])
        self.assertTrue(all(r["ok"] for o in self.opts for r in o["fit_results"]))
        r4 = {oid: next(r for r in rs if r["id"] == "R4")["ok"] for oid, rs in self.reqs.items()}
        self.assertEqual(r4, {"A": True, "B": True, "C": False})   # a missed should is shown, not a problem

    def test_option_count_is_the_owners(self):
        one = dict(self.brief, options=1)
        self.assertEqual(design_cli.round_problems(one, self.opts[:1], self.reqs), [])     # one design: no rivals needed
        probs = design_cli.round_problems(self.brief, self.opts[:2], self.reqs)            # the example asked for 3
        self.assertEqual(probs, ["the owner asked for 3 options and this round has 2"])
        hybrid = dict(self.opts[0], merged_from=["1:A", "1:B"])
        self.assertEqual(design_cli.round_problems(self.brief, [hybrid], self.reqs), [])   # a merge round holds the hybrid
        self.assertEqual(design_cli.options_asked({}), 1)

    def test_round_rules(self):
        a, b, c = self.opts
        fewer = dict(b, scorecard=dict(b["scorecard"], parts_total=1))
        same = dict(c, architecture=a["architecture"])
        probs = design_cli.round_problems(self.brief, [a, fewer, same], self.reqs)
        self.assertTrue(any("fewer parts" in p for p in probs) and any("same architecture" in p for p in probs))
        tight = json.loads(json.dumps(self.brief))
        next(r for r in tight["requirements"] if r["id"] == "R7")["check"]["rhs"] = 8
        probs = design_cli.round_problems(tight, self.opts, {o["id"]: D.requirement_results(tight, o) for o in self.opts})
        self.assertEqual(sorted(p[0] for p in probs if "R7" in p), ["A", "B", "C"])

    def test_sketches_and_board(self):
        scale = min(sketch.fit_scale(o) for o in self.opts)
        svgs = {o["id"]: sketch.render(o, scale, uid=f"t{o['id']}") for o in self.opts}
        for svg in svgs.values():
            root = ET.fromstring(svg)
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIn(f"scale {scale:.2f} px/mm", svg)
        for o in self.opts:
            o["massing"] = None
        page = design_board.build(EXAMPLE, self.brief, 1, self.opts, svgs, self.reqs, [], {})
        self.assertIn("simplest baseline", page)
        self.assertEqual(page.count('<section class="opt"'), 3)


class Shortlist(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="design_pick_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for oid in "AB":
            (self.tmp / "draft" / "round_1" / oid).mkdir(parents=True)
            (self.tmp / "draft" / "round_1" / oid / "option.json").write_text("{}")

    def log(self, *entries):
        (self.tmp / "draft" / "log.json").write_text(json.dumps([{"time": "", "notes": "", **e} for e in entries]))

    def test_several_options_need_a_pick(self):
        self.assertIsNone(design_cli.shortlisted(self.tmp))
        self.log({"round": 1, "move": "pick", "options": ["B"]})
        self.assertEqual(design_cli.shortlisted(self.tmp), (1, "B"))

    def test_single_design_needs_none(self):
        shutil.rmtree(self.tmp / "draft" / "round_1" / "B")
        self.assertEqual(design_cli.shortlisted(self.tmp), (1, "A"))
        self.log({"round": 1, "move": "pushback", "options": []})
        self.assertIsNone(design_cli.shortlisted(self.tmp))                 # pushed back: nothing to mass
        (self.tmp / "draft" / "round_2" / "A").mkdir(parents=True)
        (self.tmp / "draft" / "round_2" / "A" / "option.json").write_text("{}")
        self.assertEqual(design_cli.shortlisted(self.tmp), (2, "A"))        # the redrawn design


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="design_gate_"))
        self.product = self.tmp / "products" / EXAMPLE.name
        shutil.copytree(EXAMPLE, self.product, ignore=shutil.ignore_patterns("renders", ".staging", "*.step", "*.stl", "*.FCStd"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def edit(self, rel, fn):
        p = self.product / rel
        data = json.loads(p.read_text(encoding="utf-8"))
        fn(data)
        p.write_text(json.dumps(data), encoding="utf-8")

    def test_approved(self):
        self.assertTrue(D.gate(self.product)[0])
        self.assertTrue(D.gate(self.product, "sleeve")[0])

    def test_unknown_part(self):
        ok, msg = D.gate(self.product, "lid")
        self.assertFalse(ok)
        self.assertIn("not in the approved draft", msg)

    def test_no_approval(self):
        (self.product / "draft" / "approval.json").unlink()
        self.assertFalse(D.gate(self.product)[0])

    def test_changed_draft_closes_only_changed_parts(self):
        self.edit("draft/approved/params.json", lambda d: d.update(wall=2.0))
        self.assertFalse(D.gate(self.product, "sleeve")[0])
        self.assertFalse(D.gate(self.product)[0])
        self.assertFalse(D.gate(self.product, "board")[0])   # the board sits on the wall, so it moved too
        self.edit("draft/approved/params.json", lambda d: d.update(wall=1.6, win_l=54))
        self.assertFalse(D.gate(self.product, "sleeve")[0])
        self.assertTrue(D.gate(self.product, "board")[0])    # the port slot is the sleeve's alone

    def test_changed_brief(self):
        self.edit("brief.json", lambda d: d["notes"].append({"round": 1, "text": "a note does not reopen the gate"}))
        self.assertTrue(D.gate(self.product, "sleeve")[0])
        self.edit("brief.json", lambda d: d["requirements"][0].update(text="Holds a Pi 5"))
        self.assertFalse(D.gate(self.product, "sleeve")[0])

    def test_part_parameter_drift(self):
        self.edit("parts/sleeve/parameters/params.json", lambda d: d.update(wall=1.2, fillet=0.5))
        ok, msg = D.gate(self.product, "sleeve")
        self.assertFalse(ok)
        self.assertIn("wall = 1.2", msg)


if __name__ == "__main__":
    unittest.main()
