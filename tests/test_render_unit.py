"""Fast checks of the rendering pipeline's pure-Python parts (no SolidWorks, no Blender).

    .venv\\Scripts\\python -m unittest tests.test_render_unit -v
"""
import json
import pathlib
import shutil
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_config as rc  # noqa: E402
import render_export as rx  # noqa: E402


class ExportMath(unittest.TestCase):
    def test_transform_rot_z(self):
        # assembly.py's rot_z -90 maps local (x, y) to (y, -x) (verified in SolidWorks)
        c, s = 0.0, -1.0
        arr = [c, s, 0, -s, c, 0, 0, 0, 1, 0.010, 0.020, 0.030, 1.0]
        m = rx.matrix_from_sw(arr)
        p = rx.apply(m, (1.0, 2.0, 0.0))
        self.assertAlmostEqual(p[0], 2.0 + 10.0)
        self.assertAlmostEqual(p[1], -1.0 + 20.0)
        self.assertAlmostEqual(p[2], 30.0)

    def test_world_bbox(self):
        m = rx.matrix_from_sw([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0.1, 1])
        lo, hi = rx.world_bbox(m, [-1, -2, 0], [1, 2, 5])
        self.assertEqual(lo, [-1, -2, 100])
        self.assertEqual(hi, [1, 2, 105])

    def test_explode_auto_keeps_largest_and_ranks_levels(self):
        comps = [
            {"id": "tube-1", "part": "tube", "visible": True, "suppressed": False, "world_bbox_mm": [[-30, -30, 0], [30, 30, 120]]},
            {"id": "lid-1", "part": "lid", "visible": True, "suppressed": False, "world_bbox_mm": [[-30, -30, 120], [30, 30, 130]]},
            {"id": "screw-1", "part": "screw", "visible": True, "suppressed": False, "world_bbox_mm": [[-8, -2, 130], [-4, 2, 140]]},
            {"id": "screw-2", "part": "screw", "visible": True, "suppressed": False, "world_bbox_mm": [[4, -2, 130], [8, 2, 140]]},
            {"id": "foot-1", "part": "foot", "visible": True, "suppressed": False, "world_bbox_mm": [[-10, -10, -5], [10, 10, 0]]},
        ]
        ex = rx.explode_auto(comps, {}, "z", gap=10)
        o = ex["offsets_mm"]
        self.assertEqual(ex["anchor"], "tube-1")
        self.assertEqual(o["tube-1"], [0, 0, 0])
        self.assertEqual(o["foot-1"][2], -10)          # below the anchor moves down
        self.assertEqual(o["lid-1"][2], 10)             # one level above the anchor
        self.assertEqual(o["screw-1"][2], 20)           # two levels above
        self.assertEqual(o["screw-1"], o["screw-2"])    # same level -> same offset

    def test_explode_from_assembly_matches_labels_then_order(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "assembly.json").write_text(json.dumps({"components": [
            {"part": "screw", "at": [0, 0, 50], "label": "s_top"},
            {"part": "screw", "at": [0, 0, -50]},
        ]}))
        comps = [{"id": "screw-1", "part": "screw", "label": "s_top", "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 10], [0, 0, 0, 1]]},
                 {"id": "screw-2", "part": "screw", "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 10], [0, 0, 0, 1]]}]
        ex = rx.explode_from_assembly(comps, tmp)
        self.assertEqual(ex["offsets_mm"]["screw-1"], [0, 0, 40])
        self.assertEqual(ex["offsets_mm"]["screw-2"], [0, 0, -60])
        shutil.rmtree(tmp)

    def test_material_proposals(self):
        lib = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))
        self.assertEqual(rx.propose_material("grindmn_screw_m3x8", "", lib)["material"], "stainless_steel")
        self.assertEqual(rx.propose_material("grindmn_oring_60x2", "", lib)["material"], "rubber")
        self.assertEqual(rx.propose_material("anything", "6061-T6 (SS)", lib)["source"], "solidworks_material")
        self.assertEqual(rx.propose_material("zzz", "", lib)["source"], "default")


class Libraries(unittest.TestCase):
    def test_required_materials_exist(self):
        mats = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))["materials"]
        need = ["aluminium_raw", "aluminium_brushed", "aluminium_anodized", "aluminium_anodized_black", "stainless_steel",
                "stainless_polished", "steel_galvanized", "copper", "brass", "abs", "pla", "petg", "polycarbonate",
                "acrylic", "acrylic_frosted", "nylon", "rubber", "powder_matte", "powder_satin", "powder_gloss",
                "glass_clear", "glass_frosted", "polycarbonate_clear", "plastic_translucent"]
        self.assertFalse([m for m in need if m not in mats])
        for mid, m in mats.items():
            for k in ("base_color", "metallic", "roughness", "ior"):
                self.assertIn(k, m, f"{mid} lacks {k}")
            self.assertTrue(0 <= m["roughness"] <= 1 and 0 <= m["metallic"] <= 1, mid)

    def test_finishes_and_presets(self):
        lib = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))
        for f in ("bead_blasted", "brushed", "polished", "textured", "matte", "satin", "gloss"):
            self.assertIn(f, lib["finishes"])
        light = json.loads((rc.LIB / "lighting.json").read_text(encoding="utf-8"))["presets"]
        self.assertTrue({"soft_commercial", "dramatic_premium", "neutral_technical"} <= set(light))
        cams = json.loads((rc.LIB / "cameras.json").read_text(encoding="utf-8"))["presets"]
        self.assertTrue({"three_quarter_hero", "front_ortho", "side_ortho", "top_ortho", "detail_closeup",
                         "low_angle_hero"} <= set(cams))


class ApprovalGate(unittest.TestCase):
    """approve/final refuse unless the approved hash equals the current scene + libraries."""

    def setUp(self):
        import render_cli
        self.cli = render_cli
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        man = {"assembly": "t", "parts": {"p": {"material": {"confidence": "low"}}},
               "components": [{"id": "p-1", "part": "p"}], "bbox_mm": {"size": [10, 10, 10]}}
        rc.path(self.tmp, "manifest").parent.mkdir(parents=True)
        rc.path(self.tmp, "manifest").write_text(json.dumps(man))
        self.cli.cmd_init(types.SimpleNamespace(target=str(self.tmp), force=False))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def ns(self, **kw):
        return types.SimpleNamespace(target=str(self.tmp), force=False, shots=None, quote=None, **kw)

    def test_final_refuses_without_approval(self):
        with self.assertRaises(SystemExit) as e:
            self.cli.cmd_final(self.ns())
        self.assertIn("NOT APPROVED", str(e.exception))

    def test_approve_needs_matching_preview_and_edit_invalidates(self):
        h = self.cli.settings_hash(self.tmp)
        rp = rc.path(self.tmp, "reports") / "preview_latest.json"
        rp.parent.mkdir(parents=True)
        rp.write_text(json.dumps({"settings_hash": "stale", "shots": []}))
        with self.assertRaises(SystemExit):
            self.cli.cmd_approve(types.SimpleNamespace(target=str(self.tmp), quote="approved"))
        rp.write_text(json.dumps({"settings_hash": h, "shots": [], "partial": False}))
        with self.assertRaises(SystemExit):  # no quote -> refused
            self.cli.cmd_approve(types.SimpleNamespace(target=str(self.tmp), quote=""))
        self.cli.cmd_approve(types.SimpleNamespace(target=str(self.tmp), quote="approved, render the finals"))
        self.assertEqual(json.loads((rc.path(self.tmp, "settings") / "approval.json").read_text())["settings_hash"], h)
        # a user-visible edit after approval invalidates it
        sp = self.cli.settings_path(self.tmp)
        s = json.loads(sp.read_text())
        s["lighting"]["exposure"] = 0.5
        sp.write_text(json.dumps(s))
        with self.assertRaises(SystemExit) as e:
            self.cli.cmd_final(self.ns())
        self.assertIn("changed after approval", str(e.exception))

    def test_notes_do_not_change_hash(self):
        h = self.cli.settings_hash(self.tmp)
        sp = self.cli.settings_path(self.tmp)
        s = json.loads(sp.read_text())
        s["_comment"] = "edited note"
        sp.write_text(json.dumps(s))
        self.assertEqual(h, self.cli.settings_hash(self.tmp))

    def test_init_keeps_existing_settings(self):
        sp = self.cli.settings_path(self.tmp)
        s = json.loads(sp.read_text())
        s["lighting"]["preset"] = "dramatic_premium"
        sp.write_text(json.dumps(s))
        self.cli.cmd_init(types.SimpleNamespace(target=str(self.tmp), force=False))
        self.assertEqual(json.loads(sp.read_text())["lighting"]["preset"], "dramatic_premium")


if __name__ == "__main__":
    unittest.main()
