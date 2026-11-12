"""Write round-5 option A of flacmn_deck_pro_housing: params.json, option.json, wrap.json, front.json, back.json.

From the owner's layout (references/electronics_views/flacmn_deck_layout.svg, scaled to true size):
Wrap: top, both sides and bottom in one folded piece (3 folds); its open seam (bottom to right side) is
closed by the two end panels. Front and back: flat panels with four inward flanges; ISO 4762 M3 x 8 through
the wrap's top, sides and bottom into clinch nuts in the flanges (4 per panel). The 5in DSI screen is taped
behind the front panel, both encoders nut into it, and the caps sit proud on the shafts. The Pi + DAC sit
on the wrap's floor at the back right; cords thread out through cut-outs in the back panel."""
import json, sys
from pathlib import Path

OUT = Path(sys.argv[1])

def P(v, src="chosen", note=None):
    d = {"value": v, "src": src}
    if note:
        d["note"] = note
    return d

LAY = "owner's layout, true scale"
params = {
    "t": P(1.0, "given", "5052-H32 1.0, the only material profile"),
    "hinge": P(0.5, "estimated", "bridges bend at mid-thickness until a coupon says otherwise"),
    "allow": P(0.0, "estimated", "flat length taken by a fold; 0 until measured"),
    "corner": P(0.3, "chosen", "gap where the bottom meets the right side"),
    "gap": P(0.3, "chosen", "end panel edge to wrap inner face"),
    "W": P(241.0, "given", LAY), "H": P(88.5, "given", LAY), "D": P(100.5, "given", LAY),
    # end panels and their flanges
    "fl": P(10.0, "chosen", "flange depth: CLS-M3-0 needs 4.8 to the edge"),
    "inset": P(1.5, "chosen", "side flanges stop short of the top/bottom flanges"),
    "po": "t + gap + hinge*t", "pw": "W - 2*po", "ph": "H - 2*t - 2*hinge*t - allow",
    "fy": "hinge*t + fl/2", "ry": "D - hinge*t - fl/2",          # screw lines, front and back
    "scr_x_top": "W/2", "scr_x_bot": P(72.0, "chosen", "under the screen at the front; inside the back flange segment"),
    "nut_hole": P(4.22, "given", "PEM CLS-M3-0 mounting hole"), "screw_hole": 3.4,
    "head_d": P(5.5, "given", "projects/grindmn_screw_m3x8"), "head_h": P(3.0, "given", "projects/grindmn_screw_m3x8"),
    "bfl_x0": 12.0, "bfl_x1": 132.0,                               # back bottom flange segment (clear of the Pi)
    # Pi 4 + DAC Pro stack on the floor (floor top at z = t), USB/Ethernet end toward -x
    "pcb_l": P(85.0, "given"), "pcb_w": P(56.0, "given"), "pcb_t": P(1.4, "given"),
    "jack_oh": P(2.7, "estimated", "USB/Ethernet past the Pi's PCB edge"),
    "sd_oh": P(2.5, "estimated", "microSD card past the PCB edge"),
    "h_so": P(3.0, "chosen", "M2.5 standoff under the Pi = thermal pad gap"),
    "h_hat": P(9.0, "given", "DAC Pro standoffs"), "hat_t": P(1.6, "given"),
    "hat_l": P(65.0, "given"), "hat_w": P(56.5, "given"),
    "jumper_h": P(14.0, "estimated", "Dupont housing on the pass-through header (encoder wires)"),
    "wire_bend": P(6.0, "estimated"),
    "rca_len": P(9.0, "given", "projects/rpi_dac_pro: barrels past the HAT edge"),
    "sock_recess": P(1.0, "chosen", "socket tips stop this far inside the back panel"),
    "px1": "W - 2*t - sd_oh - 2", "px0": "px1 - pcb_l",
    "py1": "D - t - sock_recess - rca_len", "py0": "py1 - pcb_w",
    "zp": "t + h_so", "zpt": "zp + pcb_t", "zh": "zpt + h_hat", "zht": "zh + hat_t",
    # back panel openings
    "rca_x1": "px1 - 18.36", "rca_x2": "px1 - 32.98", "rca_z": "zht + 6.5",
    "rca_hole": P(13.0, "estimated", "RCA plug shell passes"),
    "jack_x": "px1 - 51.8", "jack_z": "zht + 3", "jack_hole": P(10.0, "estimated"),
    "usbc_x": "px1 - 11.2", "usbc_z": "zpt + 1.6",
    "usbc_w": P(13.0, "estimated", "USB-C overmold passes"), "usbc_h": P(7.5, "estimated"),
    "cord_z": 26.0, "cord_l": P(24.0, "estimated", "plug overmold passes"),
    "eth_slot": P(18.0, "estimated", "RJ45 plug with boot passes"), "usb_slot": P(12.0, "estimated", "USB-A plug passes"),
    "cord1_x": 30.0, "cord2_x": 62.0, "cord3_x": 94.0,
    # screen: Waveshare 5inch DSI LCD (lcd5_dsi_views.svg)
    "lens_w": P(120.7, "given"), "lens_h": P(77.2, "given"), "lens_t": P(5.4, "given"),
    "scr_pcb_w": P(121.0, "given"), "scr_pcb_h": P(76.0, "given"), "scr_d": P(13.0, "given", "lens to the back parts"),
    "va_w": P(109.0, "given"), "va_h": P(65.8, "given"), "va_l": P(5.85, "given"), "va_top": P(3.1, "given"),
    "lens_x0": P(6.0, "given", LAY), "lens_z0": "(H - lens_h)/2",
    # encoders and knob caps
    "kb_d": P(57.0, "given", LAY), "ks_d": P(35.0, "given", LAY), "knob_h": P(10.5, "given", LAY),
    "kb_x": P(154.5, "given", LAY), "kb_z": "H/2", "ks_x": P(208.3, "given", LAY), "ks_z": P(56.9, "given", LAY),
    "knob_gap": P(1.0, "chosen", "cap back face to the front panel"),
    "enc_w": P(12.5, "estimated"), "enc_h": P(13.4, "estimated"), "enc_d": P(10.1, "estimated", "body 6.6 + pins"),
    "enc_hole": P(7.4, "given"), "enc_tab_r": P(7.5, "estimated", "anti-turn tab offset"), "enc_tab_d": 2.4,
    "bush_out": P(6.0, "estimated", "bushing past the panel"),
    "feet_h": P(6.0, "chosen", "taller than the screw heads under the floor"), "feet_d": 10.0,
    "foot_y": 25.0,
    "soc_x": "px1 - 29", "soc_y": "py1 - 32",
}

rect = lambda w, h: [[0, 0], [w, 0], [w, h], [0, h]]
recipes = {"fold": {"_comment": "Starting guess for 1.0 mm 5052-H32. UNTESTED until a coupon holds.",
                    "method": "slots", "slot_length": 8.0, "slot_width": 0.5, "bridge": 1.5,
                    "end_clearance": 2.0, "hinge": "hinge", "allowance": "allow"}}
circ = lambda d, u, v: {"type": "circle", "d": d, "at": [u, v]}

# ---- wrap: top placed at [hinge*t, 0, H - t]; sides hang down; the floor folds in from the left side
wp = {"tw": "W - 2*hinge*t", "wl": "H - 2*hinge*t - allow", "wr": "H - hinge*t - allow",
      "bw": "W - hinge*t - t - corner"}
wv = lambda z: f"H - hinge*t - ({z})"                # world z -> side wall v
pi_holes = [(f"px1 - {hx}", f"py1 - {hy}") for hx in (3.5, 61.5) for hy in (3.5, 52.5)]
feet = [(14, "foot_y"), ("W - 14", "foot_y"), (14, "D - foot_y"), ("W - 14", "D - foot_y")]
wrap = {
    "_comment": "flacmn deck pro wrap: top, sides and floor in one piece; the end panels close the floor-to-right-side seam. Round 5.",
    "name": "wrap", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **wp},
    "panels": [
        {"id": "top", "name": "Top", "outline": rect("tw", "D"), "features": [
            circ("screw_hole", "scr_x_top - hinge*t", "fy"), circ("screw_hole", "scr_x_top - hinge*t", "ry")]},
        {"id": "left", "name": "Left side", "outline": rect("D", "wl"), "features": [
            circ("screw_hole", "fy", wv("H/2")), circ("screw_hole", "ry", wv("H/2"))]},
        {"id": "right", "name": "Right side", "outline": rect("D", "wr"), "features": [
            circ("screw_hole", "D - fy", wv("H/2")), circ("screw_hole", "D - ry", wv("H/2"))]},
        {"id": "floor", "name": "Floor", "outline": rect("D", "bw"), "features": [
            circ("screw_hole", "D - fy", "scr_x_bot - hinge*t"), circ("screw_hole", "D - ry", "scr_x_bot - hinge*t"),
            *[circ(2.9, f"D - ({y})", f"{x} - hinge*t") for x, y in pi_holes]]},
    ],
    "folds": [
        {"id": "f_left", "parent": "top", "parent_edge": 3, "child": "left", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold"},
        {"id": "f_right", "parent": "top", "parent_edge": 1, "child": "right", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 3, "recipe": "fold"},
        {"id": "f_floor", "parent": "left", "parent_edge": 2, "child": "floor", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 1, "recipe": "fold"},
    ],
    "recipes": recipes,
    "hardware": [],
}

# ---- end panels: the top flange is the root (horizontal, under the wrap top); the panel folds down from it
def end_panel(pid, name, edge, y0, face_feats, bottom_seg):
    ep = {"sl": "ph - 2*inset"}
    u = (lambda x: f"pw - (({x}) - po)") if edge == 0 else (lambda x: f"({x}) - po")
    pv = lambda z: f"H - t - hinge*t - ({z})"
    feats = [{**f, "at": [u(f["at"][0]), pv(f["at"][1])]} for f in face_feats]
    if bottom_seg:
        bl, boff, bu = "bfl_x1 - bfl_x0", "pw - (bfl_x1 - po)", "bfl_x1 - scr_x_bot"
    else:
        bl, boff, bu = "pw", 0, "scr_x_bot - po"
    panels = [
        {"id": "top_fl", "name": "Top flange", "outline": rect("pw", "fl"), "features": [
            circ("nut_hole", "scr_x_top - po", "fl/2")]},
        {"id": "panel", "name": name, "outline": rect("pw", "ph"), "features": feats},
        {"id": "bot_fl", "name": "Bottom flange", "outline": rect(bl, "fl"), "features": [circ("nut_hole", bu, "fl/2")]},
        {"id": "l_fl", "name": "Side flange", "outline": rect("sl", "fl"), "features": [circ("nut_hole", "sl/2", "fl/2")]},
        {"id": "r_fl", "name": "Side flange", "outline": rect("sl", "fl"), "features": [circ("nut_hole", "sl/2", "fl/2")]},
    ]
    folds = [
        {"id": "f_panel", "parent": "top_fl", "parent_edge": edge, "child": "panel", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 3, "recipe": "fold"},
        {"id": "f_bot", "parent": "panel", "parent_edge": 2, "child": "bot_fl", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 1, "recipe": "fold", "offset": boff},
        {"id": "f_l", "parent": "panel", "parent_edge": 1, "child": "l_fl", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold", "offset": "inset"},
        {"id": "f_r", "parent": "panel", "parent_edge": 3, "child": "r_fl", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold", "offset": "inset"},
    ]
    return {"_comment": f"flacmn deck pro {name.lower()}: flat panel with four inward flanges; M3 clinch nuts in the flanges. Round 5.",
            "name": pid, "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
            "params": {**params, **ep}, "panels": panels, "folds": folds, "recipes": recipes,
            "hardware": [{"name": "PEM CLS-M3-0 clinch nut (flanges, pressed from inside)", "qty": 4}]}

va_x0, va_z1 = "lens_x0 + va_l", "lens_z0 + lens_h - va_top"
front = end_panel("front", "Front panel", 0, "hinge*t", [
    {"type": "rect", "size": ["va_w + 1", "va_h + 1"], "at": [f"{va_x0} + va_w/2", f"{va_z1} - va_h/2"]},
    {"type": "circle", "d": "enc_hole", "at": ["kb_x", "kb_z"]},
    {"type": "circle", "d": "enc_tab_d", "at": ["kb_x", "kb_z + enc_tab_r"]},
    {"type": "circle", "d": "enc_hole", "at": ["ks_x", "ks_z"]},
    {"type": "circle", "d": "enc_tab_d", "at": ["ks_x", "ks_z + enc_tab_r"]}], False)
back = end_panel("back", "Back panel", 2, "D - hinge*t - fl", [
    {"type": "circle", "d": "rca_hole", "at": ["rca_x1", "rca_z"]},
    {"type": "circle", "d": "rca_hole", "at": ["rca_x2", "rca_z"]},
    {"type": "circle", "d": "jack_hole", "at": ["jack_x", "jack_z"]},
    {"type": "slot", "length": "usbc_w", "width": "usbc_h", "angle": 0, "at": ["usbc_x", "usbc_z"]},
    {"type": "slot", "length": "cord_l", "width": "eth_slot", "angle": 0, "at": ["cord1_x", "cord_z"]},
    {"type": "slot", "length": "cord_l", "width": "usb_slot", "angle": 0, "at": ["cord2_x", "cord_z"]},
    {"type": "slot", "length": "cord_l", "width": "usb_slot", "angle": 0, "at": ["cord3_x", "cord_z"]}], True)

def box(sx, sy, sz, cx, cy, z):
    return {"type": "box", "size": [sx, sy, sz], "at": [cx, cy, z]}
cyl = lambda d, h, axis, at: {"type": "cyl", "d": d, "h": h, "axis": axis, "at": at}

def encoder(x, z, d, pid, name):
    return [
        {"id": f"enc_{pid}", "name": f"PEC11R encoder, {name} (nut outside the panel)", "source": "library", "library": "encoder_pec11r", "bodies": [
            box("enc_w", "enc_d", "enc_h", x, "t + enc_d/2", f"{z} - enc_h/2"),
            cyl(7, "bush_out + t", "y", [x, "-bush_out", z]),
            cyl(6, "knob_gap + knob_h - bush_out - 1", "y", [x, "-(knob_gap + knob_h - 1)", z])]},
        {"id": f"knob_{pid}", "name": f"Knob cap, {name} (Ø{d} x 10.5, counterbored over the nut)", "source": "buy", "bodies": [
            cyl(d, "knob_h", "y", [x, "-(knob_gap + knob_h)", z])]}]

parts = [
    {"id": "wrap", "name": "Wrap (top, sides, floor)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "wrap.json", "at": ["hinge*t", 0, "H - t"]},
    {"id": "front", "name": "Front panel", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "front.json", "at": ["po", "hinge*t", "H - 2*t"]},
    {"id": "back", "name": "Back panel (removable)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "back.json", "at": ["po", "D - hinge*t - fl", "H - 2*t"]},
    {"id": "pi4", "name": "Raspberry Pi 4 B", "source": "buy", "bodies": [
        box("pcb_l", "pcb_w", "pcb_t", "px0 + pcb_l/2", "py0 + pcb_w/2", "zp"),
        box("17.4 + jack_oh", 53, 16, "px0 - jack_oh + (17.4 + jack_oh)/2", "py0 + 28", "zpt")]},
    {"id": "dac", "name": "Raspberry Pi DAC Pro", "source": "library", "library": "rpi_dac_pro", "bodies": [
        box("hat_l", "hat_w", "hat_t", "px1 - hat_l/2", "py1 - hat_w/2 + 0.25", "zh"),
        box(27.6, 14, 13, "px1 - 25.8", "py1 - 7", "zht"),
        cyl(8, "rca_len", "y", ["rca_x1", "py1", "rca_z"]),
        cyl(8, "rca_len", "y", ["rca_x2", "py1", "rca_z"]),
        box(8, 12, 6, "jack_x", "py1 - 6", "zht")]},
    {"id": "jumpers", "name": "Encoder wires on the pass-through header", "source": "buy", "bodies": [
        box(51, 5, "2.5 + jumper_h", "px1 - 32.5", "py0 + 3.5", "zht")]},
    {"id": "standoff", "name": "M2.5 standoff 3 mm (Pi)", "source": "buy", "fastener": True,
     "bodies": [cyl(5, "h_so", "z", [0, 0, "t"])], "instances": [[x, y, 0] for x, y in pi_holes]},
    {"id": "pad", "name": "Thermal pad 15 x 15 x 3 under the processor", "source": "buy", "bodies": [
        box(15, 15, "h_so", "soc_x", "soc_y", "t")]},
    {"id": "screen", "name": "Waveshare 5inch DSI LCD (VHB to the front panel)", "source": "buy", "bodies": [
        box("lens_w", "lens_t", "lens_h", "lens_x0 + lens_w/2", "t + lens_t/2", "lens_z0"),
        box("scr_pcb_w", "scr_d - lens_t", "scr_pcb_h", "lens_x0 + lens_w/2", "t + lens_t + (scr_d - lens_t)/2", "(H - scr_pcb_h)/2")]},
    *encoder("kb_x", "kb_z", 57, "big", "large"),
    *encoder("ks_x", "ks_z", 35, "small", "small"),
    {"id": "feet", "name": "Rubber foot", "source": "buy",
     "bodies": [cyl("feet_d", "feet_h", "z", [0, 0, "-feet_h"])], "instances": [[x, y, 0] for x, y in feet]},
    {"id": "screw_top", "name": "ISO 4762 M3 x 8 (top)", "source": "library", "library": "grindmn_screw_m3x8", "fastener": True,
     "bodies": [cyl("head_d", "head_h", "z", [0, 0, "H"])], "instances": [["scr_x_top", "fy", 0], ["scr_x_top", "ry", 0]]},
    {"id": "screw_bot", "name": "ISO 4762 M3 x 8 (floor)", "source": "library", "library": "grindmn_screw_m3x8", "fastener": True,
     "bodies": [cyl("head_d", "head_h", "z", [0, 0, "-head_h"])], "instances": [["scr_x_bot", "fy", 0], ["scr_x_bot", "ry", 0]]},
    {"id": "screw_left", "name": "ISO 4762 M3 x 8 (left)", "source": "library", "library": "grindmn_screw_m3x8", "fastener": True,
     "bodies": [cyl("head_d", "head_h", "x", ["-head_h", 0, "H/2"])], "instances": [[0, "fy", 0], [0, "ry", 0]]},
    {"id": "screw_right", "name": "ISO 4762 M3 x 8 (right)", "source": "library", "library": "grindmn_screw_m3x8", "fastener": True,
     "bodies": [cyl("head_d", "head_h", "x", ["W", 0, "H/2"])], "instances": [[0, "fy", 0], [0, "ry", 0]]},
    {"id": "screw_pi", "name": "M2.5 x 6 screw (Pi, from below)", "source": "buy", "fastener": True,
     "bodies": [cyl(4.5, 1.0, "z", [0, 0, -1.0])], "instances": [[x, y, 0] for x, y in pi_holes]},
    {"id": "screw_dac", "name": "M2.5 screw (DAC Pro kit, on top)", "source": "buy", "fastener": True,
     "bodies": [cyl(4.5, 1.5, "z", [0, 0, "zht"])], "instances": [[x, y, 0] for x, y in pi_holes]},
]

option = {
    "schema_version": "1.0",
    "name": "Wrap + two screwed end panels",
    "summary": ("Round 5, from the owner's layout at true scale (241 x 88.5 x 100.5). One folded wrap (top, sides, "
                "floor; 3 folds) and two end panels with four inward flanges each (4 folds). Eight ISO 4762 M3 x 8 "
                "go through the wrap's top, sides and floor into clinch nuts in the flanges, which also close the "
                "wrap's open seam. The 5in DSI screen is taped behind the front panel; both encoders nut into it and "
                "the Ø57 and Ø35 caps sit proud on the shafts. The Pi + DAC sit on the floor at the back right; USB "
                "and Ethernet cords thread out through three cut-outs in the removable back panel."),
    "architecture": {
        "mechanism": "end panels screwed to the wrap; encoders nutted into the front panel; Pi on standoffs on the floor; caps pushed on",
        "layout": "screen left, knobs right on the front; Pi flat at the back right, sockets to the back, USB/Ethernet into the free space; cords out the back panel",
        "load_path": "knobs -> front panel -> flanges -> screws -> wrap -> feet -> shelf",
        "process": "laser-cut flat, 3 + 4 + 4 hand folds on perforated lines (UNTESTED recipe); clinch nuts pressed"},
    "parts": parts,
    "load_path": ["knob_big", "front", "wrap", "feet"],
    "dims": [
        {"view": "top", "dir": "h", "a": 0, "b": "W", "at": "D + 10", "param": "W"},
        {"view": "top", "dir": "v", "a": 0, "b": "D", "at": "W + 10", "param": "D"},
        {"view": "section", "dir": "v", "a": 0, "b": "H", "at": "W + 10", "param": "H"},
        {"view": "top", "dir": "h", "a": "kb_x - kb_d/2", "b": "kb_x + kb_d/2", "at": -16, "param": "kb_d"},
        {"view": "top", "dir": "h", "a": "ks_x - ks_d/2", "b": "ks_x + ks_d/2", "at": -16, "param": "ks_d"},
    ],
    "fit": [
        {"id": "jumpers_roof", "lhs": "zht + 2.5 + jumper_h + wire_bend", "op": "<=", "rhs": "H - 2*t - 1.5",
         "why": "Encoder wires clear the top flange's nut"},
        {"id": "rear_recessed", "lhs": "py1 + rca_len", "op": "<=", "rhs": "D - t - 0.5",
         "why": "RCA barrels stop inside the back panel"},
        {"id": "rca_web", "lhs": "rca_x1 - rca_x2 - rca_hole", "op": ">=", "rhs": 1.5, "why": "Web between the RCA openings"},
        {"id": "usbc_under_rca", "lhs": "usbc_z + usbc_h/2 + 3", "op": "<=", "rhs": "rca_z - rca_hole/2",
         "why": "USB-C and RCA openings keep a 3 mm web"},
        {"id": "back_flange_vs_sockets", "lhs": "bfl_x1 + 2", "op": "<=", "rhs": "jack_x - jack_hole/2",
         "why": "Back bottom flange stops short of the socket openings"},
        {"id": "cords_above_flange", "lhs": "t + fl + 1", "op": "<=", "rhs": "cord_z - eth_slot/2",
         "why": "Cord cut-outs clear the bottom flange"},
        {"id": "cords_apart", "lhs": "cord2_x - cord1_x - cord_l", "op": ">=", "rhs": 6, "why": "Webs between the cord cut-outs"},
        {"id": "cords_left_of_pi", "lhs": "cord3_x + cord_l/2 + 10", "op": "<=", "rhs": "px0 - jack_oh",
         "why": "Cord cut-outs in the free space, clear of the Pi"},
        {"id": "back_flange_vs_pi", "lhs": "bfl_x1 + 2", "op": "<=", "rhs": "px0 - jack_oh",
         "why": "Back bottom flange stops short of the Pi"},
        {"id": "sd_vs_wall", "lhs": "px1 + sd_oh + 1", "op": "<=", "rhs": "W - t",
         "why": "microSD clears the right side"},
        {"id": "pi_vs_back_flange_y", "lhs": "py1", "op": "<=", "rhs": "D - hinge*t - fl",
         "why": "Pi PCB in front of the back side flanges"},
        {"id": "va_vs_knob", "lhs": "lens_x0 + va_l + va_w + 1", "op": "<=", "rhs": "kb_x - kb_d/2",
         "why": "Large cap leaves the viewing area clear"},
        {"id": "knobs_apart", "lhs": "kb_x + kb_d/2 + 3", "op": "<=", "rhs": "ks_x - ks_d/2", "why": "Caps 3 mm apart"},
        {"id": "small_knob_in_face", "lhs": "ks_x + ks_d/2", "op": "<=", "rhs": "W - 3", "why": "Small cap inside the face"},
        {"id": "big_knob_in_face", "lhs": "kb_z + kb_d/2", "op": "<=", "rhs": "H - 3", "why": "Large cap inside the face height"},
        {"id": "small_knob_top", "lhs": "ks_z + ks_d/2", "op": "<=", "rhs": "H - 3", "why": "Small cap inside the face height"},
        {"id": "enc_vs_screen", "lhs": "lens_x0 + scr_pcb_w + 1", "op": "<=", "rhs": "kb_x - enc_w/2",
         "why": "Large encoder body clears the screen board"},
        {"id": "enc_vs_pi", "lhs": "t + enc_d + 1", "op": "<=", "rhs": "py0", "why": "Encoders in front of the Pi"},
        {"id": "screen_vs_flanges", "lhs": "lens_z0", "op": ">=", "rhs": "2*t + 1.5 + 1",
         "why": "Screen clears the bottom flange and its nut"},
        {"id": "screen_vs_top_nut", "lhs": "lens_z0 + lens_h", "op": "<=", "rhs": "H - 2*t - 1.5 - 1",
         "why": "Screen clears the top flange's nut"},
        {"id": "screen_vs_side_nut", "lhs": "lens_x0", "op": ">=", "rhs": "2*t + gap + 1.5 + 1",
         "why": "Screen clears the left flange's nut"},
        {"id": "feet_vs_heads", "lhs": "head_h + 1", "op": "<=", "rhs": "feet_h", "why": "Feet stand taller than the screw heads"},
        {"id": "nut_catches", "lhs": "t + 2.5", "op": "<=", "rhs": 7, "why": "Encoder bushing takes the tab, washer and M7 nut"},
    ],
    "allowed_interference": [
        ["dac", "jumpers", "wires on the pass-through header"],
        ["pi4", "standoff", "standoffs under the PCB"],
        ["pad", "pi4", "pad compressed under the PCB"],
        ["pad", "wrap", "pad compressed on the floor"],
        ["standoff", "wrap", "standoffs on the floor"],
        ["enc_big", "front", "bushing through the Ø7.4 hole"],
        ["enc_small", "front", "bushing through the Ø7.4 hole"],
        ["enc_big", "knob_big", "shaft and nut in the cap's counterbore"],
        ["enc_small", "knob_small", "shaft and nut in the cap's counterbore"],
        ["screw_pi", "wrap", "screw head under the floor"],
    ],
    "costs_vs_A": [],
    "from_inspiration": [],
    "section_y": "(py0 + py1)/2",
}

OUT.mkdir(parents=True, exist_ok=True)
for name, data in (("params.json", params), ("option.json", option), ("wrap.json", wrap),
                   ("front.json", front), ("back.json", back)):
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
