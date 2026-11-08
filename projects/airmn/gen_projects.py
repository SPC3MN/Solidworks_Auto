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

RODS = {"rod_r": 209.0, "rod_angles": [18, 90, 162, 234, 306], "rod_hole": 5.5}
PLEAT = {"pleats": 120, "pleat_ro": 200.0, "pleat_ri": 150.0, "fold_flat": 2.0}
IMP = {"rim_r": 150.0, "blade_r0": 100.0, "blade_angle": 40.0, "blades": 9, "tab_w": 2.6,
       "tab_inset0": 1.0, "tab_inset1": 16.0, "slot_clear": 0.2}
CAP_D = 430.0
BAND_SEAT = {"rabbet_id": 424.0, "rabbet_depth": 3.0}

PARTS = {
    "bottom_cap": ("PETG, printed in sectors", "Closed bottom disc: lower comb groove, M5 rod holes with nut pockets underneath, USB-C PD board pocket and cable channel.", {
        "d": CAP_D, "t": 20.0, "groove_od": 408.0, "groove_id": 288.0, "groove_depth": 4.0, **RODS,
        "nut_pocket_d": 10.0, "nut_pocket_depth": 6.0,
        "pd_pocket": {"x": 145.0, "l": 40.0, "w": 30.0, "h": 8.0}, "cable_channel": {"x0": 160.0, "w": 12.0}}),
    "comb": ("PETG", "Pleat comb (one part, used top and bottom): ring with a zigzag slot that holds all 120 pleat folds at even pitch.", {
        "od": 406.0, "id": 292.0, "t": 10.0, "slot_w": 1.6, "slot_depth": 7.0, **PLEAT}),
    "pleat_pack": ("MERV 13 synthetic roll media", "Pleated filter wall: 120 pleats 50 deep, 0.8 media, 450 tall (seam overlap not modelled).", {
        "h": 450.0, "media_t": 0.8, **PLEAT}),
    "gasket": ("Closed-cell foam tape", "Comb seal, top and bottom, modelled uncompressed.", {
        "od": 406.0, "id": 290.0, "t": 3.0}),
    "inlet_ring": ("PETG", "Top-cap ring: upper comb groove underneath, outlet-band seat, M5 rod holes, stepped bellmouth into the impeller eye.", {
        "d": CAP_D, "id": 240.0, "t": 10.0, "groove_od": 408.0, "groove_id": 288.0, "groove_depth": 4.0,
        **BAND_SEAT, **RODS,
        "spider_screw_r": 132.5, "spider_screw_angles": [54, 126, 198, 270, 342], "spider_screw_depth": 8.0,
        "bellmouth_steps": [[260.0, 222.0, 5.0], [228.0, 186.0, 5.0], [189.0, 183.0, 8.0]]}),
    "outlet_band": ("PETG", "Dot-grid outlet band, flush with the caps and outside the rods: holes 7.2 on a 8.57 hex pitch (64 % open) over the impeller outlet.", {
        "od": CAP_D, "id": 425.0, "h": 162.0, "hole_d": 7.2, "units": 157, "rows": 16,
        "row_z0": 20.0, "row_pitch": 7.42}),
    "blade": ("PETG", "Flat impeller blade, 40 deg back from radial at the rim, trailing edge tapered to 0.5, tabs into the shroud and backplate slots.", {
        "t": 3.0, "te": 0.5, "taper_l": 15.0, "h": 112.0, "tab_h": 3.0, **IMP}),
    "shroud": ("PETG", "Impeller shroud: 195 eye, 9 blade slots through.", {
        "od": 300.0, "eye_d": 195.0, "t": 3.0, **IMP}),
    "backplate": ("PETG", "Impeller backplate with integral hub on the 8 mm shaft, 9 blade slots, M3 clamp screw.", {
        "od": 300.0, "t": 4.0, "hub_d": 40.0, "hub_h": 20.0, "bore": 8.0, "slot_depth": 3.0, **IMP}),
    "bridge": ("PETG", "Stiff motor bridge: ring clamped by the 5 rods, 5 spokes, hub with two 608 seats, M3 holes for the grommets.", {
        "d": CAP_D, "ring_id": 350.0, "t": 12.0, "hub_d": 80.0, "hub_h": 40.0, "spoke_w": 20.0, "bore": 12.0,
        "seat_d": 22.0, "seat_depth": 7.0, **BAND_SEAT, **RODS,
        "grommet_r": 30.0, "grommet_angles": [45, 135, 225, 315], "grommet_screw_depth": 8.0}),
    "top_cover": ("PETG, foam lined inside (liner not modelled)", "Top cover flush with the band: encloses bridge hub, grommets, bracket, coupling and motor; tie rods end in nut counterbores in its top.", {
        "d": CAP_D, "id": 424.0, "h": 167.0, "top_t": 10.0, "nut_cbore_d": 10.0, "nut_cbore_depth": 6.0, **RODS}),
    "impeller_housing": ("PETG", "Lid round the impeller: solid 430 wall seated in the inlet ring's rabbet, 8 mm top plate perforated with 7.2 holes on a 8.57 hex pitch (64 % open) for a vertical outlet; tie rods end in nut counterbores in the top.", {
        "d": CAP_D, "id": 425.0, "h": 173.0, "top_t": 8.0, "hole_d": 7.2, "hole_pitch": 8.57, "grid_r": 200.0,
        "nut_cbore_d": 10.0, "nut_cbore_depth": 5.0, **RODS}),
    "spider": ("PETG", "Motor spider inside the pack's core, screwed under the inlet ring: 5 spokes (5 vs 9 blades), hub with two 608 seats, motor hung below on grommets.", {
        "od": 280.0, "ring_id": 250.0, "t": 12.0, "hub_d": 80.0, "hub_h": 40.0, "spoke_w": 16.0,
        "spoke_angles": [18, 90, 162, 234, 306], "bore": 12.0, "seat_d": 22.0, "seat_depth": 7.0,
        "screw_r": 132.5, "screw_angles": [54, 126, 198, 270, 342], "screw_hole": 3.4,
        "grommet_r": 30.0, "grommet_angles": [45, 135, 225, 315], "grommet_screw_depth": 8.0}),
    "motor_bracket": ("PETG", "Motor bracket on 4 grommets: flange, tube round the coupling, plate for the motor face.", {
        "flange_d": 80.0, "flange_t": 5.0, "tube_od": 66.0, "tube_id": 56.0, "tube_h": 25.0, "plate_t": 5.0,
        "shaft_hole": 12.0, "motor_screw_pitch": 17.0, "motor_screw_hole": 3.2,
        "grommet_r": 30.0, "grommet_angles": [45, 135, 225, 315], "grommet_hole": 3.4}),
    "motor": ("Bought: E-S Motor 25 mm gearhead brushless 24 V 600 rpm", "Envelope stand-in: body and 4 mm D shaft (estimated).", {
        "d": 25.0, "body_l": 75.0, "shaft_d": 4.0, "shaft_l": 12.0, "flat": 1.5, "flat_l": 10.0}),
    "coupling": ("Bought: jaw coupling 4 x 8", "Flexible jaw coupling as one body (spider not modelled).", {
        "d": 20.0, "l": 25.0, "bore_low": 8.0, "depth_low": 12.0, "bore_high": 4.0, "depth_high": 10.0}),
    "shaft": ("Steel", "Impeller shaft 8 mm, from the impeller hub down through the eye to the spider.", {"_kind": "rod", "d": 8.0, "l": 222.0}),
    "tie_rod": ("Steel M5 threaded rod (nominal diameter)", "Tie rod, 5 used.", {"_kind": "rod", "d": 5.0, "l": 652.0}),
    "grommet": ("Silicone", "Motor soft mount, 4 used.", {"od": 10.0, "id": 3.2, "h": 6.0}),
    "nut_m5": ("Steel", "ISO 4032 M5 nut (hole at nominal 5).", {"_kind": "nut", "af": 8.0, "t": 4.0, "d": 5.0}),
    "foot": ("Rubber", "Soft foot, 4 used.", {"_kind": "rod", "d": 20.0, "l": 5.0}),
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
    if part == "blade":
        d, s0, s1 = ap.blade_geom(p)
        return s0, s1, -d - p["t"] / 2, -d + p["t"] / 2, 0, bz
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
            if part == "blade" and c.get("rot_z", 0):  # rotated blades stay inside the 150 rim
                pts = [(max(min(px, 150.2), -150.2), max(min(py, 150.2), -150.2), pz) for px, py, pz in pts]
        for q in pts:
            for i in range(3):
                lo[i], hi[i] = min(lo[i], q[i]), max(hi[i], q[i])
    return [round(h - l, 2) for l, h in zip(lo, hi)]


Z = {"cap": 0.0, "gasket_low": 16.0, "comb_low": 19.0, "pack": 22.0, "comb_high_top": 475.0, "gasket_high": 475.0,
     "inlet": 474.0, "spider": 434.0, "bearing_low": 434.0, "bearing_high": 467.0, "shroud": 497.0,
     "blades": 497.0, "backplate": 612.0, "shaft": 414.0, "grommets": 428.0, "bracket_top": 428.0,
     "coupling_top": 424.0, "motor_t": 405.0, "nut_low": 1.0, "rod": 1.0, "nut_high": 649.0, "housing": 481.0, "foot": -5.0,
     "pd": 3.2}


def assembled():
    """Motor group inside the pack's core: spider under the inlet ring, bracket, coupling and motor hung below it
    (flipped, motor shaft up). No exterior yet: the impeller is open above."""
    rp = [ap.polar(RODS["rod_r"], a) for a in RODS["rod_angles"]]
    gp = [ap.polar(30.0, a) for a in (45, 135, 225, 315)]
    c = [comp("bottom_cap", (0, 0, Z["cap"]))]
    c += [comp("foot", (*ap.polar(170, a), Z["foot"]), f"foot_{i + 1}") for i, a in enumerate((45, 135, 225, 315))]
    c.append(comp("pd_board", (147.7, 0, Z["pd"])))
    c += [comp("gasket", (0, 0, Z["gasket_low"]), "gasket_low"), comp("comb", (0, 0, Z["comb_low"]), "comb_low"),
          comp("pleat_pack", (0, 0, Z["pack"])), comp("comb", (0, 0, Z["comb_high_top"]), "comb_high", flip=True),
          comp("gasket", (0, 0, Z["gasket_high"]), "gasket_high"), comp("inlet_ring", (0, 0, Z["inlet"])),
          comp("shroud", (0, 0, Z["shroud"])), comp("impeller_housing", (0, 0, Z["housing"]))]
    c += [comp("blade", (0, 0, Z["blades"]), f"blade_{k + 1}", rot_z=40.0 * k) for k in range(9)]
    c += [comp("backplate", (0, 0, Z["backplate"])), comp("shaft", (0, 0, Z["shaft"])),
          comp("spider", (0, 0, Z["spider"]))]
    c += [{"part": "grindmn_bearing_608", "at": [0, 0, Z["bearing_low"]], "label": "bearing_low"},
          {"part": "grindmn_bearing_608", "at": [0, 0, Z["bearing_high"]], "label": "bearing_high"}]
    c += [comp("grommet", (x, y, Z["grommets"]), f"grommet_{i + 1}") for i, (x, y) in enumerate(gp)]
    c += [comp("motor_bracket", (0, 0, Z["bracket_top"]), flip=True),
          comp("coupling", (0, 0, Z["coupling_top"]), flip=True), comp("motor", (0, 0, Z["motor_t"]), flip=True)]
    for i, (x, y) in enumerate(rp):
        c += [comp("tie_rod", (x, y, Z["rod"]), f"rod_{i + 1}"), comp("nut_m5", (x, y, Z["nut_low"]), f"nut_low_{i + 1}"),
              comp("nut_m5", (x, y, Z["nut_high"]), f"nut_high_{i + 1}")]
    return c


def exploded():
    """Axis stack in fitting order with 40 mm gaps; motor group in a column beside it; rods and nuts round it."""
    gap, z, c = 40.0, 0.0, []
    def h(part):
        return local_bounds(part)[5]
    for i, a in enumerate((45, 135, 225, 315)):
        c.append(comp("foot", (*ap.polar(170, a), z), f"foot_{i + 1}"))
    c.append(comp("pd_board", (147.7, 0, z + 10)))
    z += h("foot") + gap
    seq = [("bottom_cap", None), ("gasket", "gasket_low"), ("comb", "comb_low"), ("pleat_pack", None),
           ("comb", "comb_high"), ("gasket", "gasket_high"), ("inlet_ring", None), ("shroud", None),
           ("blades", None), ("backplate", None), ("impeller_housing", None)]
    for part, label in seq:
        if part == "blades":
            c += [comp("blade", (0, 0, z), f"blade_{k + 1}", rot_z=40.0 * k) for k in range(9)]
            z += h("blade") + gap
        elif label == "comb_high":
            c.append(comp("comb", (0, 0, z + h("comb")), label, flip=True))
            z += h("comb") + gap
        else:
            c.append(comp(part, (0, 0, z), label))
            z += h(part) + gap
    # motor group at x = -460, bottom up in fitting order, starting at the pack's base
    zp = next(q["at"][2] for q in c if q["part"] == "airmn_pleat_pack")
    x, zz = -460.0, zp
    for part in ("motor", "motor_bracket", "coupling", "grommets", "bearing_low", "spider", "bearing_high", "shaft"):
        if part in ("motor", "motor_bracket", "coupling"):
            c.append(comp(part, (x, 0, zz + h(part)), flip=True))
            zz += h(part) + 25.0
        elif part == "grommets":
            c += [comp("grommet", (x + gx, gy, zz), f"grommet_{i + 1}")
                  for i, (gx, gy) in enumerate(ap.polar(30, a) for a in (45, 135, 225, 315))]
            zz += h("grommet") + 25.0
        elif part.startswith("bearing"):
            c.append({"part": "grindmn_bearing_608", "at": [x, 0, zz], "label": part})
            zz += 7.0 + 25.0
        else:
            c.append(comp(part, (x, 0, zz)))
            zz += h(part) + 25.0
    for i, a in enumerate(RODS["rod_angles"]):
        px, py = ap.polar(320.0, a)
        c += [comp("nut_m5", (px, py, 0), f"nut_low_{i + 1}"), comp("tie_rod", (px, py, 24.0), f"rod_{i + 1}"),
              comp("nut_m5", (px, py, 24.0 + 652.0 + 20.0), f"nut_high_{i + 1}")]
    return c


def bearing_aware_extents(comps):
    plain = [q for q in comps if q["part"].startswith("airmn_")]
    box = extents(plain)
    return box  # the 608s (22 x 7) sit inside the bridge or the shaft column, never on the outside


def gen_assemblies():
    a = assembled()
    write(ROOT / "assemblies" / "airmn" / "assembly.json", json.dumps({
        "_comment": "airmn bench prototype, assembled. z = 0 at the bottom cap's underside; stack heights in "
                    "projects/airmn/requirements.md (Layout). Rods on R209 at 18 + 72k deg; blades every 40 deg.",
        "components": a,
        "expected": {"_comment": "x, y: caps 430 across; z: feet -5 .. impeller housing top 481 + 173 = 654. Solid lid round the impeller, perforated top (vertical outlet); the motor group hangs under the inlet ring inside the pack's core. No interference "
                                 "allowed: every hole, groove and slot has clearance, and nominal M5 rod in nominal "
                                 "nut bore only touches.",
                     "bbox": bearing_aware_extents(a), "allowed_interference": []}}, indent=1) + "\n")
    e = exploded()
    write(ROOT / "assemblies" / "airmn_exploded" / "assembly.json", json.dumps({
        "_comment": "airmn exploded: housing stack on the axis in fitting order with 40 mm gaps; motor group "
                    "(motor, bracket, coupling, grommets, 608, spider, 608, shaft) at x = -460 from the pack base; "
                    "rods and nuts on R320 at the rod angles. Extents worked out from each part's spec bbox.",
        "components": e,
        "expected": {"bbox": bearing_aware_extents(e), "allowed_interference": []}}, indent=1) + "\n")
    print("assembly bbox", bearing_aware_extents(a), "exploded bbox", bearing_aware_extents(e))


if __name__ == "__main__":
    gen_parts()
    gen_assemblies()
