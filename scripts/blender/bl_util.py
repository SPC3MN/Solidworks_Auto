"""Shared helpers for the scripts that run inside Blender (blender -b --python ...).

Units: the Blender scene is in metres (the STEP Importer outputs metres). The manifest
is in mm, so every manifest length is multiplied by MM when it enters Blender.
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

MM = 0.001
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIB = ROOT / "libraries" / "render"
STEP_ADDON = "bl_ext.user_default.step_importer"


def script_args():
    """Arguments after '--' on the Blender command line, as a dict of --key value pairs."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, key = {}, None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
            out[key] = True
        elif key:
            out[key] = a
            key = None
    return out


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")


def lib(name):
    return load_json(LIB / f"{name}.json")


def log(*a):
    print("[render]", *a, flush=True)


def srgb_to_linear(hex_or_rgb):
    if isinstance(hex_or_rgb, str):
        h = hex_or_rgb.lstrip("#")
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    else:
        rgb = list(hex_or_rgb)[:3]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]


def kelvin_rgb(k):
    """Approximate linear RGB of a black body at k kelvin (normalised so the max channel is 1)."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    rgb = [min(max(c, 0), 255) / 255 for c in (r, g, b)]
    lin = srgb_to_linear(rgb)
    m = max(lin)
    return [c / m for c in lin]


def matrix_from_manifest(rows):
    m = Matrix([list(r) for r in rows])
    m.translation = Vector(m.translation) * MM
    return m


def world_bbox(objs):
    """(min, max) Vectors of the evaluated world-space bounding boxes of mesh objects."""
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return (Vector([min(p[i] for p in pts) for i in range(3)]),
            Vector([max(p[i] for p in pts) for i in range(3)]))


def exact_world_bbox(obj):
    """Bounding box from the vertices (bound_box of a rotated object is loose)."""
    mw = obj.matrix_world
    vs = [mw @ v.co for v in obj.data.vertices]
    return (Vector([min(v[i] for v in vs) for i in range(3)]),
            Vector([max(v[i] for v in vs) for i in range(3)]))


def local_aabb_world(obj):
    """The mesh's local bbox corners carried through matrix_world, then boxed: the same
    quantity the adapters compute from (part bbox, transform), so comparing the two checks
    the transform exactly, whatever the rotation."""
    me = obj.data
    lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
    pts = [obj.matrix_world @ Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    return (Vector([min(p[i] for p in pts) for i in range(3)]),
            Vector([max(p[i] for p in pts) for i in range(3)]))


def load_manifest(path):
    """The product manifest as schema 2.0 (older files are upgraded in memory)."""
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from render_adapters import common
    return common.load(path)


def collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in par.children]:
        par.children.link(c)
    return c


def clear_scene():
    """Empty file with addons still enabled (read_factory_settings would disable them)."""
    bpy.ops.wm.read_homefile(use_empty=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.objects, bpy.data.collections,
                bpy.data.lights, bpy.data.cameras, bpy.data.worlds, bpy.data.images, bpy.data.node_groups):
        for item in list(blk):
            blk.remove(item)
