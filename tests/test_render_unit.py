"""Fast checks of the rendering pipeline's pure-Python parts (no CAD system, no Blender).

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

import render_adapters  # noqa: E402
import render_config as rc  # noqa: E402
from render_adapters import common as C  # noqa: E402
from render_adapters import freecad as fc  # noqa: E402
from render_adapters import mesh_file as mf  # noqa: E402
from render_adapters import solidworks as sw  # noqa: E402


class ExportMath(unittest.TestCase):
    def test_transform_rot_z(self):
        # assembly.py's rot_z -90 maps local (x, y) to (y, -x) (verified in SolidWorks)
        c, s = 0.0, -1.0
        arr = [c, s, 0, -s, c, 0, 0, 0, 1, 0.010, 0.020, 0.030, 1.0]
        m = sw.matrix_from_sw(arr)
        p = C.apply(m, (1.0, 2.0, 0.0))
        self.assertAlmostEqual(p[0], 2.0 + 10.0)
        self.assertAlmostEqual(p[1], -1.0 + 20.0)
        self.assertAlmostEqual(p[2], 30.0)

    def test_world_bbox(self):
        m = sw.matrix_from_sw([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0.1, 1])
        lo, hi = C.world_bbox(m, [-1, -2, 0], [1, 2, 5])
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
        ex = C.explode_auto(comps, "z", gap=10)
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
        ex = C.explode_from_assembly(comps, tmp)
        self.assertEqual(ex["offsets_mm"]["screw-1"], [0, 0, 40])
        self.assertEqual(ex["offsets_mm"]["screw-2"], [0, 0, -60])
        shutil.rmtree(tmp)

    def test_material_proposals(self):
        lib = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))
        self.assertEqual(C.propose_material("grindmn_screw_m3x8", "", lib)["material"], "stainless_steel")
        self.assertEqual(C.propose_material("grindmn_oring_60x2", "", lib)["material"], "rubber")
        self.assertEqual(C.propose_material("anything", "6061-T6 (SS)", lib)["source"], "cad_material")
        self.assertEqual(C.propose_material("zzz", "", lib)["source"], "default")
        self.assertEqual(C.propose_material("zzz", "mat_0", lib)["source"], "default")  # exporter placeholder
        self.assertEqual(C.propose_material("zzz", "ABS black", lib)["material"], "abs")


def lib():
    return json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))


def tiny_manifest(adapter="file"):
    m = C.new_manifest(project="t", assembly="prod", adapter=adapter, application="x")
    m["parts"]["bolt"] = C.part_entry("bolt", {"file": "export/geometry/parts/bolt.glb", "format": "gltf"},
                                      [-2, -2, 0], [2, 2, 10], source_material="Steel", source_color=[1, 0, 0], lib=lib())
    rz = [[0, -1, 0, 5], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]  # 90 deg about Z, then +5 mm in x
    m["components"].append(C.component_entry("prod/bolt.001", "bolt", rz, "prod", m["parts"]))
    m["components"].append(C.component_entry("prod/bolt.002", "bolt", C.IDENTITY, "prod", m["parts"]))
    return C.finish(m)


class Manifest(unittest.TestCase):
    """The source-neutral contract between adapters and Blender."""

    def test_build_and_validate(self):
        m = tiny_manifest()
        self.assertEqual(m["schema_version"], "2.0")
        self.assertEqual(m["parts"]["bolt"]["source_color"], "#FF0000")
        self.assertEqual(m["components"][0]["world_bbox_mm"], [[3.0, -2.0, 0.0], [7.0, 2.0, 10.0]])
        self.assertEqual(m["bbox_mm"]["size"], [9.0, 4.0, 10.0])
        self.assertEqual(C.validate(m), [])

    def test_validate_catches_problems(self):
        m = tiny_manifest()
        m["components"][1]["part"] = "nope"
        m["components"].append(dict(m["components"][0]))
        m["parts"]["bolt"]["geometry"]["format"] = "dwg"
        m["units"]["length"] = "in"
        p = " ".join(C.validate(m))
        for word in ("unknown part", "not unique", "known format", "units"):
            self.assertIn(word, p)

    def test_upgrade_schema_1(self):
        old = {"schema_version": "1.0", "assembly": "a", "source_cad": "C:/x/a.SLDASM",
               "step": {"assembly": "export/step/a.step", "schema": "AUTOMOTIVE_DESIGN"},
               "parts": {"p": {"part_id": "p", "step": "export/step/parts/p.step", "sw_material": "6061",
                               "sw_appearance": {"rgb": [0, 0, 1]},
                               "material": {"material": "x", "source": "solidworks_material"}}},
               "components": [{"id": "p-1", "part": "p", "sw_path": "C:/x/p.SLDPRT"}]}
        m = C.upgrade(old)
        self.assertEqual(m["source"]["adapter"], "solidworks")
        self.assertEqual(m["parts"]["p"]["geometry"]["file"], "export/step/parts/p.step")
        self.assertEqual(m["parts"]["p"]["source_color"], "#0000FF")
        self.assertEqual(m["parts"]["p"]["material"]["source"], "cad_material")
        self.assertEqual(m["geometry"]["assembly"]["format"], "step")
        self.assertIn("step", old)  # the input is not modified

    def test_template_material_and_colour_dropped(self):
        parts = {k: C.part_entry(k, {"file": "f.step", "format": "step"}, [0, 0, 0], [1, 1, 1], source_material="Steel",
                                 source_color="#CAD1EE", lib=lib()) for k in ("grindmn_screw", "grindmn_oring")}
        C.drop_template_material(parts, lib())
        self.assertEqual(parts["grindmn_oring"]["material"]["material"], "rubber")
        self.assertIsNone(parts["grindmn_screw"]["source_color"])

    def test_detect_adapter(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        for name, want in (("a.SLDASM", "solidworks"), ("b.FCStd", "freecad"), ("c.step", "file"), ("d.glb", "file"),
                           ("e.stl", "file")):
            (tmp / name).write_bytes(b"x")
            self.assertEqual(render_adapters.detect(tmp / name), want)
        (tmp / "f.dwg").write_bytes(b"x")
        with self.assertRaises(SystemExit):
            render_adapters.detect(tmp / "f.dwg")
        shutil.rmtree(tmp)

    def test_size_check(self):
        self.assertTrue(mf.check_size([340, 600, 6.35], [340, 600, 6.35])[0])
        self.assertTrue(mf.check_size([340, 600, 6.35], [340, 0, 0])[0])  # unknown axes skipped
        self.assertFalse(mf.check_size([340000, 600000, 6350], [340, 600, 6.35])[0])


class FreeCADAdapter(unittest.TestCase):
    """Host side of the FreeCAD adapter (the part that runs inside FreeCAD needs FreeCAD)."""

    def test_gui_colors_from_fcstd(self):
        import zipfile
        tmp = pathlib.Path(tempfile.mkdtemp())
        f = tmp / "t.FCStd"
        xml = ('<Document><ViewProviderData><ViewProvider name="Body"><Properties>'
               '<Property name="ShapeColor" type="App::PropertyColor"><PropertyColor value="4278190335"/></Property>'
               '</Properties></ViewProvider></ViewProviderData></Document>')  # 0xFF0000FF = red, opaque
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("GuiDocument.xml", xml)
        self.assertEqual(fc.gui_colors(f), {"Body": [1.0, 0.0, 0.0]})
        shutil.rmtree(tmp)

    def test_manifest_from_dump(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        rdir = tmp / "render"
        (rdir / "export" / "geometry" / "parts").mkdir(parents=True)
        (tmp / "box.FCStd").write_bytes(b"")
        part_file = str(rdir / "export" / "geometry" / "parts" / "Plate.step")
        raw = {"root": "box", "freecad_version": "1.0.0", "warnings": [],
               "hierarchy": [{"id": "box", "parent": None, "kind": "assembly"},
                             {"id": "Part", "parent": "box", "kind": "subassembly", "label": "Part"}],
               "parts": {"Plate": {"file": part_file, "bbox_min": [0, 0, 0], "bbox_max": [100, 50, 5],
                                   "label": "Plate", "object": "box#Body", "material_name": "", "solids": 1}},
               "components": [{"id": "Part/Link", "name": "Plate", "label": "Plate", "parent": "Part", "part": "Plate",
                               "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 20], [0, 0, 0, 1]], "visible": True,
                               "world_bbox_mm": [[0, 0, 20], [100, 50, 25]]}],
               "freecad_bbox": [[0, 0, 20], [100, 50, 25]]}
        orig = fc.run_dump
        fc.run_dump = lambda f, r: (raw, pathlib.Path("FreeCADCmd.exe"))
        try:
            m = C.finish(fc.export(tmp / "box.FCStd", rdir, lib()))
        finally:
            fc.run_dump = orig
        self.assertEqual(m["source"]["adapter"], "freecad")
        self.assertEqual(m["parts"]["Plate"]["geometry"], {"file": "export/geometry/parts/Plate.step", "format": "step",
                                                           "scale_to_m": None, "up_axis": "Z"})
        self.assertEqual(m["bbox_mm"]["size"], [100.0, 50.0, 5.0])
        self.assertTrue(m["validation"]["freecad_bbox_check"]["pass"])
        shutil.rmtree(tmp)


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
        rc.path(self.tmp, "manifest").parent.mkdir(parents=True)
        C.save(tiny_manifest(), rc.path(self.tmp, "manifest"))
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
