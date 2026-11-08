"""Write every grindmn S part project that the generator owns (params, spec, model.py, requirements) and
both assemblies (grindmn, grindmn_exploded).

grindmn S (2026-11-08): 13 parts, 7 machined and 6 bought; see ../requirements.md. Driving values live here;
rerun after any change:
    python3 projects/grindmn/gen_projects.py
The inner burr and the 608 bearing keep their hand-written projects.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import grindmn_parts as gp  # noqa: E402

# name: (part number and material, one-line description, params)
PARTS = {
    "tube": ("Part 1, 6061-T6, diamond knurl z 22 to 97, clear anodise", "Body: spider seat, outer burr seat, hopper and bridge seat bored from the bottom in one chucking; Ø61 spigot and O-ring groove for the flush cup.", {
        "length": 99.0, "od": 64.0, "hopper_d": 50.0, "burr_seat_d": 54.0, "z_burr_shoulder": 30.0,
        "spider_seat_d": 56.0, "z_spider_top": 10.0, "spigot": {"d": 61.0, "h": 20.0},
        "oring_groove": {"z0": 12.0, "w": 2.7, "floor_d": 57.9}}),
    "bridge": ("Part 2, 6061-T6, clear anodise, bearing seat masked", "Top bearing carrier: Ø50 g6 pilot in the tube's bridge seat, Ø64 flange on the tube's top face, 626 seat bored from the top, three spokes with 10 mm bean openings. Lifts out with the shaft for cleaning.", {
        "t": 12.0, "pilot_h": 8.0, "pilot_od": 50.0, "flange_od": 64.0, "ring_id": 46.0, "hub_d": 26.0,
        "lip_hole_d": 15.0, "spoke_w": 4.0, "spoke_angles": [60, 180, 300], "seat_d": 19.0, "seat_depth": 6.0}),
    "spider": ("Part 3, 6061-T6, clear anodise, bearing seat masked", "Lower bearing carrier, pressed into the tube from below against the outer burr: Ø56/52 ring, three 4 mm spokes, hub with the 608 seat bored from the bottom, two tabs into the outer burr's notches.", {
        "hub_d": 30.0, "hub_h": 10.0, "lip_hole_d": 14.0, "ring_od": 56.0, "ring_id": 52.0, "ring_z0": 5.0,
        "ring_h": 10.0, "spoke_w": 4.0, "spoke_z": [5.0, 10.0], "spoke_angles": [0, 120, 240], "seat_d": 22.0,
        "seat_depth": 7.0, "tabs": {"r0": 26.0, "r1": 26.9, "w": 4.0, "h": 2.0, "angles": [90, 270]}}),
    "shaft": ("Part 4, 416 stainless, bearing seats ground", "Stepped shaft hung from the nut: Ø8 lower seat and burr drive flats (the burr rests where they start), Ø6 above with the top seat, M6 x 0.75 thread (modelled at Ø6) and the crank flat.", {
        "_kind": "stepped_shaft", "d_low": 8.0, "d_high": 6.0, "length": 134.0, "z_step": 46.0, "flats_z0": 16.0,
        "burr_flats": 6.5, "crank_flat": 5.2, "crank_flat_z": 121.0}),
    "nut": ("Part 5, 6061-T6, diamond knurl, clear anodise, thread masked", "Grind nut: M6 x 0.75 with a nylon patch, Ø9 boss on the top bearing's inner ring, 45-line stepless scale on the top chamfer (16.7 µm a line).", {
        "_kind": "nut_s", "d": 28.0, "h": 10.0, "boss_d": 9.0, "boss_h": 3.0, "tap_d": 5.25}),
    "crank_arm": ("Part 6, 6061-T6, clear anodise", "One-piece crank: 8 mm plate on a Ø16 boss, blind D bore resting on the shaft's end (slip fit, nothing holds it), index line on the boss, M6 for the handle at r 85.", {
        "_kind": "crank_s", "t": 8.0, "boss_d": 16.0, "boss_h": 6.0, "w_hub": 16.0, "w_knob": 12.0, "knob_x": 85.0,
        "bore_d": 6.0, "bore_depth": 13.0, "flat": 5.2, "tap_d": 5.0}),
    "catch_cup": ("Part 7, 6061-T6, smooth, bead blast, clear anodise", "Catch cup, flush Ø64: slides over the tube's Ø61 spigot onto the O-ring and stops on the tube's bottom face; about 119 ml.", {
        "od": 64.0, "h": 69.0, "sleeve_d": 61.2, "sleeve_depth": 20.0, "chamber_d": 58.0, "base": 4.0,
        "corner_r": 2.0}),
    "outer_burr": ("Bought: 48 mm conical burr set, outer ring (assumed sizes)", "Outer burr with two notches in its lower face for the spider's tabs (assumed: check on the bought set).", {
        "od": 54.0, "h": 20.0, "flange_h": 6.0, "flats": 50.0, "bore_top": 45.0, "bore_low": 49.0, "bore_step_z": 10.0,
        "teeth": 20, "tooth_r": 24.5, "tooth_hw": 2.0, "notches": {"r0": 25.6, "w": 4.4, "h": 2.3, "angles": [90, 270]}}),
    "bearing_626": ("Bought: 626-2RS, 6 x 19 x 6", "Top bearing, one body (rings joined by recessed shields).", {
        "_kind": "bearing", "d": 6.0, "D": 19.0, "B": 6.0, "ring_od_in": 9.5, "ring_id_out": 15.5, "recess": 0.3}),
    "oring_58x2": ("Bought: O-ring 58 x 2, NBR 70 or FKM, food grade", "Holds the catch cup; modelled as installed in the groove.", {
        "_kind": "oring", "centre_d": 59.9, "cs": 2.0}),
    "handle": ("Bought: revolving handle, M6 stud, aluminium (model unverified)", "Envelope: M6 x 8 stud and a Ø20 x 30 grip.", {
        "_kind": "handle", "stud_d": 6.0, "stud_l": 8.0, "grip_d": 20.0, "grip_l": 30.0}),
}

# Tube z at grind 0 (z = 0 at the tube's bottom face). Toward grind 119 the shaft, inner burr, crank and
# handle move down by up to 1.98 mm; everything else stays.
ASSEMBLY = [
    ("grindmn_tube", {"at": [0, 0, 0]}),
    ("grindmn_spider", {"at": [0, 0, -5]}),
    ("grindmn_bearing_608", {"at": [0, 0, -5], "label": "bearing_lower"}),
    ("grindmn_shaft", {"at": [0, 0, -5]}),
    ("grindmn_outer_burr", {"at": [0, 0, 10]}),
    ("grindmn_inner_burr", {"at": [0, 0, 11]}),
    ("grindmn_bridge", {"at": [0, 0, 91]}),
    ("grindmn_bearing_626", {"at": [0, 0, 97], "label": "bearing_top"}),
    ("grindmn_nut", {"at": [0, 0, 103]}),
    ("grindmn_crank_arm", {"at": [0, 0, 116]}),
    ("grindmn_handle", {"at": [85, 0, 122]}),
    ("grindmn_catch_cup", {"at": [0, 0, -49]}),
    ("grindmn_oring_58x2", {"at": [0, 0, 12.35]}),
]
MOVING = {"grindmn_shaft", "grindmn_inner_burr", "grindmn_crank_arm", "grindmn_handle"}

ALLOWED = [  # nominal threads in tap-drill holes and the O-ring squeeze
    ["grindmn_catch_cup", "grindmn_oring_58x2"], ["grindmn_nut", "grindmn_shaft"],
    ["grindmn_crank_arm", "grindmn_handle"],
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
        "_comment": "grindmn S (2026-11-08) at grind 0, tube z from section 6 of projects/grindmn/requirements.md. "
                    "Axis on the origin; the crank points along +x; spider tabs and burr notches at 90/270 deg. "
                    "Written by projects/grindmn/gen_projects.py.",
        "components": components(),
        "expected": {
            "_comment": "x: tube and cup -32 .. handle grip 85 + 10 = 95; y: tube and cup +-32; z: cup base -49 .. "
                        "grip top 122 + 8 + 30 = 160. Allowed interference: nominal threads in tap-drill holes "
                        "(nut on the shaft, handle stud in the arm) and the O-ring squeeze.",
            "bbox": [127.0, 64.0, 209.0],
            "allowed_interference": ALLOWED,
        },
    }
    (ROOT / "assemblies" / "grindmn" / "assembly.json").write_text(json.dumps(asm, indent=1) + "\n")

    # Exploded: housing and crank on the axis bottom to top with 12 mm gaps; the shaft and inner burr at
    # x = -110; the handle above the arm's handle end.
    gap = 12.0

    def h(part):
        return part_bbox(part)["bbox.z"]["expected"]
    axis = ["grindmn_catch_cup", "grindmn_oring_58x2", "grindmn_spider", "grindmn_bearing_608",
            "grindmn_outer_burr", "grindmn_tube", "grindmn_bridge", "grindmn_bearing_626", "grindmn_nut",
            "grindmn_crank_arm"]
    comps, z = [], 0.0
    for part in axis:
        comps.append({"part": part, "at": [0, 0, round(z, 3)]})
        z += h(part) + gap
    top = z
    zk = top
    comps.append({"part": "grindmn_handle", "at": [85.0, 0, round(zk, 3)]})
    zk += h("grindmn_handle") + gap
    zs = 0.0
    for part in ["grindmn_shaft", "grindmn_inner_burr"]:
        comps.append({"part": part, "at": [-110.0, 0, round(zs, 3)]})
        zs += h(part) + gap
    # x: inner burr at -110 (r 23.8) .. handle grip at 85 (r 10); y: tube, cup and bridge +-32;
    # z: the tallest stack, less its last gap
    bbox = [round(85 + 10 + 110 + 23.8, 3), 64.0, round(max(top, zk, zs) - gap, 3)]
    exp = {
        "_comment": "Exploded view of grindmn S: housing and crank on the axis (x = 0), bottom to top in fitting "
                    "order with 12 mm gaps; the shaft and inner burr at x = -110; the handle above the arm's handle "
                    "end (x = 85). Written by projects/grindmn/gen_projects.py.",
        "components": comps,
        "expected": {"bbox": bbox, "bbox_tol": 0.2, "views": ["isometric", "front"], "allowed_interference": []},
    }
    (ROOT / "assemblies" / "grindmn_exploded" / "assembly.json").write_text(json.dumps(exp, indent=1) + "\n")


def main():
    for name, (what, desc, p) in PARTS.items():
        write_part(name, what, desc, p)
        vol, bbox = gp.expected(name, p)
        print(f"grindmn_{name:14} volume {vol:>12} bbox {bbox}")
    write_assemblies()


if __name__ == "__main__":
    main()
