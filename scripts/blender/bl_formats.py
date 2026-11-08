"""Geometry importers for every format the render pipeline accepts, behind one call.

    objs = bl_formats.import_file(path, fmt, scale_to_m=None, up_axis="Z")

Everything comes out in metres, Z-up (the scene frame). Operator options were read from
Blender 5.2's RNA (see docs/rendering.md); nothing here guesses an option name.

- step: STEP Importer extension (cascadio -> glTF). STEP carries units; up_axis="Y" turns
  cascadio's glTF Y-up back into the CAD Z-up frame (verified).
- gltf: glTF is metres and Y-up by definition; Blender's importer converts to Z-up.
- fbx, usd: carry units; their importers apply them.
- obj, stl, ply: no units in the file. `scale_to_m` (0.001 for mm, the CAD default) and the
  file's up axis (CAD files are usually Z-up) must be given.
"""
import bpy

import bl_util as U

AXES = {"Z": ("Y", "Z"), "Y": ("NEGATIVE_Z", "Y")}  # file up axis -> (forward_axis, up_axis) for obj/stl/ply


def step_prefs(tol_linear=0.01, tol_angular=0.1):
    addon = bpy.context.preferences.addons.get(U.STEP_ADDON)
    if addon is None:
        try:
            bpy.ops.preferences.addon_enable(module=U.STEP_ADDON)
            addon = bpy.context.preferences.addons.get(U.STEP_ADDON)
        except Exception:  # noqa: BLE001
            addon = None
    if addon is None or not hasattr(bpy.ops.import_scene, "step"):
        raise SystemExit("STEP Importer extension is not installed/enabled. See docs/rendering.md (Installation).")
    p = addon.preferences
    p.tol_linear = float(tol_linear)    # absolute, mm (with tol_relative off; verified)
    p.tol_angular = float(tol_angular)  # radians
    p.tol_relative = False
    p.import_materials = True
    p.shade_smooth = True
    p.show_progress = False
    return p


def import_file(path, fmt, scale_to_m=None, up_axis="Z"):
    """Import one geometry file into the current scene; returns the new objects."""
    path = str(path)
    before = set(bpy.data.objects)
    if fmt == "step":
        res = bpy.ops.import_scene.step(filepath=path, up_axis="Y", scale=1.0, merge_objects=False,
                                        use_assembly_collections=False, placement="ORIGIN", origin_offset="KEEP")
    elif fmt == "gltf":
        res = bpy.ops.import_scene.gltf(filepath=path)
    elif fmt in ("obj", "stl", "ply"):
        if scale_to_m is None:
            raise ValueError(f"{fmt} has no units: scale_to_m is required (0.001 for mm)")
        fwd, up = AXES[(up_axis or "Z").upper()]
        op = {"obj": bpy.ops.wm.obj_import, "stl": bpy.ops.wm.stl_import, "ply": bpy.ops.wm.ply_import}[fmt]
        res = op(filepath=path, global_scale=float(scale_to_m), forward_axis=fwd, up_axis=up)
    elif fmt == "fbx":
        res = bpy.ops.import_scene.fbx(filepath=path)
    elif fmt == "usd":
        res = bpy.ops.wm.usd_import(filepath=path, apply_unit_conversion_scale=True)
    else:
        raise ValueError(f"unknown geometry format {fmt}")
    if "FINISHED" not in res:
        raise RuntimeError(f"{fmt} importer returned {res} for {path}")
    bpy.context.view_layer.update()
    return [o for o in bpy.data.objects if o not in before]


def linear_to_srgb(rgb):
    return [c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055 for c in rgb]


def base_color(objs):
    """First Principled base colour found on the imported objects, as sRGB 0..1 (the form
    CAD colours are given in), or None."""
    for o in objs:
        for slot in getattr(o, "material_slots", ()):
            m = slot.material
            if m and m.use_nodes:
                bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf:
                    return [round(c, 4) for c in linear_to_srgb(bsdf.inputs["Base Color"].default_value[:3])]
    return None


def material_name(objs):
    for o in objs:
        for slot in getattr(o, "material_slots", ()):
            if slot.material:
                return slot.material.name
    return ""
