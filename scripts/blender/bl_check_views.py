"""Pipeline check renders for backends without a viewport (FreeCAD): the exported STL in the
Z-up named views of swlib.render (isometric, top, front, right), shaded with Workbench.

    blender -b --python bl_check_views.py -- --stl part.stl --out renders/ [--size 800] [--views isometric,front]
"""
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bl_util import MM, clear_scene, log, script_args, world_bbox  # noqa: E402

S2, S3, S6 = 2 ** 0.5, 3 ** 0.5, 6 ** 0.5
# (screen-right, screen-up, toward-viewer) in model axes, as in swlib.Z_UP_VIEWS
VIEWS = {
    "isometric": ((1 / S2, 1 / S2, 0), (-1 / S6, 1 / S6, 2 / S6), (1 / S3, -1 / S3, 1 / S3)),
    "top": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "right": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
}


def main():
    a = script_args()
    out = pathlib.Path(a["out"])
    out.mkdir(parents=True, exist_ok=True)
    size = int(a.get("size", 800))
    clear_scene()
    bpy.ops.wm.stl_import(filepath=a["stl"], global_scale=MM)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo, hi = world_bbox(objs)
    centre = (lo + hi) / 2
    corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (0.72, 0.75, 0.82)
    sc.display.shading.show_cavity = True
    sc.display.shading.show_object_outline = True
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.view_settings.view_transform = "Standard"

    cam_data = bpy.data.cameras.new("check")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("check", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    span = (hi - lo).length
    cam_data.clip_start, cam_data.clip_end = span * 0.01, span * 10

    names = a["views"].split(",") if isinstance(a.get("views"), str) else list(VIEWS)
    for name in names:
        r, u, d = VIEWS[name]
        r, u, d = Vector(r), Vector(u), Vector(d)
        rot = Matrix((r, u, d)).transposed().to_4x4()
        cam.matrix_world = Matrix.Translation(centre + d * span * 2) @ rot
        w = max(abs((c - centre).dot(r)) for c in corners) * 2
        h = max(abs((c - centre).dot(u)) for c in corners) * 2
        cam_data.ortho_scale = max(w, h) * 1.1
        sc.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        log(f"view {name} -> {sc.render.filepath}")


main()
