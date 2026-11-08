"""Procedural environments: workshop, laboratory, industrial, office, display, architectural.

All geometry is generated here (boxes, cylinders, procedural materials). No downloaded
assets, so there is nothing to license. The product is never moved: each room is built
around it, with the support surface (bench, desk, plinth, floor) touching the product's
lowest point, and props kept out of the product's box plus a clearance. Furniture keeps
real-world sizes; supports grow when the product is bigger than them.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import bl_materials as BM
import bl_stage as ST
import bl_util as U


class Room:
    def __init__(self, box, coll, name):
        self.lo, self.hi = box
        self.c = (self.lo + self.hi) / 2
        self.size = self.hi - self.lo
        self.z0 = self.lo.z
        self.coll = coll
        self.name = name
        self.props, self.lights = [], []
        self.foot = max(self.size.x, self.size.y)

    def box(self, label, dims, top_center, mat, bevel=0.0):
        """Box with its TOP face centred at top_center (x, y, z)."""
        me = ST.box_mesh(f"{self.name}_{label}", dims, bevel)
        ob = bpy.data.objects.new(f"{self.name}_{label}", me)
        ob.location = top_center
        me.materials.append(mat)
        self.coll.objects.link(ob)
        self.props.append(ob)
        return ob

    def cyl(self, label, r, h, base_center, mat, verts=48):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=h)
        for v in bm.verts:
            v.co.z += h / 2
        me = bpy.data.meshes.new(f"{self.name}_{label}")
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = len(p.vertices) == 4
        ob = bpy.data.objects.new(f"{self.name}_{label}", me)
        ob.location = base_center
        me.materials.append(mat)
        self.coll.objects.link(ob)
        self.props.append(ob)
        return ob

    def area(self, label, size, loc, target, irradiance, kelvin, shape="RECTANGLE", size_y=None):
        """Area light aimed at target; power from the irradiance wanted there (P = E pi d^2)."""
        d = bpy.data.lights.new(f"{self.name}_{label}", "AREA")
        d.shape = shape
        d.size = size
        if size_y:
            d.size_y = size_y
        dist = (Vector(loc) - Vector(target)).length
        d.energy = irradiance * math.pi * dist * dist
        d.color = U.kelvin_rgb(kelvin)
        ob = bpy.data.objects.new(d.name, d)
        ob.location = loc
        ST.aim(ob, Vector(target))
        self.coll.objects.link(ob)
        self.lights.append(ob)
        return ob

    def spot(self, label, loc, target, irradiance, kelvin, angle=35, blend=0.4, radius=0.05):
        """Spot light; power from the irradiance wanted at the target (P = E 4 pi d^2)."""
        d = bpy.data.lights.new(f"{self.name}_{label}", "SPOT")
        dist = (Vector(loc) - Vector(target)).length
        d.energy, d.spot_size, d.spot_blend = irradiance * 4 * math.pi * dist * dist, math.radians(angle), blend
        d.shadow_soft_size = radius
        d.color = U.kelvin_rgb(kelvin)
        ob = bpy.data.objects.new(d.name, d)
        ob.location = loc
        ST.aim(ob, Vector(target))
        self.coll.objects.link(ob)
        self.lights.append(ob)
        return ob


def _support_dims(r, w, d, margin=0.12):
    """Support top at least w x d, and the product footprint plus a margin."""
    return max(w, r.size.x + 2 * margin), max(d, r.size.y + 2 * margin)


def workshop(r):
    wood = BM.textured("Env_BenchWood", "wood", "#7E6851", "#6A563F", 45.0, 0.55, 0.02)
    steel = BM.simple("Env_SteelFrame", "#2E3134", 0.45, 0.9)
    concrete = BM.textured("Env_Concrete", "concrete", "#8E8C88", "#6F6D69", 3.0, 0.85, 0.15)
    peg = BM.textured("Env_Pegboard", "pegboard", "#A89A86", "#2A241D", 25.0, 0.7, 0.2, vertical=True)
    w, d = _support_dims(r, 1.8, 0.75)
    top_y = r.c.y + d / 2 - r.size.y / 2 - 0.12  # product near the front edge
    r.box("BenchTop", (w, d, 0.045), (r.c.x, top_y, r.z0), wood, 0.003)
    floor_z = r.z0 - 0.9
    for sx in (-1, 1):
        for sy in (-1, 1):
            r.box(f"Leg{sx}{sy}", (0.05, 0.05, 0.9 - 0.045), (r.c.x + sx * (w / 2 - 0.06), top_y + sy * (d / 2 - 0.06), r.z0 - 0.045), steel)
    r.box("Floor", (12, 12, 0.02), (r.c.x, r.c.y, floor_z), concrete)
    wall_y = top_y + d / 2 + 0.01
    r.box("Pegboard", (w, 0.015, 0.9), (r.c.x, wall_y, r.z0 + 0.9), peg)
    r.box("Wall", (12, 0.1, 3.2), (r.c.x, wall_y + 0.06, floor_z + 3.2), BM.simple("Env_WallGrey", "#B8B5AE", 0.9))
    r.area("Overhead", 1.4, (r.c.x, top_y, r.z0 + 1.3), (r.c.x, top_y, r.z0), 3.0, 4600, size_y=0.25)
    r.area("Window", 2.0, (r.c.x - 2.2, r.c.y - 1.2, r.z0 + 0.9), r.c, 2.2, 5600, size_y=1.4)
    return {"world": ("#D5D3CF", 0.12), "support": "workbench"}


def laboratory(r):
    resin = BM.simple("Env_EpoxyResin", "#2B2D30", 0.28)
    cabinet = BM.simple("Env_LabCabinet", "#E9ECEE", 0.5)
    tiles = BM.textured("Env_WallTiles", "tiles", "#F2F4F5", "#C9CDD0", 8.0, 0.25, 0.05, vertical=True)
    floor = BM.textured("Env_LabFloor", "tiles", "#D8DCDE", "#AEB3B6", 2.0, 0.4, 0.02)
    glass = BM.build({"id": "env_glass", **U.lib("materials")["materials"]["glass_clear"]})
    shelf_m = BM.simple("Env_ShelfWhite", "#F4F4F4", 0.4)
    w, d = _support_dims(r, 2.0, 0.8)
    top_y = r.c.y + d / 2 - r.size.y / 2 - 0.15
    r.box("BenchTop", (w, d, 0.03), (r.c.x, top_y, r.z0), resin, 0.002)
    r.box("Cabinet", (w - 0.04, d - 0.06, 0.87), (r.c.x, top_y + 0.02, r.z0 - 0.03), cabinet, 0.002)
    floor_z = r.z0 - 0.9
    r.box("Floor", (12, 12, 0.02), (r.c.x, r.c.y, floor_z), floor)
    wall_y = top_y + d / 2 + 0.01
    r.box("Backsplash", (12, 0.05, 3.2), (r.c.x, wall_y + 0.02, floor_z + 3.2), tiles)
    sh_z = r.z0 + max(0.55, r.size.z + 0.2)
    r.box("Shelf", (w, 0.28, 0.025), (r.c.x, wall_y - 0.14, sh_z), shelf_m)
    for i, (dx, rad, h) in enumerate(((-0.6, 0.04, 0.18), (-0.45, 0.05, 0.22), (0.5, 0.035, 0.15), (0.62, 0.045, 0.2))):
        x = r.c.x + dx * w / 2
        r.cyl(f"Bottle{i}", rad, h, (x, wall_y - 0.14, sh_z), glass)
    r.area("Ceiling", 1.6, (r.c.x, top_y - 0.3, r.z0 + 1.5), (r.c.x, top_y, r.z0), 3.2, 6500, size_y=0.6)
    r.area("Fill", 1.5, (r.c.x + 1.8, r.c.y - 1.6, r.z0 + 0.6), r.c, 1.4, 6500, size_y=1.5)
    return {"world": ("#EEF3F7", 0.35), "support": "lab bench"}


def industrial(r):
    concrete = BM.textured("Env_FactoryFloor", "concrete", "#7E7C78", "#5C5A57", 1.5, 0.75, 0.2)
    steel = BM.simple("Env_StandSteel", "#3A3D40", 0.4, 0.9)
    plate = BM.textured("Env_TreadPlate", "brushed_metal", "#9EA2A5", "#7B7F82", 60.0, 0.35, 0.05, 0.9)
    wall = BM.textured("Env_CladWall", "ribs", "#5D6870", "#4B555C", 25.0, 0.6, 0.12)
    beam = BM.simple("Env_BeamYellow", "#C9A227", 0.5, 0.2)
    big = r.foot > 1.2
    floor_z = r.z0 if big else r.z0 - 0.85
    r.box("Floor", (30, 30, 0.02), (r.c.x, r.c.y, floor_z), concrete)
    if not big:
        w, d = _support_dims(r, 1.2, 0.8)
        r.box("StandTop", (w, d, 0.012), (r.c.x, r.c.y + 0.1, r.z0), plate)
        for sx in (-1, 1):
            for sy in (-1, 1):
                r.box(f"Leg{sx}{sy}", (0.06, 0.06, 0.85 - 0.012), (r.c.x + sx * (w / 2 - 0.05), r.c.y + 0.1 + sy * (d / 2 - 0.05), r.z0 - 0.012), steel)
    wy = r.c.y + max(3.0, r.size.y / 2 + 2.5)
    r.box("Wall", (30, 0.2, 8), (r.c.x, wy, floor_z + 8), wall)
    for i, dx in enumerate((-3.5, 3.5)):
        r.box(f"Column{i}", (0.3, 0.3, 8), (r.c.x + dx, wy - 0.3, floor_z + 8), beam)
    for i, dx in enumerate((-2.0, 0.0, 2.0)):
        r.area(f"HighBay{i}", 0.5, (r.c.x + dx, r.c.y, floor_z + 6), (r.c.x + dx, r.c.y, floor_z), 1.0, 4300, shape="DISK")
    r.area("KeyFill", 2.0, (r.c.x - 2.0, r.c.y - 2.0, r.z0 + 1.2), r.c, 2.5, 5000, size_y=1.5)
    return {"world": ("#8A9097", 0.2), "support": "floor" if big else "steel workstand"}


def office(r):
    oak = BM.textured("Env_DeskOak", "wood", "#B98F60", "#A07648", 40.0, 0.45, 0.02)
    plaster = BM.textured("Env_Plaster", "plaster", "#ECE8E1", "#DCD7CE", 6.0, 0.9, 0.05, vertical=True)
    floor = BM.textured("Env_OfficeFloor", "wood", "#7E6046", "#6A4E37", 30.0, 0.5, 0.02)
    dark = BM.simple("Env_MonitorBlack", "#121314", 0.25)
    ceramic = BM.simple("Env_MugWhite", "#F2F1ED", 0.15)
    w, d = _support_dims(r, 1.6, 0.8)
    top_y = r.c.y + d / 2 - r.size.y / 2 - 0.15
    r.box("Desk", (w, d, 0.03), (r.c.x, top_y, r.z0), oak, 0.004)
    for sx in (-1, 1):
        r.box(f"Leg{sx}", (0.04, d - 0.1, 0.72), (r.c.x + sx * (w / 2 - 0.05), top_y, r.z0 - 0.03), BM.simple("Env_DeskLeg", "#2B2C2E", 0.5, 0.8))
    floor_z = r.z0 - 0.75
    r.box("Floor", (12, 12, 0.02), (r.c.x, r.c.y, floor_z), floor)
    wall_y = top_y + d / 2 + 0.25
    r.box("Wall", (12, 0.1, 3.0), (r.c.x, wall_y + 0.05, floor_z + 3.0), plaster)
    mx = r.c.x - w / 2 + 0.3
    if mx + 0.3 < r.lo.x - 0.1:
        r.box("Monitor", (0.55, 0.03, 0.34), (mx, top_y + d / 2 - 0.12, r.z0 + 0.45), dark, 0.006)
        r.box("MonitorStand", (0.04, 0.04, 0.11), (mx, top_y + d / 2 - 0.1, r.z0 + 0.11), dark)
    ux = r.c.x + w / 2 - 0.25
    if ux - 0.05 > r.hi.x + 0.1:
        r.cyl("Mug", 0.042, 0.095, (ux, top_y - 0.05, r.z0), ceramic)
    r.area("Window", 2.4, (r.c.x - 2.5, r.c.y - 0.5, r.z0 + 0.8), r.c, 3.2, 6200, size_y=1.6)
    r.area("Ceiling", 1.2, (r.c.x + 0.4, r.c.y - 0.6, r.z0 + 1.6), r.c, 1.2, 4000, size_y=1.2)
    return {"world": ("#E9EEF2", 0.35), "support": "desk"}


def display(r):
    wall = BM.simple("Env_GalleryWall", "#2A2B2E", 0.85)
    plinth = BM.simple("Env_Plinth", "#F1F0EC", 0.6)
    floor = BM.textured("Env_GalleryFloor", "concrete", "#3A3A3C", "#2C2C2E", 2.0, 0.35, 0.05)
    side = max(0.45, r.foot + 0.15)
    h = 0.95
    r.box("Plinth", (side, side, h), (r.c.x, r.c.y, r.z0), plinth, 0.003)
    floor_z = r.z0 - h
    r.box("Floor", (12, 12, 0.02), (r.c.x, r.c.y, floor_z), floor)
    r.box("Wall", (12, 0.1, 4.0), (r.c.x, r.c.y + 1.8, floor_z + 4.0), wall)
    r.spot("Spot", (r.c.x + 0.3, r.c.y - 0.6, r.z0 + 1.8), r.c, 5.0, 4200, angle=28, blend=0.5, radius=0.06)
    r.area("Fill", 1.2, (r.c.x - 1.4, r.c.y - 1.2, r.z0 + 0.6), r.c, 0.8, 5200, size_y=1.2)
    r.area("WallWash", 2.5, (r.c.x, r.c.y + 1.0, floor_z + 3.6), (r.c.x, r.c.y + 1.8, floor_z + 1.0), 1.0, 3800, size_y=0.3)
    return {"world": ("#101012", 0.05), "support": "display plinth"}


def architectural(r):
    concrete = BM.textured("Env_PolishedConcrete", "concrete", "#B9B6B0", "#A29F99", 2.0, 0.22, 0.03)
    plaster = BM.textured("Env_WhitePlaster", "plaster", "#F3F1EC", "#E6E3DC", 5.0, 0.9, 0.04)
    stone = BM.textured("Env_Travertine", "concrete", "#D9CBB3", "#C2B194", 12.0, 0.5, 0.06)
    side = max(0.6, r.foot + 0.3)
    h = 0.45
    r.box("Plinth", (side * 1.6, side, h), (r.c.x, r.c.y + 0.05, r.z0), stone, 0.004)
    floor_z = r.z0 - h
    r.box("Floor", (20, 20, 0.02), (r.c.x, r.c.y, floor_z), concrete)
    wy = r.c.y + 2.2
    # back wall with a tall window opening (two wall pieces and a lintel)
    r.box("WallL", (4.0, 0.2, 4.0), (r.c.x - 3.2, wy, floor_z + 4.0), plaster)
    r.box("WallR", (4.0, 0.2, 4.0), (r.c.x + 3.2, wy, floor_z + 4.0), plaster)
    r.box("Lintel", (2.4, 0.2, 0.8), (r.c.x, wy, floor_z + 4.0), plaster)
    r.box("WallSide", (0.2, 8.0, 4.0), (r.c.x - 3.0, r.c.y - 1.0, floor_z + 4.0), plaster)
    r.area("Daylight", 2.4, (r.c.x, wy + 0.5, floor_z + 1.6), (r.c.x, r.c.y, r.z0), 2.5, 6500, size_y=3.2)
    sun = bpy.data.lights.new("Arch_Sun", "SUN")
    sun.energy, sun.angle, sun.color = 1.8, math.radians(2.0), U.kelvin_rgb(5600)
    so = bpy.data.objects.new("Arch_Sun", sun)
    so.rotation_euler = (math.radians(55), 0, math.radians(160))
    r.coll.objects.link(so)
    r.lights.append(so)
    r.area("Bounce", 2.0, (r.c.x + 1.5, r.c.y - 2.0, r.z0 + 0.8), r.c, 1.0, 5800, size_y=2.0)
    return {"world": ("#DDE6EE", 0.4), "support": "stone plinth"}


PRESETS = {"workshop": workshop, "laboratory": laboratory, "industrial": industrial,
           "office": office, "display": display, "architectural": architectural}


def build(scene, box, settings, coll):
    env = settings.get("environment", {})
    name = env.get("preset", "workshop")
    r = Room(box, coll, f"Env_{name}")
    info = PRESETS[name](r)
    inten = env.get("intensity", 1.0)
    for L in r.lights:
        L.data.energy *= inten
    wc, ws = info["world"]
    scene.world = ST.world(f"World_Env_{name}", wc, ws * inten)
    scene.render.film_transparent = False
    # clearance check: no prop may enter the product box (+2 mm); supports may only touch it
    clash = []
    lo, hi = box[0] - Vector((0.002,) * 3), box[1] + Vector((0.002,) * 3)
    for p in r.props:
        # matrix_basis, not matrix_world: this scene has not been evaluated yet
        pts = [p.matrix_basis @ Vector(v.co) for v in p.data.vertices]
        plo = Vector([min(q[i] for q in pts) for i in range(3)])
        phi = Vector([max(q[i] for q in pts) for i in range(3)])
        overlap = all(plo[i] < hi[i] and phi[i] > lo[i] for i in range(3))
        if overlap and phi.z > box[0].z + 1e-5:
            clash.append(p.name)
    return {"environment": name, "support": info["support"], "props": [p.name for p in r.props],
            "lights": [L.name for L in r.lights], "prop_clashes": clash}
