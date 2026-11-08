"""Write every airmn part project (params, spec, model.py, requirements) and both assemblies.

All driving values live here, taken from ../requirements.md; rerun after any change:
    .venv\\Scripts\\python projects\\airmn\\gen_projects.py
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import airmn_parts as ap  # noqa: E402

PLEAT = {"pleats": 120, "pleat_ro": 200.0, "pleat_ri": 150.0, "fold_flat": 2.0}
D = 430.0
SCREWS = {"screw_r": 208.0, "screw_angles": [18, 90, 162, 234, 306]}
HEX = {"hole_d": 10.0, "hole_pitch": 11.2}

PARTS = {
    "base": ("PETG, printed in sectors", "Bottom of the unit: 430 x 20 plate with 4 printed feet, comb groove on top, 5 M3 screws up into the frame flange (counterbored underneath), USB-C PD board pocket and cable channel.", {
        "d": D, "t": 20.0, "foot_h": 5.0, "foot_d": 20.0, "foot_r": 170.0, "foot_angles": [45, 135, 225, 315],
        "groove_od": 408.0, "groove_id": 288.0, "groove_depth": 4.0, **SCREWS, "screw_hole": 3.4,
        "cbore_d": 6.5, "cbore_depth": 3.5,
        "pd_pocket": {"x": 145.0, "l": 40.0, "w": 30.0, "h": 8.0}, "cable_channel": {"x0": 160.0, "w": 12.0}}),
    "frame": ("PETG, printed in sectors", "Perforated frame round the filter, flush with the fan head: 430 / 422 x 453, the top grid's 10 mm holes on an 11.2 hex pitch round the wall (120 column pairs x 43 rows), solid end bands, inner flange 422 / 410 x 8 at the bottom tapped M3 for the base screws.", {
        "od": D, "id": 422.0, "h": 453.0, "hole_d": 10.0, "units": 120, "rows": 43,
        "row_pitch": round(11.2 * 3 ** 0.5 / 2, 5), "row_z0": 22.8, "flange_id": 410.0, "flange_h": 8.0, **SCREWS,
        "perforated": False}),  # smooth for visualisation for now (owner); True cuts the 5160-hole grid
    "comb": ("TPU 95A (comb and gasket in one)", "Pleat comb and gasket in one, used top and bottom: ring 406 / 292 x 10 with the zigzag slot holding all 120 pleat folds, two sealing beads 1.5 x 1 on the outer face (404 / 401 and 297 / 294).", {
        "od": 406.0, "id": 292.0, "t": 10.0, "slot_w": 1.6, "slot_depth": 7.0, "bead_h": 1.0,
        "beads": [[404.0, 401.0], [297.0, 294.0]], **PLEAT}),
    "pleat_pack": ("MERV 13 synthetic roll media", "Pleated filter wall: 120 pleats 50 deep, 0.8 media, 450 tall (seam overlap not modelled).", {
        "h": 450.0, "media_t": 0.8, **PLEAT}),
    "fan_head": ("PETG, printed in sectors", "Everything that lifts off as one, 179 tall: motor cup 100 / 90 (open bottom, 5 mm motor plate on top with the motor's 2 x M3) hanging into the filter core on 11 flat radial struts 3 x 40 (the flow straightener, trailing edges 50 below the rotor), spigot 421.6 / 412 into the frame, inlet flange (opening 286) on the frame rim and the top comb's beads, 404 duct round the rotor, no outlet vanes, 8 mm top with 10 mm holes on an 11.2 hex pitch (72 % open) 40 above the rotor.", {
        "d": D, "spigot_z": 26.0, "spigot_h": 5.0, "spigot_od": 421.6, "spigot_id": 412.0, "flange_t": 10.0,
        "inlet_d": 286.0, "bore": 404.0, "top_z": 179.0, "top_t": 8.0, **HEX, "grid_r": 198.0,
        "cup_d": 100.0, "cup_id": 90.0, "cup_h": 90.0, "plate_t": 5.0,
        "struts": 11, "strut_t": 3.0, "strut_z": 1.0, "shaft_hole": 6.0, "motor_screw_pitch": 17.0,
        "motor_screw_hole": 3.4, "cbore_d": 6.0, "cbore_depth": 2.5}),
    "rotor": ("PETG", "Axial rotor in one part: hub 100 x 40 straight on the motor's 4 mm D shaft (shaft from below; M3 clamp screw 3 above the bottom), 7 flat PLACEHOLDER blades to R200.5 (1.5 mm tip gap), no pitch yet.", {
        "hub_d": 100.0, "h": 40.0, "bore": 4.0, "clamp_from_top": 37.0, "blades": 7, "blade_t": 3.0, "tip_r": 200.5}),
    "motor": ("Bought: E-S Motor 25 mm gearhead brushless 24 V 600 rpm", "Envelope stand-in: body and 4 mm D shaft (estimated).", {
        "d": 25.0, "body_l": 75.0, "shaft_d": 4.0, "shaft_l": 12.0, "flat": 1.5, "flat_l": 10.0}),
    "pd_board": ("Bought: Adafruit HUSB238 #5807", "Envelope stand-in: PCB and USB-C socket (estimated).", {
        "l": 25.4, "w": 17.8, "t": 1.6, "usbc": {"l": 9.0, "w": 7.5, "h": 3.2, "overhang": 1.6}}),
}

MODEL = '''"""airmn {part}: geometry lives in projects/airmn/airmn_parts.py (shared by all airmn parts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "airmn"))
import airmn_parts  # noqa: E402


def build(app, params):
    return airmn_parts.build(app, "{part}", params)
'''


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def gen_parts():
    boxes = {}
    for part, (mat, desc, p) in PARTS.items():
        name = f"airmn_{part}"
        d = ROOT / "projects" / name
        vol, bbox = ap.expected(part, p)
        boxes[name] = bbox
        write(d / "parameters" / "params.json", json.dumps(p, indent=2) + "\n")
        write(d / "design" / "model.py", MODEL.format(part=part))
        spec = {"_comment": "Expected values worked out by hand in projects/airmn/airmn_parts.py from projects/airmn/requirements.md.",
                "solid_bodies": {"expected": 1},
                **{f"bbox.{a}": {"expected": v, "tol": 0.05} for a, v in zip("xyz", bbox)},
                "volume": {"expected": vol, "rel_tol": 0.001},
                "export.step": {"rel_tol": 0.001}, "export.stl": {"rel_tol": 0.01}}
        write(d / "validation" / "spec.json", json.dumps(spec, indent=2) + "\n")
        write(d / "requirements.md", f"# {name}\n\n{desc}\n\n- Material: {mat}\n"
              f"- Expected volume {vol} mm3, bbox {bbox[0]} x {bbox[1]} x {bbox[2]} mm (from `airmn_parts.py`).\n"
              f"- All sizes: `parameters/params.json`; sources and assumptions: [../airmn/requirements.md](../airmn/requirements.md).\n")
        print(f"{name:22s} vol {vol:14.3f}  bbox {bbox}")
    return boxes


# ---------------------------------------------------------------------------- assemblies
FLIP = [1, 0, 0, 0, -1, 0, 0, 0, -1]


def comp(part, at, label=None, rot_z=0.0, flip=False):
    c = {"part": f"airmn_{part}", "at": [round(v, 3) for v in at]}
    if label:
        c["label"] = label
    if rot_z:
        c["rot_z"] = rot_z
    if flip:
        c["xform"] = FLIP + [round(v, 3) for v in at]
        del c["at"]
    return c


def local_bounds(part):
    """Axis-aligned local extents (xmin, xmax, ymin, ymax, zmin, zmax) of a part, by hand."""
    p = PARTS[part][2]
    _, (bx, by, bz) = ap.expected(part, p)
    if part == "rotor":
        n = p["blades"]
        pts = [q for k in range(n) for q in ap.rotor_blade_pts(p, 360 * k / n + 180 / n)]
        r = p["hub_d"] / 2
        xs, ys = [q[0] for q in pts] + [-r, r], [q[1] for q in pts] + [-r, r]
        return min(xs), max(xs), min(ys), max(ys), 0, bz
    if part == "pd_board":
        return -p["l"] / 2, p["l"] / 2 + p["usbc"]["overhang"], -by / 2, by / 2, 0, bz
    return -bx / 2, bx / 2, -by / 2, by / 2, 0, bz


def extents(comps):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for c in comps:
        part = c["part"][6:]
        x0, x1, y0, y1, z0, z1 = local_bounds(part)
        corners = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        if "xform" in c:
            m, t = c["xform"][:9], c["xform"][9:]
            pts = [tuple(sum(q[i] * m[3 * i + j] for i in range(3)) + t[j] for j in range(3)) for q in corners]
        else:
            a = math.radians(c.get("rot_z", 0))
            ca, sa = math.cos(a), math.sin(a)
            t = c["at"]
            pts = [(x * ca - y * sa + t[0], x * sa + y * ca + t[1], z + t[2]) for x, y, z in corners]
        for q in pts:
            for i in range(3):
                lo[i], hi[i] = min(lo[i], q[i]), max(hi[i], q[i])
    return [round(h - l, 2) for l, h in zip(lo, hi)]


# Stack (z, mm; z = 0 at the base plate's underside). The frame is 1 mm shorter than the uncompressed stack, so
# each comb's beads are squeezed 0.5 mm: the base groove floor and the fan head's flange overlap them by 0.5.
SQUEEZE = 0.5
Z = {"base": -5.0, "pd": 3.2, "frame": 20.0, "comb_low": 16.0 - SQUEEZE}
Z["pack"] = Z["comb_low"] + 4.0                     # slot floor: bead 1 + ring 10 - slot 7
Z["comb_high"] = Z["pack"] + 450.0 + 4.0            # flipped: its bead face is the top
Z["head"] = Z["frame"] + 453.0 - 5.0 - 26.0         # cup bottom; spigot 26 above it, flange on the frame rim
Z["rotor"] = Z["head"] + 91.0                       # 1 over the motor plate; struts end 50 below
Z["motor"] = Z["rotor"] + 6.0                       # flipped: shaft end 6 into the hub, face under the plate
SQUEEZED = [["airmn_base", "airmn_comb"], ["airmn_comb", "airmn_fan_head"]]


def assembled():
    """Filter in a perforated frame on the base; the fan head (rotor and motor inside) sits on the frame."""
    return [comp("base", (0, 0, Z["base"])), comp("pd_board", (147.7, 0, Z["pd"])),
            comp("frame", (0, 0, Z["frame"])), comp("comb", (0, 0, Z["comb_low"]), "comb_low"),
            comp("pleat_pack", (0, 0, Z["pack"])), comp("comb", (0, 0, Z["comb_high"]), "comb_high", flip=True),
            comp("rotor", (0, 0, Z["rotor"])), comp("motor", (0, 0, Z["motor"]), flip=True),
            comp("fan_head", (0, 0, Z["head"]))]


def exploded():
    """Axis stack in fitting order with 40 mm gaps; the frame beside it at x = -480, from the pack base."""
    gap, z, c = 40.0, 0.0, []
    def h(part):
        return local_bounds(part)[5]
    c.append(comp("pd_board", (147.7, 0, z + 8.2)))
    for part, label in [("base", None), ("comb", "comb_low"), ("pleat_pack", None), ("comb", "comb_high"),
                        ("motor", None), ("fan_head", None), ("rotor", None)]:
        if label == "comb_high" or part == "motor":
            c.append(comp(part, (0, 0, z + h(part)), label, flip=True))
        else:
            c.append(comp(part, (0, 0, z), label))
        if part == "pleat_pack":
            c.append(comp("frame", (-480.0, 0, z)))
        z += h(part) + gap
    return c


def gen_assemblies():
    a = assembled()
    write(ROOT / "assemblies" / "airmn" / "assembly.json", json.dumps({
        "_comment": "airmn bench prototype, assembled (6th pass: perforated frame, comb-gaskets, one-part fan "
                    "head). z = 0 at the base plate's underside; stack in projects/airmn/requirements.md.",
        "components": a,
        "expected": {"_comment": "x, y: 430 across; z: feet -5 .. fan head top 621. Only the comb beads overlap "
                                 "(0.5 mm squeeze at the base and under the fan head); every other fit has "
                                 "clearance or only touches.",
                     "bbox": extents(a), "allowed_interference": SQUEEZED}}, indent=1) + "\n")
    e = exploded()
    write(ROOT / "assemblies" / "airmn_exploded" / "assembly.json", json.dumps({
        "_comment": "airmn exploded: stack on the axis in fitting order with 40 mm gaps; frame at x = -480 from "
                    "the pack base. Extents worked out from each part's spec bbox.",
        "components": e,
        "expected": {"bbox": extents(e), "allowed_interference": []}}, indent=1) + "\n")
    print("assembly bbox", extents(a), "exploded bbox", extents(e))


if __name__ == "__main__":
    gen_parts()
    gen_assemblies()
