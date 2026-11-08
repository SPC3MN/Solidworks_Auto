"""Generic adapter, Blender side: any 3D file -> one GLB per unique part + raw product data.

    blender -b --python scripts/blender/bl_ingest.py -- --source <file> --render-dir <folder>/render
        --out-json <raw.json> [--units mm] [--up Z] [--tol-linear 0.01] [--tol-angular 0.1]

Used for products that arrive as files (a STEP from FreeCAD, Onshape, Fusion, Inventor, Creo,
CATIA, a vendor download; or glTF/OBJ/STL/PLY/FBX/USD). The host side
(scripts/render_adapters/mesh_file.py) turns the raw data into the product manifest.

Structure recovered from the file:
- every mesh object is a component; its world matrix is the component transform
- empties above it are subassemblies (a single top-level empty is the product root)
- instances: STEP and glTF keep each instance's geometry in part coordinates, so components
  whose meshes match (same base name without Blender's ".001" suffix, same vertex and face
  count, same local bbox to 0.01 mm) become one part with several components. Meshes that are
  baked in world coordinates (OBJ, STL) simply become one part each.
"""
import json
import pathlib
import re
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bl_formats as F  # noqa: E402
import bl_util as U  # noqa: E402

SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def clean(name):
    return SAFE.sub("_", re.sub(r"\.\d{3}$", "", name)).strip("_") or "part"


def path_of(ob, root):
    names = []
    while ob is not None and ob is not root:
        names.append(ob.name)
        ob = ob.parent
    return "/".join(reversed(names))


def main():
    a = U.script_args()
    src = pathlib.Path(a["source"]).resolve()
    rdir = pathlib.Path(a["render-dir"]).resolve()
    fmt = a["format"]
    scale = float(a["scale-to-m"]) if a.get("scale-to-m") else None
    U.clear_scene()
    if fmt == "step":
        F.step_prefs(a.get("tol-linear", 0.01), a.get("tol-angular", 0.1))
    objs = F.import_file(src, fmt, scale, a.get("up", "Z"))
    meshes = [o for o in objs if o.type == "MESH" and len(o.data.vertices)]
    if not meshes:
        raise SystemExit(f"no mesh geometry in {src}")
    tops = [o for o in objs if o.parent is None]
    root_ob = tops[0] if len(tops) == 1 and tops[0].type == "EMPTY" else None
    root = clean(root_ob.name) if root_ob else clean(src.stem)

    hierarchy = [{"id": root, "parent": None, "kind": "assembly"}]
    for o in objs:
        if o.type == "EMPTY" and o is not root_ob and any(m in meshes for m in o.children_recursive):
            par = path_of(o.parent, root_ob) if o.parent and o.parent is not root_ob else root
            hierarchy.append({"id": path_of(o, root_ob), "parent": par or root, "kind": "subassembly"})

    parts, comps, prints = {}, [], {}
    geo = rdir / "export" / "geometry" / "parts"
    geo.mkdir(parents=True, exist_ok=True)
    for o in sorted(meshes, key=lambda m: path_of(m, root_ob)):
        me = o.data
        lo = Vector([min(v.co[i] for v in me.vertices) for i in range(3)])
        hi = Vector([max(v.co[i] for v in me.vertices) for i in range(3)])
        base = clean(me.name if me.users > 1 else o.name)
        fp = (me.name if me.users > 1 else None, len(me.vertices), len(me.polygons),
              tuple(round(x / U.MM, 2) for x in (*lo, *hi)))
        pid = prints.get((base, fp))
        if pid is None:
            pid, k = base, 2
            while pid in parts:
                pid, k = f"{base}_{k}", k + 1
            prints[(base, fp)] = pid
            parts[pid] = {"mesh": me, "bbox_min": [v / U.MM for v in lo], "bbox_max": [v / U.MM for v in hi],
                          "color": F.base_color([o]), "material_name": F.material_name([o]),
                          "file": str((geo / f"{pid}.glb").relative_to(rdir)).replace("\\", "/")}
        mw = o.matrix_world
        t = [[mw[i][j] for j in range(4)] for i in range(4)]
        for i in range(3):
            t[i][3] = mw[i][3] / U.MM
        wlo, whi = U.exact_world_bbox(o)
        cid = path_of(o, root_ob)
        par = path_of(o.parent, root_ob) if o.parent and o.parent is not root_ob else root
        comps.append({"id": cid, "name": o.name, "parent": par or root, "part": pid, "transform": t,
                      "visible": not o.hide_render, "world_bbox_mm": [[v / U.MM for v in wlo], [v / U.MM for v in whi]],
                      "source": {k: o[k] for k in o.keys() if isinstance(o[k], (str, int, float))}})

    # one GLB per unique part, in part coordinates (identity transform)
    for pid, p in parts.items():
        ob = bpy.data.objects.new(f"_export_{pid}", p["mesh"])
        bpy.context.scene.collection.objects.link(ob)
        for other in bpy.context.view_layer.objects:
            other.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        res = bpy.ops.export_scene.gltf(filepath=str(rdir / p["file"]), export_format="GLB", use_selection=True,
                                        export_yup=True, export_apply=False, export_materials="EXPORT", export_extras=False)
        if "FINISHED" not in res:
            raise SystemExit(f"GLB export failed for {pid}")
        bpy.data.objects.remove(ob)
        del p["mesh"]

    vis = [o for o in meshes if not o.hide_render]
    boxes = [U.exact_world_bbox(o) for o in vis]
    blo = Vector([min(b[0][i] for b in boxes) for i in range(3)])
    bhi = Vector([max(b[1][i] for b in boxes) for i in range(3)])
    out = {"root": root, "format": fmt, "hierarchy": hierarchy, "parts": parts, "components": comps,
           "bbox_mm": {"min": [v / U.MM for v in blo], "max": [v / U.MM for v in bhi]},
           "blender": bpy.app.version_string}
    pathlib.Path(a["out-json"]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    U.log(f"ingest {src.name}: {len(comps)} components, {len(parts)} unique parts, {len(hierarchy) - 1} subassemblies")


if __name__ == "__main__":
    main()
