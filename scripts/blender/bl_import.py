"""Import a product into Blender from its manifest, validate it, save <asm>_cad.blend.

    blender -b --python scripts/blender/bl_import.py -- --render-dir <folder>/render
        [--tol-linear 0.01] [--tol-angular 0.1] [--no-crosscheck]

Strategy (see docs/rendering.md): every unique part is imported once from its own STEP
with the STEP Importer extension, its bodies are joined into one mesh in part
coordinates, and every component instance becomes an object that shares that mesh and
takes its transform from the manifest. Repeated components therefore share geometry
but keep their own transform, name and material. The objects carry the SolidWorks ids
as custom properties (sw_id, sw_part, sw_parent), so nothing depends on Blender names.

Validation: per-part bbox, per-component world bbox, overall bbox, component count,
hierarchy, missing parts. A cross-check imports the whole assembly STEP once and
compares its bbox. The report goes to render/reports/import_report.json; the exit code
is 1 when a check fails.
"""
import pathlib
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bl_util as U  # noqa: E402


def addon_prefs():
    addon = bpy.context.preferences.addons.get(U.STEP_ADDON)
    if addon is None:
        try:
            bpy.ops.preferences.addon_enable(module=U.STEP_ADDON)
            addon = bpy.context.preferences.addons.get(U.STEP_ADDON)
        except Exception:  # noqa: BLE001
            addon = None
    if addon is None or not hasattr(bpy.ops.import_scene, "step"):
        raise SystemExit("STEP Importer extension is not installed/enabled. See docs/rendering.md (Installation).")
    return addon.preferences


def import_step(path, up_axis="Y"):
    """Import one STEP; returns the new objects. up_axis='Y': cascadio writes glTF Y-up,
    the importer turns it back into the CAD Z-up frame (verified, see findings)."""
    before = set(bpy.data.objects)
    res = bpy.ops.import_scene.step(filepath=str(path), up_axis=up_axis, scale=1.0, merge_objects=False,
                                    use_assembly_collections=False, placement="ORIGIN", origin_offset="KEEP")
    if "FINISHED" not in res:
        raise RuntimeError(f"importer returned {res}")
    return [o for o in bpy.data.objects if o not in before]


def join_part(objs, name):
    """Join the imported bodies of one part into a single mesh in part coordinates."""
    meshes = [o for o in objs if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh in STEP")
    step_rgb = None
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if m and m.use_nodes:
                bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf:
                    step_rgb = [round(c, 4) for c in bsdf.inputs["Base Color"].default_value[:3]]
    for o in meshes:  # bake world transform (glTF nodes + axis correction) into the vertices
        o.data = o.data.copy() if o.data.users > 1 else o.data
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
    base = meshes[0]
    if len(meshes) > 1:
        with bpy.context.temp_override(active_object=base, selected_editable_objects=meshes, object=base):
            bpy.ops.object.join()
    for o in objs:
        if o.name in bpy.data.objects and o is not base:
            bpy.data.objects.remove(o)
    mesh = base.data
    mesh.name = f"MESH_{name}"
    # one generic slot: real materials are assigned per object later
    mesh.materials.clear()
    mesh.materials.append(None)
    bpy.data.objects.remove(base)
    return mesh, step_rgb, len(meshes)


def close(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def main():
    args = U.script_args()
    rdir = pathlib.Path(args["render-dir"]).resolve()
    man = U.load_json(rdir / "export" / "product_manifest.json")
    prefs = addon_prefs()
    prefs.tol_linear = float(args.get("tol-linear", 0.01))   # absolute, mm (verified on the crank arm)
    prefs.tol_angular = float(args.get("tol-angular", 0.1))  # radians
    prefs.tol_relative = False
    prefs.import_materials = True
    prefs.shade_smooth = True
    prefs.show_progress = False
    U.clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system, scene.unit_settings.scale_length = "METRIC", 1.0
    checks, t0 = [], time.time()

    def check(cid, ok, **kw):
        checks.append({"id": cid, "pass": bool(ok), **kw})

    # 1. one mesh per unique part
    meshes, parts_report = {}, {}
    for pid, p in man["parts"].items():
        src = rdir / p["step"]
        t = time.time()
        try:
            objs = import_step(src)
            mesh, step_rgb, nbodies = join_part(objs, pid)
        except Exception as e:  # noqa: BLE001 - reported, not hidden
            check(f"import.{pid}", False, error=str(e), step=str(src))
            continue
        meshes[pid] = mesh
        lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)]) / U.MM
        hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)]) / U.MM
        tol = max(0.2, 0.005 * max(Vector(p["bbox_mm"]["max"]) - Vector(p["bbox_mm"]["min"])))
        ok = close(lo, p["bbox_mm"]["min"], tol) and close(hi, p["bbox_mm"]["max"], tol)
        parts_report[pid] = {"bodies": nbodies, "triangles": sum(len(f.vertices) - 2 for f in mesh.polygons),
                             "seconds": round(time.time() - t, 2), "step_rgb": step_rgb,
                             "bbox_mm": [[round(v, 3) for v in lo], [round(v, 3) for v in hi]]}
        mesh["sw_part"] = pid
        mesh["step_rgb"] = step_rgb or []
        check(f"part_bbox.{pid}", ok, measured=parts_report[pid]["bbox_mm"],
              expected=[p["bbox_mm"]["min"], p["bbox_mm"]["max"]], tol_mm=round(tol, 3))

    # 2. hierarchy as collections, one object per component instance
    root = U.collection(f"CAD_{man['assembly']}")
    root["sw_role"] = "cad_root"
    cols = {man["hierarchy"][0]["id"]: root}
    for node in man["hierarchy"][1:]:
        cols[node["id"]] = U.collection(f"ASM_{node['id']}", cols.get(node["parent"], root))
    placed = []
    for c in man["components"]:
        if not c.get("part") or c["part"] not in meshes:
            continue
        name = c.get("label") or c["id"]
        ob = bpy.data.objects.new(name, meshes[c["part"]])
        cols.get(c["parent"], root).objects.link(ob)
        ob.matrix_world = U.matrix_from_manifest(c["transform"])
        ob.material_slots[0].link = "OBJECT"  # per-instance materials on shared meshes
        ob["sw_id"], ob["sw_part"], ob["sw_parent"] = c["id"], c["part"], c["parent"]
        ob["sw_label"] = c.get("label", "")
        hidden = c["suppressed"] or not c["visible"]
        ob.hide_render = ob.hide_viewport = hidden
        placed.append((c, ob))
    bpy.context.view_layer.update()

    # 3. validation of the placed assembly
    expected = [c for c in man["components"] if c.get("part")]
    check("components", len(placed) == len(expected), expected=len(expected), placed=len(placed),
          missing=[c["id"] for c in expected if c["id"] not in {p[0]["id"] for p in placed}])
    bad = []
    for c, ob in placed:
        lo, hi = U.exact_world_bbox(ob)
        lo, hi = lo / U.MM, hi / U.MM
        e_lo, e_hi = c["world_bbox_mm"]
        size = max(Vector(e_hi) - Vector(e_lo))
        if not (close(lo, e_lo, max(0.3, 0.01 * size)) and close(hi, e_hi, max(0.3, 0.01 * size))):
            bad.append({"id": c["id"], "measured": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
                        "expected": [e_lo, e_hi]})
    check("component_positions", not bad, wrong=bad, checked=len(placed))
    vis = [ob for c, ob in placed if not ob.hide_render]
    lo = Vector([min(U.exact_world_bbox(o)[0][i] for o in vis) for i in range(3)]) / U.MM
    hi = Vector([max(U.exact_world_bbox(o)[1][i] for o in vis) for i in range(3)]) / U.MM
    size = [round(h - l, 3) for l, h in zip(lo, hi)]
    check("assembly_bbox", close(size, man["bbox_mm"]["size"], 0.3), measured=size,
          expected=man["bbox_mm"]["size"], note="also proves scale (mm -> m) and Z-up orientation")
    check("hierarchy", all(n["id"] in cols for n in man["hierarchy"]), nodes=len(man["hierarchy"]))

    # 4. cross-check against the whole-assembly STEP (independent of the manifest transforms)
    if not args.get("no-crosscheck") and man["step"].get("assembly"):
        tmp = bpy.data.scenes.new("_crosscheck")
        win_scene = bpy.context.window.scene if bpy.context.window else None
        try:
            with bpy.context.temp_override(scene=tmp):
                objs = import_step(rdir / man["step"]["assembly"])
            ms = [o for o in objs if o.type == "MESH"]
            clo, chi = U.world_bbox(ms)
            csize = [round((h - l) / U.MM, 3) for l, h in zip(clo, chi)]
            check("crosscheck.assembly_step_bbox", close(csize, man["bbox_mm"]["size"], 0.5), measured=csize,
                  expected=man["bbox_mm"]["size"])
            check("crosscheck.assembly_step_mesh_count", len(ms) >= len(vis), meshes=len(ms), components=len(vis),
                  note="bodies, so >= components for multi-body parts")
            for o in objs:
                bpy.data.objects.remove(o)
        except Exception as e:  # noqa: BLE001
            check("crosscheck.assembly_step", False, error=str(e))
        finally:
            if win_scene:
                bpy.context.window.scene = win_scene
            bpy.data.scenes.remove(tmp)
        for m in [m for m in bpy.data.meshes if m.users == 0]:
            bpy.data.meshes.remove(m)
        for m in [m for m in bpy.data.materials if m.users == 0]:
            bpy.data.materials.remove(m)

    ok = all(c["pass"] for c in checks)
    out_blend = rdir / "blender" / f"{man['assembly']}_cad.blend"
    out_blend.parent.mkdir(parents=True, exist_ok=True)
    scene["sw_manifest"] = str(rdir / "export" / "product_manifest.json")
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), compress=True)
    report = {"pass": ok, "seconds": round(time.time() - t0, 1), "blend": str(out_blend),
              "tessellation": {"tol_linear_mm": prefs.tol_linear, "tol_angular_rad": prefs.tol_angular},
              "importer": "STEP Importer extension (bl_ext.user_default.step_importer)",
              "triangles_total": sum(r["triangles"] for r in parts_report.values()),
              "parts": parts_report, "checks": checks}
    U.save_json(rdir / "reports" / "import_report.json", report)
    for c in checks:
        if not c["pass"] or not c["id"].startswith("part_bbox"):
            U.log("PASS" if c["pass"] else "FAIL", c["id"], {k: v for k, v in c.items() if k not in ("id", "pass", "wrong")}
                  if c["pass"] else {k: v for k, v in c.items() if k not in ("id", "pass")})
    U.log(f"{'PASS' if ok else 'FAIL'} import: {len(placed)} components, {len(meshes)} parts, "
          f"{report['triangles_total']} triangles, {report['seconds']} s -> {out_blend}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
