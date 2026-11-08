"""Import a product into Blender from its manifest, validate it, save <asm>_cad.blend.

    blender -b --python scripts/blender/bl_import.py -- --render-dir <folder>/render
        [--tol-linear 0.01] [--tol-angular 0.1] [--no-crosscheck]

Source-neutral: the manifest (scripts/render_adapters/common.py) names one geometry file per
unique part in any supported format (bl_formats.py), whichever CAD adapter wrote it. Every
unique part is imported once, its bodies are joined into one mesh in part coordinates, and
every component instance becomes an object that shares that mesh and takes its transform
from the manifest. Repeated components therefore share geometry but keep their own
transform, name and material. Objects carry the CAD ids as custom properties (cad_id,
cad_part, cad_parent, cad_label), so nothing depends on Blender names.

Validation: per-part bbox, per-component placement, overall bbox, component count,
hierarchy, missing parts; a cross-check imports the whole-product file when the manifest
has one. How independent the expected values are is in manifest.validation.reference.
The report goes to render/reports/import_report.json; the exit code is 1 when a check fails.
"""
import pathlib
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bl_formats as F  # noqa: E402
import bl_util as U  # noqa: E402


def join_part(objs, name):
    """Join the imported bodies of one part into a single mesh in part coordinates."""
    meshes = [o for o in objs if o.type == "MESH" and len(o.data.vertices)]
    if not meshes:
        raise RuntimeError("no mesh in the geometry file")
    rgb = F.base_color(meshes)
    for o in meshes:  # bake world transform (file nodes + axis correction) into the vertices
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
    mesh.materials.clear()  # one generic slot: real materials are assigned per object later
    mesh.materials.append(None)
    bpy.data.objects.remove(base)
    return mesh, rgb, len(meshes)


def close(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def purge():
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for m in [m for m in blk if m.users == 0]:
            blk.remove(m)


def main():
    args = U.script_args()
    rdir = pathlib.Path(args["render-dir"]).resolve()
    mpath = rdir / "export" / "product_manifest.json"
    man = U.load_manifest(mpath)
    U.clear_scene()
    formats = {p["geometry"]["format"] for p in man["parts"].values()}
    if (man.get("geometry") or {}).get("assembly"):
        formats.add(man["geometry"]["assembly"]["format"])
    prefs = F.step_prefs(args.get("tol-linear", 0.01), args.get("tol-angular", 0.1)) if "step" in formats else None
    scene = bpy.context.scene
    scene.unit_settings.system, scene.unit_settings.scale_length = "METRIC", 1.0
    checks, t0 = [], time.time()

    def check(cid, ok, **kw):
        checks.append({"id": cid, "pass": bool(ok), **kw})

    # 1. one mesh per unique part
    meshes, parts_report = {}, {}
    for pid, p in man["parts"].items():
        g = p["geometry"]
        src = rdir / g["file"]
        t = time.time()
        try:
            objs = F.import_file(src, g["format"], g.get("scale_to_m"), g.get("up_axis", "Z"))
            mesh, rgb, nbodies = join_part(objs, pid)
        except Exception as e:  # noqa: BLE001 - reported, not hidden
            check(f"import.{pid}", False, error=str(e), file=str(src))
            continue
        meshes[pid] = mesh
        lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)]) / U.MM
        hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)]) / U.MM
        tol = max(0.2, 0.005 * max(Vector(p["bbox_mm"]["max"]) - Vector(p["bbox_mm"]["min"])))
        ok = close(lo, p["bbox_mm"]["min"], tol) and close(hi, p["bbox_mm"]["max"], tol)
        parts_report[pid] = {"bodies": nbodies, "triangles": sum(len(f.vertices) - 2 for f in mesh.polygons),
                             "seconds": round(time.time() - t, 2), "file_rgb": rgb, "format": g["format"],
                             "bbox_mm": [[round(v, 3) for v in lo], [round(v, 3) for v in hi]]}
        mesh["cad_part"] = pid
        mesh["file_rgb"] = rgb or []
        check(f"part_bbox.{pid}", ok, measured=parts_report[pid]["bbox_mm"],
              expected=[p["bbox_mm"]["min"], p["bbox_mm"]["max"]], tol_mm=round(tol, 3))

    # 2. hierarchy as collections, one object per component instance
    root = U.collection(f"CAD_{man['assembly']}")
    root["cad_role"] = "cad_root"
    cols = {man["hierarchy"][0]["id"]: root}
    for node in man["hierarchy"][1:]:
        cols[node["id"]] = U.collection(f"ASM_{node['id'].split('/')[-1]}", cols.get(node["parent"], root))
    placed = []
    for c in man["components"]:
        if not c.get("part") or c["part"] not in meshes:
            continue
        ob = bpy.data.objects.new(c.get("label") or c["name"] or c["id"], meshes[c["part"]])
        cols.get(c["parent"], root).objects.link(ob)
        ob.matrix_world = U.matrix_from_manifest(c["transform"])
        ob.material_slots[0].link = "OBJECT"  # per-instance materials on shared meshes
        ob["cad_id"], ob["cad_part"], ob["cad_parent"] = c["id"], c["part"], c["parent"]
        ob["cad_label"] = c.get("label", "")
        hidden = c["suppressed"] or not c["visible"]
        ob.hide_render = ob.hide_viewport = hidden
        placed.append((c, ob))
    bpy.context.view_layer.update()

    # 3. validation of the placed product
    expected = [c for c in man["components"] if c.get("part")]
    check("components", len(placed) == len(expected), expected=len(expected), placed=len(placed),
          missing=[c["id"] for c in expected if c["id"] not in {p[0]["id"] for p in placed}])
    bad = []
    for c, ob in placed:
        lo, hi = U.local_aabb_world(ob)  # same quantity as the manifest's world_bbox_mm: exact for any rotation
        lo, hi = lo / U.MM, hi / U.MM
        e_lo, e_hi = c["world_bbox_mm"]
        tol = max(0.3, 0.01 * max(Vector(e_hi) - Vector(e_lo)))
        if not (close(lo, e_lo, tol) and close(hi, e_hi, tol)):
            bad.append({"id": c["id"], "measured": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
                        "expected": [e_lo, e_hi]})
    check("component_positions", not bad, wrong=bad, checked=len(placed))
    vis = [ob for c, ob in placed if not ob.hide_render]
    boxes = [U.exact_world_bbox(o) for o in vis]
    lo = Vector([min(b[0][i] for b in boxes) for i in range(3)]) / U.MM
    hi = Vector([max(b[1][i] for b in boxes) for i in range(3)]) / U.MM
    size = [round(h - l, 3) for l, h in zip(lo, hi)]
    check("assembly_bbox", close(size, man["bbox_mm"]["size"], max(0.3, 0.002 * max(size))), measured=size,
          expected=man["bbox_mm"]["size"], reference=man["validation"]["reference"],
          note="also proves scale (mm -> m) and Z-up when the reference is the CAD kernel")
    check("hierarchy", all(n["id"] in cols for n in man["hierarchy"]), nodes=len(man["hierarchy"]))

    # 4. cross-check against the whole-product file (independent of the manifest transforms)
    whole = (man.get("geometry") or {}).get("assembly")
    if not args.get("no-crosscheck") and whole and (rdir / whole["file"]).exists():
        tmp = bpy.data.scenes.new("_crosscheck")
        win_scene = bpy.context.window.scene if bpy.context.window else None
        try:
            with bpy.context.temp_override(scene=tmp):
                objs = F.import_file(rdir / whole["file"], whole["format"], whole.get("scale_to_m"), whole.get("up_axis", "Z"))
            ms = [o for o in objs if o.type == "MESH"]
            csize = [round(float(v), 3) for v in
                     (Vector([max(U.exact_world_bbox(o)[1][i] for o in ms) for i in range(3)]) -
                      Vector([min(U.exact_world_bbox(o)[0][i] for o in ms) for i in range(3)])) / U.MM]
            check("crosscheck.assembly_bbox", close(csize, man["bbox_mm"]["size"], max(0.5, 0.003 * max(csize))),
                  measured=csize, expected=man["bbox_mm"]["size"], file=whole["file"])
            check("crosscheck.assembly_mesh_count", len(ms) >= len(vis), meshes=len(ms), components=len(vis),
                  note="bodies, so >= components for multi-body parts")
            for o in objs:
                bpy.data.objects.remove(o)
        except Exception as e:  # noqa: BLE001
            check("crosscheck.assembly", False, error=str(e))
        finally:
            if win_scene:
                bpy.context.window.scene = win_scene
            bpy.data.scenes.remove(tmp)
        purge()

    ok = all(c["pass"] for c in checks)
    out_blend = rdir / "blender" / f"{man['assembly']}_cad.blend"
    out_blend.parent.mkdir(parents=True, exist_ok=True)
    scene["cad_manifest"] = str(mpath)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), compress=True)
    report = {"pass": ok, "seconds": round(time.time() - t0, 1), "blend": str(out_blend),
              "source": man["source"]["adapter"], "validation_reference": man["validation"]["reference"],
              "tessellation": {"tol_linear_mm": prefs.tol_linear, "tol_angular_rad": prefs.tol_angular} if prefs else None,
              "formats": sorted(formats),
              "triangles_total": sum(r["triangles"] for r in parts_report.values()),
              "parts": parts_report, "checks": checks}
    U.save_json(rdir / "reports" / "import_report.json", report)
    for c in checks:
        if not c["pass"] or not c["id"].startswith("part_bbox"):
            U.log("PASS" if c["pass"] else "FAIL", c["id"], {k: v for k, v in c.items() if k not in ("id", "pass", "wrong")}
                  if c["pass"] else {k: v for k, v in c.items() if k not in ("id", "pass")})
    U.log(f"{'PASS' if ok else 'FAIL'} import ({man['source']['adapter']}): {len(placed)} components, {len(meshes)} parts, "
          f"{report['triangles_total']} triangles, {report['seconds']} s -> {out_blend}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
