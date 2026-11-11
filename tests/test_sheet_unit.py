"""Fast checks of the hand-folded sheet pipeline's pure-Python parts (no FreeCAD, no Blender).

    python3 -m unittest tests.test_sheet_unit -v
"""
import argparse
import copy
import json
import math
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import draft_lib as D  # noqa: E402
import dxf_io  # noqa: E402
import fold_patterns as FP  # noqa: E402
import sheet_cli  # noqa: E402
import sheet_draw  # noqa: E402
import sheet_lib as S  # noqa: E402

REC = {**FP.DEFAULTS["slots"], "method": "slots", "slot_length": 8.0, "slot_width": 0.5, "bridge": 1.5, "end_clearance": 2.0}


def tray(**kw):
    args = dict(length=120, width=80, height=30, flange=10)
    args.update(kw)
    return S.tray(**args)


class Patterns(unittest.TestCase):
    def test_slots_are_centred_and_keep_the_ends(self):
        cuts = FP.slots(40, REC)
        self.assertEqual(len(cuts), 3)                                   # 3 x 8 + 2 x 1.5 = 27 fits in 36, a fourth does not
        self.assertAlmostEqual(cuts[0][0] - 4, 40 - (cuts[-1][0] + 4))   # the same uncut length at both ends
        self.assertAlmostEqual(cuts[1][0] - cuts[0][0], 9.5)
        self.assertEqual(FP.slots(9, REC), [])                           # 9 - 2 x 2 leaves no room for one slot
        s = FP.summary(40, REC)
        self.assertEqual((s["slots"], s["cut_length"], s["bridge_total"], s["end_uncut"]), (3, 24.0, 16.0, 6.5))


class Dxf(unittest.TestCase):
    def test_round_trip(self):
        layers = {"CUT_THROUGH": [{"kind": "poly", "closed": True, "pts": [[0, 0], [10, 0], [10, 5], [0, 5]], "bulges": [0, 0.5, 0, 0]},
                                  {"kind": "circle", "c": [5, 2.5], "r": 1}],
                  "FOLD_PERFORATION": [{"kind": "stadium", "a": [1, 1], "b": [4, 1], "w": 0.5}, {"kind": "line", "a": [0, 0], "b": [3, 4]}]}
        path = pathlib.Path(tempfile.mkdtemp(prefix="dxf_")) / "t.dxf"
        self.addCleanup(shutil.rmtree, path.parent, ignore_errors=True)
        dxf_io.write(path, layers)
        back = dxf_io.read(path)
        self.assertEqual(dxf_io.counts(back), {"CUT_THROUGH": 2, "FOLD_PERFORATION": 2})
        self.assertEqual(back["CUT_THROUGH"][0]["bulges"], [0, 0.5, 0, 0])
        self.assertEqual(back["FOLD_PERFORATION"][0]["bulges"], [0, 1, 0, 1])       # the slot's two round ends
        self.assertEqual(dxf_io.extent({"c": back["CUT_THROUGH"]}), (0, 0, 10, 5))
        with self.assertRaises(ValueError):
            dxf_io.write(path, {"LASER": []})

    def test_bulge_and_text(self):
        self.assertAlmostEqual(dxf_io.bulge([1, 0], [-1, 0], [0, 1]), 1.0)          # upper half circle, counter-clockwise
        self.assertAlmostEqual(dxf_io.bulge([-1, 0], [1, 0], [0, 1]), -1.0)
        self.assertAlmostEqual(dxf_io.bulge([1, 0], [0, 1], [math.sqrt(0.5), math.sqrt(0.5)]), math.tan(math.pi / 8))
        self.assertEqual(len(dxf_io.text("18", 0, 0, 5)), 2 + 7)
        with self.assertRaises(ValueError):
            dxf_io.text("x", 0, 0, 5)


class Sheet(unittest.TestCase):
    def test_tray_folds_to_its_stated_size(self):
        lo, hi = S.folded_bbox(S.resolve(tray()))
        self.assertEqual([round(h - l, 6) for l, h in zip(lo, hi)], [120, 80, 30])
        lo, hi = S.folded_bbox(S.resolve(tray(dims="inside")))                # inside sizes: the sheet adds a thickness each side
        self.assertEqual([round(h - l, 6) for l, h in zip(lo, hi)], [122, 82, 32])
        lo, hi = S.folded_bbox(S.resolve(tray(flange=0)))
        self.assertEqual([round(h - l, 6) for l, h in zip(lo, hi)], [120, 80, 30])

    def test_allowance_and_hinge_keep_the_size(self):
        raw = tray()
        raw["params"]["allow"] = 1.2
        raw["params"]["hinge"] = 0.8
        sheet = S.resolve(raw)
        lo, hi = S.folded_bbox(sheet)
        self.assertEqual([round(h - l, 6) for l, h in zip(lo, hi)], [120, 80, 30])
        self.assertTrue(all(abs(math.dist(f["s"], f["s2"]) - 1.2) < 1e-9 for f in sheet["folds"]))

    def test_recipe_change_leaves_panels_and_folds_alone(self):
        raw = tray()
        a = S.resolve(raw)
        other = copy.deepcopy(raw)
        other["recipes"]["fold"].update(slot_length=4.0, bridge=1.0, slot_width=0)
        b = S.resolve(other)
        self.assertEqual({k: p["flat"] for k, p in a["panels"].items()}, {k: p["flat"] for k, p in b["panels"].items()})
        self.assertEqual([(f["m0"], f["m1"], f["signed"]) for f in a["folds"]], [(f["m0"], f["m1"], f["signed"]) for f in b["folds"]])
        fa, fb = S.fold_entities(a, a["folds"][0])[0], S.fold_entities(b, b["folds"][0])[0]
        self.assertEqual((fa[0]["kind"], fb[0]["kind"]), ("stadium", "line"))
        self.assertGreater(len(fb), len(fa))

    def test_tree_rules(self):
        raw = tray()
        raw["folds"] = raw["folds"][:-1]                                        # a flange left unattached
        with self.assertRaises(S.SheetError):
            S.resolve(raw)
        raw = tray()
        raw["panels"][1]["outline"][1][0] = "bl + 5"                            # a wall longer than the base edge it folds from
        raw["panels"][1]["outline"][2][0] = "bl + 5"
        with self.assertRaises(S.SheetError):
            S.resolve(raw)
        raw = tray()
        raw["folds"][0]["recipe"] = "nope"
        with self.assertRaises(S.SheetError):
            S.resolve(raw)

    def test_three_separate_verdicts(self):
        sheet = S.resolve(tray())
        v = S.verdicts(S.checks(sheet))
        self.assertEqual(v, {"geometric": True, "manufacturable": True, "experimental": False})
        self.assertTrue(S.untested(sheet))
        thin = tray()
        thin["recipes"]["fold"]["bridge"] = 0.4                                 # under the profile's minimum bridge
        v = S.verdicts(S.checks(S.resolve(thin)))
        self.assertEqual((v["geometric"], v["manufacturable"]), (True, False))
        sheet["mat"] = dict(sheet["mat"], tested=[{"coupon": "t:05", "result": "held", "angle": 90,
                                                   "recipe": {"method": "slots", "slot_length": 8.2, "slot_width": 0.5, "bridge": 1.5}}])
        self.assertTrue(S.verdicts(S.checks(sheet))["experimental"])
        self.assertFalse(S.untested(sheet))
        sheet["mat"]["tested"][0]["result"] = "cracked"
        self.assertTrue(S.untested(sheet))

    def test_hole_too_near_an_edge(self):
        raw = tray()
        raw["panels"][0]["features"] = [{"type": "circle", "d": 4, "at": [2.5, 20]}]
        bad = [c["id"] for c in S.checks(S.resolve(raw)) if not c["ok"] and c["level"] == "manufacturable"]
        self.assertEqual(bad, ["feature.base.0.web", "fold.f_left.features"])

    def test_sequence_and_draft_bodies(self):
        sheet = S.resolve(tray())
        st = S.states(sheet)
        self.assertEqual([s["sequence"] for s in st], [1] * 4 + [2] * 4)        # flanges first, then the walls
        self.assertEqual(st[-1]["angles"], S.final_angles(sheet))
        self.assertEqual(st[3]["angles"]["f_front"], 0)
        bodies = S.draft_bodies(sheet)
        self.assertEqual(sorted(b["axis"] for b in bodies), ["x"] * 2 + ["y"] * 2 + ["z"] * 5)
        raw = tray()
        raw["folds"][0]["angle"] = 60
        with self.assertRaises(S.SheetError):
            S.draft_bodies(S.resolve(raw))

    def test_flat_svg(self):
        svg = sheet_draw.flat_svg(S.resolve(tray()))
        self.assertIn("UNTESTED FOLDS", svg)
        self.assertEqual(svg.count('class="fold"'), 8)


class Coupons(unittest.TestCase):
    def test_sheet_and_record(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="coupons_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "lib").mkdir()
        shutil.copy(S.LIB / "materials.json", tmp / "lib" / "materials.json")
        real, S.LIB = S.LIB, tmp / "lib"
        self.addCleanup(setattr, S, "LIB", real)
        shutil.copy(real / "manufacturing.json", tmp / "lib" / "manufacturing.json")
        ns = argparse.Namespace(folder=str(tmp / "c"), material="5052-H32_1.0", manufacturing="generic_untested", slot_lengths="4,8",
                                bridges="0.5,1.5", slot_width=0.5, end_clearance=2.0, strip="40x60")
        sheet_cli.cmd_coupons(ns)
        table = json.loads((tmp / "c" / "coupons.json").read_text())["coupons"]
        self.assertEqual([c["id"] for c in table], ["01", "02", "03", "04"])
        self.assertEqual([bool(c["flags"]) for c in table], [True, True, False, False])     # a 0.5 bridge is under the minimum
        back = dxf_io.read(tmp / "c" / "coupons.dxf")
        self.assertEqual(len(back["CUT_THROUGH"]), 4)
        sheet_cli.cmd_record(argparse.Namespace(coupons=str(tmp / "c" / "coupons.json"), id="04", result="held", angle=90.0,
                                                leg_a=30.4, leg_b=30.5, grain="across", notes=None))
        entry = json.loads((tmp / "lib" / "materials.json").read_text())["5052-H32_1.0"]["tested"][0]
        self.assertEqual((entry["recipe"]["slot_length"], entry["result"], entry["hinge_measured"]), (8.0, "held", 0.45))
        sheet = S.resolve(tray())                                              # the tray's recipe is now a tested one
        self.assertFalse(S.untested(sheet))


if __name__ == "__main__":
    unittest.main()
