"""Principled BSDF materials from libraries/render/materials.json, and their assignment.

Resolution order for one component (later wins):
  library material proposed in the manifest (per part)
  -> settings.materials.parts[<part_id>]
  -> settings.materials.components[<component id or label>]
An assignment is {"material": id, "finish": id, "color": "#hex", "roughness": x, ...};
any field of a library material can be overridden. Equal resolved assignments share one
Blender material.
"""
import copy
import hashlib
import json

import bpy

import bl_util as U

PRINCIPLED_INPUTS = {
    "metallic": "Metallic", "roughness": "Roughness", "ior": "IOR", "transmission": "Transmission Weight",
    "anisotropy": "Anisotropic", "anisotropic_rotation": "Anisotropic Rotation", "coat": "Coat Weight",
    "coat_roughness": "Coat Roughness", "subsurface": "Subsurface Weight", "specular": "Specular IOR Level",
    "alpha": "Alpha", "sheen": "Sheen Weight",
}


def resolve(library, proposal, part_over=None, comp_over=None):
    """Merged material spec for one component."""
    a = {}
    for layer in (proposal or {}, part_over or {}, comp_over or {}):
        a.update({k: v for k, v in layer.items() if v is not None and not k.startswith("_")})
    mid = a.get("material") or library["name_rules"]["default"]
    if mid not in library["materials"]:
        U.log(f"unknown material '{mid}', using aluminium_raw")
        mid = "aluminium_raw"
    spec = copy.deepcopy(library["materials"][mid])
    spec["id"] = mid
    fin = a.get("finish")
    if fin:
        spec.update(copy.deepcopy(library["finishes"].get(fin, {})))
        spec["finish"] = fin
    for k in ("color", "base_color"):
        if a.get(k):
            spec["base_color"] = a[k]
    for k in list(PRINCIPLED_INPUTS) + ["bump", "variation", "brush", "emission", "emission_strength"]:
        if k in a:
            spec[k] = a[k]
    return spec


def _key(spec):
    keep = {k: v for k, v in spec.items() if k not in ("name", "category", "_note")}
    return hashlib.sha1(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:8]


def tree(m):
    """Node tree of a material (Blender 5 always has one; older versions need use_nodes)."""
    if m.node_tree is None:
        m.use_nodes = True
    return m.node_tree


def principled(nt):
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return b


def _node(nt, kind, loc, **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
    return n


def build(spec):
    """Blender material for a resolved spec (cached by content)."""
    name = f"M_{spec['id']}{'_' + spec['finish'] if spec.get('finish') else ''}_{_key(spec)}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m["render_spec"] = json.dumps(spec)
    nt = tree(m)
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (900, 0))
    bsdf = _node(nt, "ShaderNodeBsdfPrincipled", (500, 0))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    col = U.srgb_to_linear(spec.get("base_color", "#CCCCCC")) + [1.0]
    bsdf.inputs["Base Color"].default_value = col
    for k, inp in PRINCIPLED_INPUTS.items():
        if k in spec and inp in bsdf.inputs:
            bsdf.inputs[inp].default_value = spec[k]
    if spec.get("transmission", 0) > 0:
        bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.0)
    if spec.get("emission"):
        bsdf.inputs["Emission Color"].default_value = U.srgb_to_linear(spec["emission"]) + [1.0]
        bsdf.inputs["Emission Strength"].default_value = spec.get("emission_strength", 2.0)
    if spec.get("alpha", 1.0) < 1.0 and hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"

    tex = _node(nt, "ShaderNodeTexCoord", (-900, 0))
    obj = tex.outputs["Object"]

    # low-frequency roughness variation, so large faces are not perfectly uniform
    var = spec.get("variation", 0.0)
    if var > 0:
        noise = _node(nt, "ShaderNodeTexNoise", (-500, 250), Scale=12.0, Detail=2.0, Roughness=0.5)
        nt.links.new(obj, noise.inputs["Vector"])
        rng = _node(nt, "ShaderNodeMapRange", (-200, 250))
        rng.inputs["To Min"].default_value = max(0.0, spec.get("roughness", 0.4) - var / 2)
        rng.inputs["To Max"].default_value = min(1.0, spec.get("roughness", 0.4) + var / 2)
        nt.links.new(noise.outputs["Fac"], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], bsdf.inputs["Roughness"])

    # surface relief (tiny: these are rendering cues, not geometry)
    bump = spec.get("bump") or {"type": "none"}
    kind, scale_mm, strength = bump.get("type", "none"), bump.get("scale", 0.2), bump.get("strength", 0.05)
    height = None
    if kind in ("noise", "orange_peel"):
        n = _node(nt, "ShaderNodeTexNoise", (-500, -150), Scale=1.0 / (scale_mm * U.MM),
                  Detail=4.0 if kind == "noise" else 1.0, Roughness=0.6)
        nt.links.new(obj, n.inputs["Vector"])
        height = n.outputs["Fac"]
    elif kind == "brushed":
        # fine streaks along the brush direction: radial_z (turned parts) or linear_x (flat stock)
        mp = _node(nt, "ShaderNodeMapping", (-700, -150))
        if spec.get("brush", "radial_z") == "linear_x":
            mp.inputs["Scale"].default_value = (2.0, 300.0, 300.0)
            src = obj
        else:  # lathe marks: rings around Z, i.e. noise varying along the height and radius
            sep = _node(nt, "ShaderNodeSeparateXYZ", (-900, -300))
            nt.links.new(obj, sep.inputs["Vector"])
            ln = _node(nt, "ShaderNodeVectorMath", (-800, -300))
            ln.operation = "LENGTH"
            comb = _node(nt, "ShaderNodeCombineXYZ", (-750, -350))
            xy = _node(nt, "ShaderNodeCombineXYZ", (-850, -400))
            nt.links.new(sep.outputs["X"], xy.inputs["X"])
            nt.links.new(sep.outputs["Y"], xy.inputs["Y"])
            nt.links.new(xy.outputs["Vector"], ln.inputs[0])
            nt.links.new(ln.outputs["Value"], comb.inputs["X"])
            nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
            src = comb.outputs["Vector"]
            mp.inputs["Scale"].default_value = (300.0, 300.0, 1.0)
        nt.links.new(src, mp.inputs["Vector"])
        n = _node(nt, "ShaderNodeTexNoise", (-500, -150), Scale=1.0 / (scale_mm * U.MM) / 300.0, Detail=6.0)
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        height = n.outputs["Fac"]
        tan = _node(nt, "ShaderNodeTangent", (100, -350))
        tan.direction_type = "RADIAL"
        tan.axis = "X" if spec.get("brush") == "linear_x" else "Z"
        if "Tangent" in bsdf.inputs:
            nt.links.new(tan.outputs["Tangent"], bsdf.inputs["Tangent"])
    elif kind == "layer_lines":  # FDM layers stacked along Z
        w = _node(nt, "ShaderNodeTexWave", (-500, -150), Scale=0.314 / (scale_mm * U.MM), Distortion=0.0)
        w.wave_type, w.bands_direction = "BANDS", "Z"
        nt.links.new(obj, w.inputs["Vector"])
        height = w.outputs["Fac"]
    if spec.get("grain"):  # wood: distorted rings for colour and a hint of relief
        w = _node(nt, "ShaderNodeTexWave", (-500, 450), Scale=60.0, Distortion=6.0, Detail=3.0)
        w.wave_type, w.rings_direction = "RINGS", "X"
        nt.links.new(obj, w.inputs["Vector"])
        mix = _node(nt, "ShaderNodeMix", (100, 350))
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = col
        mix.inputs["B"].default_value = [c * 0.55 for c in col[:3]] + [1.0]
        nt.links.new(w.outputs["Fac"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    if height is not None and strength > 0:
        b = _node(nt, "ShaderNodeBump", (200, -200), Strength=min(1.0, strength), Distance=scale_mm * U.MM * 0.5)
        nt.links.new(height, b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
        if "Coat Normal" in bsdf.inputs and spec.get("coat", 0) > 0 and kind != "orange_peel":
            pass  # the clear coat stays smooth over a textured base, as on real anodising
    return m


def assign(objects, manifest, settings, library=None):
    """Assign materials to CAD objects (those with an sw_id). Returns the assignment table."""
    library = library or U.lib("materials")
    mset = settings.get("materials", {})
    table = []
    for ob in objects:
        if "sw_id" not in ob:
            continue
        part = manifest["parts"].get(ob["sw_part"], {})
        proposal = part.get("material", {})
        comp_over = mset.get("components", {}).get(ob["sw_id"]) or mset.get("components", {}).get(ob.get("sw_label", ""))
        spec = resolve(library, proposal, mset.get("parts", {}).get(ob["sw_part"]), comp_over)
        mat = build(spec)
        for slot in ob.material_slots:
            slot.link = "OBJECT"
            slot.material = mat
        src = "component override" if comp_over else ("part setting" if ob["sw_part"] in mset.get("parts", {}) else
                                                      proposal.get("source", "default"))
        table.append({"component": ob["sw_id"], "label": ob.get("sw_label", ""), "part": ob["sw_part"],
                      "material": spec["id"], "finish": spec.get("finish"), "color": spec.get("base_color"),
                      "roughness": spec.get("roughness"), "source": src,
                      "confidence": "user/claude" if src in ("component override", "part setting")
                      else proposal.get("confidence", "low")})
    return table


def simple(name, color, roughness=0.5, metallic=0.0, emission=None, strength=0.0, alpha=1.0):
    """Plain material for scene props (floors, walls, furniture)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = tree(m)
    bsdf = principled(nt)
    bsdf.inputs["Base Color"].default_value = U.srgb_to_linear(color) + [1.0]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = U.srgb_to_linear(emission) + [1.0]
        bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
    return m


def textured(name, kind, color, color2, scale, roughness=0.5, bump=0.1, metallic=0.0, vertical=False):
    """Procedural prop material: kind = concrete | tiles | pegboard | plaster | wood | ribs | brushed_metal."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = tree(m)
    bsdf = principled(nt)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    tc0 = _node(nt, "ShaderNodeTexCoord", (-1200, 0))
    tc = _node(nt, "ShaderNodeMapping", (-1000, 0))  # walls (vertical=True): pattern in x/z
    if vertical:
        tc.inputs["Rotation"].default_value = (1.5708, 0.0, 0.0)
    nt.links.new(tc0.outputs["Object"], tc.inputs["Vector"])
    c1, c2 = U.srgb_to_linear(color) + [1.0], U.srgb_to_linear(color2) + [1.0]
    mix = _node(nt, "ShaderNodeMix", (-200, 200))
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value, mix.inputs["B"].default_value = c1, c2
    if kind in ("tiles", "pegboard"):
        t = _node(nt, "ShaderNodeTexBrick", (-600, 200), Scale=scale, **{"Mortar Size": 0.03 if kind == "tiles" else 0.0})
        t.offset = 0.0 if kind == "pegboard" else 0.5
        nt.links.new(tc.outputs["Vector"], t.inputs["Vector"])
        t.inputs["Color1"].default_value = t.inputs["Color2"].default_value = c1
        t.inputs["Mortar"].default_value = c2
        fac = t.outputs["Fac"]
        if kind == "pegboard":  # round holes on a grid
            v = _node(nt, "ShaderNodeTexVoronoi", (-600, -100), Scale=scale)
            v.feature = "F1"
            v.voronoi_dimensions = "2D"
            nt.links.new(tc.outputs["Vector"], v.inputs["Vector"])
            v.inputs["Randomness"].default_value = 0.0
            lt = _node(nt, "ShaderNodeMath", (-400, -100))
            lt.operation = "LESS_THAN"
            lt.inputs[1].default_value = 0.18
            nt.links.new(v.outputs["Distance"], lt.inputs[0])
            fac = lt.outputs["Value"]
        nt.links.new(fac, mix.inputs["Factor"])
    elif kind == "ribs":  # vertical cladding ribs: sharp bands along X
        w = _node(nt, "ShaderNodeTexWave", (-600, 200), Scale=scale, Distortion=0.0)
        w.wave_type, w.bands_direction, w.wave_profile = "BANDS", "X", "SAW"
        nt.links.new(tc.outputs["Vector"], w.inputs["Vector"])
        nt.links.new(w.outputs["Fac"], mix.inputs["Factor"])
        fac = w.outputs["Fac"]
    elif kind == "wood":
        # fine grain along X: bands across Y, lightly distorted (scale = bands per metre / ~3)
        mp = _node(nt, "ShaderNodeMapping", (-800, 200))
        mp.inputs["Scale"].default_value = (0.15, 1.0, 1.0)
        nt.links.new(tc.outputs["Vector"], mp.inputs["Vector"])
        w = _node(nt, "ShaderNodeTexWave", (-600, 200), Scale=scale, Distortion=2.5, Detail=6.0, **{"Detail Scale": 2.0})
        w.wave_type, w.bands_direction = "BANDS", "Y"
        nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
        nt.links.new(w.outputs["Fac"], mix.inputs["Factor"])
        fac = w.outputs["Fac"]
    else:  # concrete, plaster, brushed_metal: noise
        n = _node(nt, "ShaderNodeTexNoise", (-600, 200), Scale=scale, Detail=8.0, Roughness=0.6)
        nt.links.new(tc.outputs["Vector"], n.inputs["Vector"])
        ramp = _node(nt, "ShaderNodeMapRange", (-400, 200))
        ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.35, 0.65
        nt.links.new(n.outputs["Fac"], ramp.inputs["Value"])
        nt.links.new(ramp.outputs["Result"], mix.inputs["Factor"])
        fac = n.outputs["Fac"]
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    if bump > 0:
        b = _node(nt, "ShaderNodeBump", (0, -200), Strength=bump, Distance=0.002)
        nt.links.new(fac, b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m
