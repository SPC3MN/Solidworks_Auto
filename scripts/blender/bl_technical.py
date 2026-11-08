"""Exploded and technical presentation: exploded copies, see-through housings, cutaways,
highlighting, isolation and hiding.

The assembled CAD objects are never moved. The exploded view is a second collection of
linked duplicates (sharing the meshes) placed at assembled transform + the manifest's
explode offset (from a designed exploded assembly or computed from the hierarchy).
Per-shot overrides change material slots and visibility and are undone after the shot.
"""
import bpy
from mathutils import Vector

import bl_materials as BM
import bl_util as U


def exploded_collection(cad_objs, manifest, scene_coll_name, scale=1.0):
    ex = manifest.get("exploded") or {}
    offs = ex.get("offsets_mm", {})
    root = bpy.data.collections.new(f"CAD_{manifest['assembly']}_exploded")
    root["cad_role"] = "exploded"
    out = []
    for ob in cad_objs:
        dup = ob.copy()  # linked duplicate: same mesh
        dup.name = f"{ob.name}.exploded"
        off = Vector(offs.get(ob["cad_id"], (0, 0, 0))) * U.MM * scale
        dup.matrix_world = ob.matrix_world.copy()
        dup.matrix_world.translation = ob.matrix_world.translation + off
        dup["explode_offset_mm"] = list(offs.get(ob["cad_id"], (0, 0, 0)))
        root.objects.link(dup)
        for s_src, s_dup in zip(ob.material_slots, dup.material_slots):
            s_dup.link = "OBJECT"
            s_dup.material = s_src.material
        out.append(dup)
    return root, out, ex.get("method", "none")


def _match(ob, keys):
    return bool(keys) and (ob.get("cad_id") in keys or ob.get("cad_label") in keys or ob.get("cad_part") in keys)


def auto_housing(objs):
    """The component whose box contains the most other component centres (the enclosure)."""
    best, n_best = None, 0
    for ob in objs:
        lo, hi = U.exact_world_bbox(ob)
        n = 0
        for o2 in objs:
            if o2 is ob:
                continue
            a, b = U.exact_world_bbox(o2)
            c = (a + b) / 2
            n += all(lo[i] <= c[i] <= hi[i] for i in range(3))
        if n > n_best:
            best, n_best = ob, n
    return best


def cutaway_material(base, centre, axis, keep_positive, section_color="#D2462D"):
    """Copy of `base` that is transparent on one side of a plane through `centre`, with the
    exposed inside faces (back faces) shown in a flat section colour."""
    name = f"{base.name}_cut_{axis}{'p' if keep_positive else 'n'}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = base.copy()
    m.name = name
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surf = out.inputs["Surface"].links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    cmp = nt.nodes.new("ShaderNodeMath")
    cmp.operation = "LESS_THAN" if keep_positive else "GREATER_THAN"
    cmp.inputs[1].default_value = centre["xyz".index(axis)]
    nt.links.new(sep.outputs[axis.upper()], cmp.inputs[0])
    sec = nt.nodes.new("ShaderNodeBsdfPrincipled")
    sec.inputs["Base Color"].default_value = U.srgb_to_linear(section_color) + [1.0]
    sec.inputs["Roughness"].default_value = 0.6
    inside = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], inside.inputs["Fac"])
    nt.links.new(surf, inside.inputs[1])
    nt.links.new(sec.outputs["BSDF"], inside.inputs[2])
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    cut = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cmp.outputs["Value"], cut.inputs["Fac"])
    nt.links.new(inside.outputs["Shader"], cut.inputs[1])
    nt.links.new(transp.outputs["BSDF"], cut.inputs[2])
    nt.links.new(cut.outputs["Shader"], out.inputs["Surface"])
    return m


def apply_overrides(objs, shot, settings, product_box):
    """Apply a shot's technical overrides. Returns (undo function, description)."""
    tech = dict(settings.get("technical", {}))
    tech.update({k: shot[k] for k in ("xray", "highlight", "cutaway", "hide", "isolate") if k in shot})
    saved_mats = [(s, s.material) for ob in objs for s in ob.material_slots]
    saved_vis = [(ob, ob.hide_render) for ob in objs]
    desc = {}
    lib = U.lib("materials")

    xray = tech.get("xray") or []
    if xray == "auto" or xray == ["auto"]:
        h = auto_housing([o for o in objs if not o.hide_render])
        xray = [h["cad_id"]] if h else []
    if xray:
        mat = BM.build(BM.resolve(lib, {"material": "xray_housing"}))
        for ob in objs:
            if _match(ob, xray):
                for s in ob.material_slots:
                    s.material = mat
        desc["xray"] = xray
    hl = tech.get("highlight") or {}
    if hl.get("components"):
        mat = BM.build(BM.resolve(lib, {"material": "powder_gloss", "color": hl.get("color", "#FF7A00"),
                                        "emission": hl.get("color", "#FF7A00"), "emission_strength": 0.3}))
        for ob in objs:
            if _match(ob, hl["components"]):
                for s in ob.material_slots:
                    s.material = mat
        desc["highlight"] = hl
    cut = tech.get("cutaway") or {}
    if cut.get("components"):
        lo, hi = product_box
        centre = list(cut.get("centre_m") or ((lo + hi) / 2))
        targets = cut["components"]
        if targets in ("auto", ["auto"]):
            h = auto_housing([o for o in objs if not o.hide_render])
            targets = [h["cad_id"]] if h else []
        for ob in objs:
            if _match(ob, targets):
                for s in ob.material_slots:
                    if s.material:
                        s.material = cutaway_material(s.material, centre, cut.get("axis", "y"), cut.get("keep", "+") == "+")
        desc["cutaway"] = {"components": targets, "axis": cut.get("axis", "y"), "keep": cut.get("keep", "+")}
    iso = tech.get("isolate") or []
    hide = tech.get("hide") or []
    for ob in objs:
        if (iso and not _match(ob, iso)) or _match(ob, hide):
            ob.hide_render = True
    if iso:
        desc["isolate"] = iso
    if hide:
        desc["hide"] = hide

    def undo():
        for s, m in saved_mats:
            s.material = m
        for ob, h in saved_vis:
            ob.hide_render = h
    return undo, desc
