"""Write the grindmn part projects changed by the top-adjust redesign (params, spec, model.py,
requirements) and both assemblies (grindmn, grindmn_exploded).

Driving values live here, taken from ../requirements.md (top-adjust, 2026-11-08); rerun after any change:
    python3 projects/grindmn/gen_projects.py
Parts not listed in PARTS keep their hand-written projects (burrs, bearings, hardware, crank arm, knob, ...).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import grindmn_parts as gp  # noqa: E402

DOWEL = {"r": 28.5, "d": 3.0}

# name: (part number and material, one-line description, params)
PARTS = {
    "tube": ("Part 1, 6061-T6, diamond knurl above the cup, clear anodise", "Body: spider seat, outer burr seat and hopper bored from the bottom in one chucking; O-ring groove for the cup; two M4 burr screws; dowel hole in the top face for the bridge.", {
        "length": 99.0, "od": 64.0, "hopper_d": 50.0, "burr_seat_d": 54.0, "z_burr_shoulder": 30.0,
        "spider_seat_d": 56.0, "z_spider_top": 10.0, "oring_groove": {"z0": 12.0, "w": 2.7, "floor_d": 60.9},
        "z_burr_screws": 25.0, "dowel": {**DOWEL, "depth": 6.0}}),
    "bridge": ("Part 2, 6061-T6, clear anodise, bearing seat masked", "Top bearing carrier: pilot in the hopper bore, flange on the tube's top face, 608 seat bored from the top, three spokes with 9 mm bean openings, dowel hole against rotation.", {
        "t": 12.0, "pilot_h": 8.0, "pilot_od": 50.0, "flange_od": 64.0, "ring_id": 46.0, "hub_d": 28.0,
        "lip_hole_d": 18.5, "spoke_w": 4.0, "spoke_angles": [60, 180, 300], "seat_d": 22.0, "seat_depth": 7.0,
        "dowel": {**DOWEL, "d": 3.1}}),
    "spider": ("Part 3, 6061-T6, clear anodise, bearing seat masked", "Lower bearing carrier, pressed into the tube from below against the outer burr: Ø56/52 ring, three 4 mm spokes, hub with the 608 seat bored from the bottom; open over the burr exit.", {
        "hub_d": 30.0, "hub_h": 10.0, "lip_hole_d": 14.0, "ring_od": 56.0, "ring_id": 52.0, "ring_z0": 5.0,
        "ring_h": 10.0, "spoke_w": 4.0, "spoke_z": [5.0, 10.0], "spoke_angles": [0, 120, 240], "seat_d": 22.0,
        "seat_depth": 7.0}),
    "click_disc": ("Part 11, 303 stainless", "Click disc keyed to the shaft's flat: boss on the top bearing's inner ring, 45 radial click grooves for the nut's plunger.", {
        "d": 30.0, "t": 5.0, "boss_d": 11.5, "boss_h": 2.0, "bore_d": 8.0, "flat": 7.2, "clicks": 45,
        "groove_r_in": 9.0, "groove_w": 1.0, "groove_depth": 0.84}),
    "adjuster_nut": ("Part 12, 6061-T6, diamond knurl, clear anodise, thread masked", "Grind dial: M8 x 0.75 nut on the shaft's top thread, 0-44 scale etched on the top chamfer, push-fit ball plunger at r 12 clicking into the disc.", {
        "d": 30.0, "h": 10.0, "tap_d": 7.25, "plunger_r": 12.0, "plunger_d": 4.0}),
    "shaft": ("Part 4, 416 stainless, ground at the bearing seats", "Shaft hung from the adjuster nut: lower seat, collar, burr drive flats, two e-clip grooves, top seat, M8 x 0.75 thread (modelled at Ø8), flat from the click disc to the top end.", {
        "d": 8.0, "length": 138.0, "collar_d": 10.0, "collar_z": [13.0, 16.0], "groove_d": 6.0, "groove_w": 0.74,
        "clip_grooves_z": [46.2, 82.0], "burr_drive_z": [16.0, 46.0], "burr_flats": 6.5, "crank_flat": 7.2,
        "crank_flat_z": 110.0}),
    "lid": ("Part 8, 6061-T6, clear anodise", "Lid ring on the bridge flange, lifts off over the Ø30 adjuster nut.", {
        "od": 64.0, "t": 3.0, "hole_d": 32.0, "spigot_h": 0, "spigot_d": 0}),
    "catch_cup": ("Part 9, 6061-T6, smooth, bead blast, clear anodise", "Catch cup: slides over the tube's bottom onto the O-ring and stops on the tube's bottom face; about 125 ml chamber.", {
        "od": 68.0, "h": 69.0, "sleeve_d": 64.2, "sleeve_depth": 20.0, "chamber_d": 60.0, "base": 4.0,
        "corner_r": 2.0}),
    "spring": ("Part 13, stainless 302/304, bought", "Compression spring at its grind-0 installed length (about 31 N; 25 N at the coarsest setting).", {
        "od": 12.0, "wire": 1.2, "coils": 6, "length": 14.7}),
    "ball_plunger": ("Part 21, stainless, bought (Ø4 push-fit, Ø2 ball; part number unverified)", "Push-fit ball plunger in the adjuster nut, ball down.", {
        "sleeve_d": 4.0, "sleeve_l": 4.0, "nose_d": 2.0, "nose_h": 1.0, "nose_round": 0.6}),
    "screw_m3x10": ("ISO 4762 M3 x 10, A2, bought", "Socket head screw, arm to hub (2 used).", {
        "_kind": "screw", "d": 3.0, "length": 10.0, "head_d": 5.5, "head_h": 3.0, "socket": 2.5, "socket_depth": 1.6}),
    "dowel_3x8": ("ISO 8734 3 x 8, A1 stainless, bought", "Dowel pin, pressed into the tube's top face; keeps the bridge from turning.", {
        "_kind": "magnet", "d": 3.0, "h": 8.0}),
}

# Tube z at grind 0 (z = 0 at the tube's bottom face). Every part on the shaft side moves down by up to
# 1.98 mm toward grind 119; the tube, spider, bridge, burrs' outer ring, lid and the nut's seat do not.
CRANK = -8.0  # crank stack moved down 8 mm from the bottom-adjust layout
ASSEMBLY = [
    ("grindmn_tube", {"at": [0, 0, 0]}),
    ("grindmn_spider", {"at": [0, 0, -5]}),
    ("grindmn_bearing_608", {"at": [0, 0, -5], "label": "bearing_lower"}),
    ("grindmn_shaft", {"at": [0, 0, -5]}),
    ("grindmn_outer_burr", {"at": [0, 0, 10]}),
    ("grindmn_inner_burr", {"at": [0, 0, 11]}),
    ("grindmn_eclip_6", {"at": [0, 0, 41.2], "label": "eclip_burr"}),
    ("grindmn_eclip_6", {"at": [0, 0, 77.0], "label": "eclip_spring"}),
    ("grindmn_washer_8", {"at": [0, 0, 77.7]}),
    ("grindmn_spring", {"at": [0, 0, 79.3]}),
    ("grindmn_spacer", {"at": [0, 0, 94]}),
    ("grindmn_bridge", {"at": [0, 0, 91]}),
    ("grindmn_bearing_608", {"at": [0, 0, 96], "label": "bearing_top"}),
    ("grindmn_dowel_3x8", {"at": [28.5, 0, 95]}),
    ("grindmn_lid", {"at": [0, 0, 103]}),
    ("grindmn_click_disc", {"at": [0, 0, 103]}),
    ("grindmn_ball_plunger", {"at": [12, 0, 107], "label": "plunger"}),
    ("grindmn_adjuster_nut", {"at": [0, 0, 108]}),
    ("grindmn_crank_hub", {"at": [0, 0, 121]}),
    ("grindmn_magnet_6x3", {"at": [0, 0, 133]}),
    ("grindmn_crank_arm", {"at": [0, 0, 145 + CRANK]}),
    ("grindmn_screw_m3x10", {"at": [-6, 0, 133], "label": "arm_screw_1"}),
    ("grindmn_screw_m3x10", {"at": [6, 0, 133], "label": "arm_screw_2"}),
    ("grindmn_bearing_mf105", {"at": [85, 0, 151 + CRANK], "label": "knob_bearing_low"}),
    ("grindmn_crank_knob", {"at": [85, 0, 151.8 + CRANK]}),
    ("grindmn_bearing_mf105", {"label": "knob_bearing_high", "xform": [1, 0, 0, 0, -1, 0, 0, 0, -1, 85, 0, 181.0 + CRANK]}),
    ("grindmn_shoulder_5x30", {"at": [85, 0, 144.5 + CRANK]}),
    ("grindmn_catch_cup", {"at": [0, 0, -49]}),
    ("grindmn_oring_60x2", {"at": [0, 0, 12.35]}),
    ("grindmn_screw_m4x6", {"label": "burr_screw_90", "xform": [-1.0, 0.0, 0, 0, 0, 1, 0.0, 1.0, 0, 0.0, 26.0, 25]}),
    ("grindmn_screw_m4x6", {"label": "burr_screw_270", "xform": [1.0, -0.0, 0, 0, 0, 1, -0.0, -1.0, 0, -0.0, -26.0, 25]}),
]

ALLOWED = [  # nominal threads in tap-drill holes, the O-ring squeeze, the plunger ball in a click groove
    ["grindmn_catch_cup", "grindmn_oring_60x2"], ["grindmn_screw_m4x6", "grindmn_tube"],
    ["grindmn_crank_arm", "grindmn_shoulder_5x30"], ["grindmn_crank_hub", "grindmn_screw_m3x10"],
    ["grindmn_adjuster_nut", "grindmn_shaft"], ["grindmn_ball_plunger", "grindmn_click_disc"],
]


def spec_for(name, p):
    vol, bbox = gp.expected(name, p)
    return {
        "_comment": "Expected values worked out by hand in projects/grindmn/grindmn_parts.py (closed forms and 1-D integrals), from requirements.md.",
        "solid_bodies": {"expected": 1},
        **{f"bbox.{a}": {"expected": b, "tol": 0.05} for a, b in zip("xyz", bbox)},
        "volume": {"expected": vol, "rel_tol": 0.001},
        "export.step": {"rel_tol": 0.001}, "export.stl": {"rel_tol": 0.01},
    }, vol, bbox


MODEL = '''"""grindmn {name}: geometry lives in projects/grindmn/grindmn_parts.py (shared by all grindmn parts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "grindmn"))
import grindmn_parts  # noqa: E402


def build(app, params):
    return grindmn_parts.build(app, "{name}", params)
'''


def write_part(name, what, desc, p):
    folder = ROOT / "projects" / f"grindmn_{name}"
    for sub in ("design", "parameters", "validation"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    spec, vol, bbox = spec_for(name, p)
    (folder / "parameters" / "params.json").write_text(json.dumps(p, indent=2) + "\n")
    (folder / "validation" / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    (folder / "design" / "model.py").write_text(MODEL.format(name=name))
    (folder / "requirements.md").write_text(
        f"# grindmn {name.replace('_', ' ')}: {what}\n\n{desc}\n\n"
        "Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend "
        "on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by "
        "`projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. "
        "z = 0 at the part's own bottom face, z up, axis on the origin.\n\n"
        f"Expected: volume {vol} mm³, bounding box {bbox[0]} × {bbox[1]} × {bbox[2]} mm.\n\n"
        "Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, "
        "etching; click grooves are modelled square.\n")


def components():
    out = []
    for part, place in ASSEMBLY:
        out.append({"part": part, **place})
    return out


def part_bbox(part):
    return json.loads((ROOT / "projects" / part / "validation" / "spec.json").read_text())


def write_assemblies():
    asm = {
        "_comment": "grindmn hand grinder, top-adjust (2026-11-08), at grind 0, tube z from section 6 of "
                    "projects/grindmn/requirements.md. Axis on the origin; the crank arm points along +x; outer burr "
                    "flats and their M4 screws at 90/270 deg, bridge dowel at 0 deg, plunger at r 12 on +x. "
                    "Written by projects/grindmn/gen_projects.py.",
        "components": components(),
        "expected": {
            "_comment": "x: cup -34 .. knob 85 + 10 = 95; y: burr-screw heads at 90/270 reach 32 + 2.2 = 34.2 each "
                        "side; z: cup base -49 .. shoulder screw head 136.5 + 40 = 176.5. Allowed interference: "
                        "nominal threads in tap-drill holes, the O-ring squeeze, the plunger ball in a click groove.",
            "bbox": [129.0, 68.4, 225.5],
            "allowed_interference": ALLOWED,
        },
    }
    d = ROOT / "assemblies" / "grindmn"
    (d / "assembly.json").write_text(json.dumps(asm, indent=1) + "\n")

    # Exploded: housing and crank on the axis bottom to top with 12 mm gaps; the shaft group beside it at
    # x = -110; the knob stack above the arm's knob end; radial parts pulled 20 mm out.
    gap = 12.0
    def h(part):
        return part_bbox(part)["bbox.z"]["expected"]
    axis = ["grindmn_catch_cup", "grindmn_oring_60x2", "grindmn_spider", "grindmn_bearing_608",
            "grindmn_outer_burr", "grindmn_tube", "grindmn_dowel_3x8", "grindmn_bridge", "grindmn_bearing_608",
            "grindmn_lid", "grindmn_click_disc", "grindmn_ball_plunger", "grindmn_adjuster_nut",
            "grindmn_crank_hub", "grindmn_magnet_6x3", "grindmn_crank_arm", "grindmn_screw_m3x10",
            "grindmn_screw_m3x10"]
    shaft = ["grindmn_shaft", "grindmn_inner_burr", "grindmn_eclip_6", "grindmn_eclip_6", "grindmn_washer_8",
             "grindmn_spring", "grindmn_spacer"]
    comps, z = [], 0.0
    for part in axis:
        x = {"grindmn_dowel_3x8": 28.5, "grindmn_ball_plunger": 12.0}.get(part, 0.0)
        if part == "grindmn_screw_m3x10":
            x = -6.0 if sum(c["part"] == part for c in comps) == 0 else 6.0
            if x > 0:
                z -= h(part) + gap  # both arm screws side by side
        comps.append({"part": part, "at": [x, 0, round(z, 3)]})
        z += h(part) + gap
    top = z
    z = 0.0
    for part in shaft:
        comps.append({"part": part, "at": [-110.0, 0, round(z, 3)]})
        z += h(part) + gap
    zk = next(c["at"][2] for c in comps if c["part"] == "grindmn_crank_arm") + h("grindmn_crank_arm") + gap
    for part in ["grindmn_bearing_mf105", "grindmn_crank_knob", "grindmn_bearing_mf105", "grindmn_shoulder_5x30"]:
        comps.append({"part": part, "at": [85.0, 0, round(zk, 3)]})
        zk += h(part) + gap
    zt = next(c["at"][2] for c in comps if c["part"] == "grindmn_tube")
    comps.append({"part": "grindmn_screw_m4x6", "label": "burr_screw_90",
                  "xform": [-1.0, 0.0, 0, 0, 0, 1, 0.0, 1.0, 0, 0.0, 46.0, zt + 25]})
    comps.append({"part": "grindmn_screw_m4x6", "label": "burr_screw_270",
                  "xform": [1.0, -0.0, 0, 0, 0, 1, -0.0, -1.0, 0, -0.0, -46.0, zt + 25]})
    # x: inner burr at -110 (r 23.8) .. knob at 85 (r 10); y: burr screws pulled out to 46 plus their length;
    # z: the taller of the axis stack and the knob stack, less the last gap
    ys = 46.0 + h("grindmn_screw_m4x6")
    bbox = [round(85 + 10 + 110 + 23.8, 3), round(2 * ys, 3), round(max(top, zk) - gap, 3)]
    exp = {
        "_comment": "Exploded view of the top-adjust grindmn: housing and crank on the axis (x = 0), bottom to top "
                    "in fitting order with 12 mm gaps; the shaft group at x = -110; the knob stack above the arm's "
                    "knob end (x = 85); the burr screws pulled 20 mm out. Written by projects/grindmn/gen_projects.py.",
        "components": comps,
        "expected": {"bbox": bbox, "bbox_tol": 0.2, "views": ["isometric", "front"], "allowed_interference": []},
    }
    (ROOT / "assemblies" / "grindmn_exploded" / "assembly.json").write_text(json.dumps(exp, indent=1) + "\n")
    return top


def main():
    for name, (what, desc, p) in PARTS.items():
        write_part(name, what, desc, p)
        vol, bbox = gp.expected(name, p)
        print(f"grindmn_{name:14} volume {vol:>12} bbox {bbox}")
    write_assemblies()


if __name__ == "__main__":
    main()
