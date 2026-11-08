"""Studio set: light rigs, world, backdrop sweep / floor, background.

Everything is sized from the product bounding box `box` = (min, max) in metres, so the
same preset works for a 20 mm encoder and a 2 m frame. The product is never moved:
the floor is put at the product's lowest point.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import bl_materials as BM
import bl_util as U


def product_metrics(box):
    lo, hi = box
    size = hi - lo
    centre = (lo + hi) / 2
    diag = max(size.length, 1e-3)
    return centre, size, diag


def direction(az, el):
    """Unit vector from the product toward a light/camera at azimuth az, elevation el (degrees)."""
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def aim(obj, target):
    d = target - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def lights(rig, box, mods, coll, prefix):
    """Create the lights of a rig preset (dict from lighting.json) in collection coll."""
    centre, size, diag = product_metrics(box)
    made = []
    inten = mods.get("intensity", 1.0)
    for i, L in enumerate(rig["lights"]):
        d = L["dist"] * diag
        e = L["irradiance"] * inten * (1.0 if i == 0 else mods.get("fill_ratio", 1.0))
        data = bpy.data.lights.new(f"{prefix}_{L['name']}", "AREA")
        data.shape = L.get("shape", "RECTANGLE")
        soft = mods.get("softness", 1.0)
        data.size = L["size"][0] * diag * soft
        if data.shape in ("RECTANGLE", "ELLIPSE"):
            data.size_y = L["size"][1] * diag * soft
        data.energy = e * math.pi * d * d
        data.color = U.kelvin_rgb(L.get("kelvin", 5600) + mods.get("warmth_kelvin", 0))
        if hasattr(data, "spread"):
            data.spread = math.radians(L.get("spread", 180))
        ob = bpy.data.objects.new(f"{prefix}_{L['name']}", data)
        ob.location = centre + direction(L["az"] + mods.get("rotate", 0), L["el"]) * d
        aim(ob, centre)
        coll.objects.link(ob)
        made.append(ob)
    for F in rig.get("flags", []):
        d = F["dist"] * diag
        me = box_mesh(f"{prefix}_{F['name']}", (F["size"][0] * diag, F["size"][1] * diag, 0.0))
        ob = bpy.data.objects.new(f"{prefix}_{F['name']}", me)
        me.materials.append(BM.simple("Flag_Black", "#050505", 0.9))
        ob.location = centre + direction(F["az"] + mods.get("rotate", 0), F["el"]) * d
        aim(ob, centre)
        ob.visible_camera = ob.visible_shadow = ob.visible_diffuse = False
        coll.objects.link(ob)
        made.append(ob)
    return made


def world(name, color, strength, gradient=None):
    """World: flat ambient colour; with gradient=(top, bottom) the camera sees a vertical
    gradient while lighting still uses the flat colour (Light Path: Is Camera Ray)."""
    w = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    nt = BM.tree(w)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = U.srgb_to_linear(color) + [1.0]
    bg.inputs["Strength"].default_value = strength
    if gradient:
        cam_bg = nt.nodes.new("ShaderNodeBackground")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Window"], sep.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = U.srgb_to_linear(gradient[1]) + [1.0]
        mix.inputs["B"].default_value = U.srgb_to_linear(gradient[0]) + [1.0]
        nt.links.new(sep.outputs["Y"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], cam_bg.inputs["Color"])
        cam_bg.inputs["Strength"].default_value = 1.0
        lp = nt.nodes.new("ShaderNodeLightPath")
        sel = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], sel.inputs["Fac"])
        nt.links.new(bg.outputs["Background"], sel.inputs[1])
        nt.links.new(cam_bg.outputs["Background"], sel.inputs[2])
        nt.links.new(sel.outputs["Shader"], out.inputs["Surface"])
    else:
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w


def sweep_mesh(name, width, depth, height, radius):
    """Cyclorama: floor toward -Y (the camera side), a curve of `radius`, then a wall at +Y."""
    bm = bmesh.new()
    prof = [(-depth, 0.0), (0.0, 0.0)]
    n = 16
    for i in range(1, n + 1):
        t = math.pi / 2 * i / n
        prof.append((radius * math.sin(t), radius * (1 - math.cos(t))))
    prof.append((radius, height))
    left = [bm.verts.new((-width / 2, y, z)) for y, z in prof]
    right = [bm.verts.new((width / 2, y, z)) for y, z in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def box_mesh(name, dims, bevel=0.0):
    """Axis-aligned box centred on x/y with its top face at z = 0 (a plane when dz = 0)."""
    dx, dy, dz = dims
    bm = bmesh.new()
    if dz <= 0:
        vs = [bm.verts.new((x * dx / 2, y * dy / 2, 0)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        bm.faces.new(vs)
    else:
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x, v.co.y, v.co.z = v.co.x * dx, v.co.y * dy, v.co.z * dz - dz / 2
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=3, affect="EDGES", profile=0.5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def backdrop(cfg_floor, cfg_bg, box, coll, prefix, transparent=False):
    """Floor sweep or plane under the product (top at the product's lowest point).
    Gradient backgrounds colour the sweep from floor to wall. With transparent film the
    floor becomes a shadow catcher, so contact shadows survive on a transparent PNG."""
    centre, size, diag = product_metrics(box)
    lo = box[0]
    kind = cfg_floor.get("type", "sweep")
    if kind == "none":
        return None
    s = max(diag, 0.05)
    if kind == "sweep":
        me = sweep_mesh(f"{prefix}_Sweep", width=12 * s, depth=8 * s, height=6 * s, radius=2.0 * s)
        ob = bpy.data.objects.new(f"{prefix}_Sweep", me)
        ob["sweep_offset"] = max(size.y / 2, 0) + 1.6 * s
        ob["sweep_centre"] = (centre.x, centre.y, lo.z)
        ob.location = (centre.x, centre.y + ob["sweep_offset"], lo.z)
    else:
        me = box_mesh(f"{prefix}_Floor", (30 * s, 30 * s, 0.0))
        ob = bpy.data.objects.new(f"{prefix}_Floor", me)
        ob.location = (centre.x, centre.y, lo.z)
    coll.objects.link(ob)
    col = cfg_floor.get("color", cfg_bg.get("color", "#EEEEEE"))
    rough = cfg_floor.get("roughness", 0.5)
    if cfg_bg.get("type") == "gradient" and kind == "sweep":
        m = bpy.data.materials.new(f"{prefix}_SweepGradient")
        nt = BM.tree(m)
        bsdf = BM.principled(nt)
        bsdf.inputs["Roughness"].default_value = rough
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.0, 5.0 * s
        nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = U.srgb_to_linear(cfg_floor.get("color", cfg_bg["color"])) + [1.0]
        mix.inputs["B"].default_value = U.srgb_to_linear(cfg_bg.get("color2", cfg_bg["color"])) + [1.0]
        nt.links.new(rng.outputs["Result"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        m = BM.simple(f"{prefix}_FloorMat", col, rough)
    ob.data.materials.append(m)
    if transparent:
        ob.is_shadow_catcher = True
    return ob


def orient_backdrop(ob, az):
    """Turn the sweep about the product so its wall is behind the camera's view (az in degrees)."""
    if ob is None or "sweep_offset" not in ob:
        return
    a = math.radians(az)
    cx, cy, z = ob["sweep_centre"]
    off = ob["sweep_offset"]
    ob.rotation_euler = (0.0, 0.0, a)
    ob.location = (cx - math.sin(a) * off, cy + math.cos(a) * off, z)


def build_studio(scene, box, settings, coll):
    """Studio set into `coll` and the scene world. Returns a description for the report."""
    lib = U.lib("lighting")["presets"]
    st = settings.get("studio", {})
    lmods = settings.get("lighting", {})
    preset_name = lmods.get("preset") or st.get("lighting", "soft_commercial")
    rig = lib[preset_name]
    bg = dict(rig["background"])
    bg.update(st.get("background", {}))
    fl = dict(rig["floor"])
    fl.update(st.get("floor", {}))
    transparent = bg.get("type") == "transparent"
    made = lights(rig, box, lmods, coll, "Studio")
    floor = backdrop(fl, bg, box, coll, "Studio", transparent)
    w = rig["world"]
    grad = (bg["color"], bg.get("color2", bg["color"])) if bg.get("type") in ("gradient", "solid") else None
    scene.world = world(f"World_Studio_{preset_name}", w["color"], w["strength"] * lmods.get("intensity", 1.0), grad)
    scene.render.film_transparent = transparent
    return {"lighting": preset_name, "lights": [o.name for o in made], "background": bg, "floor": fl,
            "look": lmods.get("look", rig.get("look", "None")), "exposure": lmods.get("exposure", rig.get("exposure", 0.0)),
            "floor_object": floor.name if floor else None}
