"""Write round-8 option A of flacmn_deck_pro_housing: params.json, option.json, shell.json, back.json.

From the owner's layout (references/electronics_views/flacmn_deck_layout.svg, scaled to true size) and the
round-5 push-back: Shell: the front face in the centre, with the top, bottom and both sides folding back from
it (4 folds). It is drawn flat in the sheet frame and stood up (`stand`): sheet (x, y) = (x - hinge*t,
H - hinge*t - z). Back: a flat plate with four inward flanges; ISO 4762 M3 x 8 through the shell's top, sides
and floor into clinch nuts in the flanges. Round 7: the back plate is flat; 4 M3 x 8 enter from the back
face into clinch nuts in tabs folded down from the top and up from the floor. The 5in DSI screen is taped behind the front face, both encoders
nut into it, and the caps sit proud on the shafts. The Pi + DAC sit on the floor at the back right; cords
thread out through cut-outs in the back plate."""
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
    "gap": P(0.3, "chosen", "back plate edge to shell inner face"),
    "W": P(241.0, "given", LAY), "H": P(88.5, "given", LAY), "D": P(100.5, "given", LAY),
    # end panels and their flanges
    "pw": "W - 2*(t + gap)", "ph": "H - 2*(t + gap)",
    "tab_w": P(16.0, "chosen", "clinch nut + 3 mm each side"), "tab_h": P(12.0, "chosen", "nut centre 7 from the fold"),
    "nut_v": 7.0,
    "tx1": 40.0, "tx2": "W - 40", "bx1": 40.0, "bx2": P(124.0, "chosen", "floor tab clear of the Pi's USB/Ethernet end"),
    "nut_hole": P(4.22, "given", "PEM CLS-M3-0 mounting hole"), "screw_hole": 3.4,
    "head_d": P(5.5, "given", "projects/grindmn_screw_m3x8"), "head_h": P(3.0, "given", "projects/grindmn_screw_m3x8"),
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
    "knob_gap": P(1.0, "chosen", "cap back face to the front face"),
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

# ---- shell: the front face is the root, laid flat; the top, floor and sides fold back from it
sp = {"fw": "W - 2*hinge*t", "fh": "H - 2*hinge*t", "inset": "(1 - hinge)*t + corner", "fl_l": "D - t - 2*hinge*t - allow", "lw": "fw - 2*inset"}
sx = lambda x: f"({x}) - hinge*t"                     # world x -> sheet x of the front face
sy = lambda z: f"H - hinge*t - ({z})"                 # world z -> sheet y of the front face
fv = lambda y: f"({y}) - hinge*t"                     # world y -> v on a flap (distance from its fold)
pi_holes = [(f"px1 - {hx}", f"py1 - {hy}") for hx in (3.5, 61.5) for hy in (3.5, 52.5)]
feet = [(14, "foot_y"), ("W - 14", "foot_y"), (14, "D - foot_y"), ("W - 14", "D - foot_y")]
va_x0, va_z1 = "lens_x0 + va_l", "lens_z0 + lens_h - va_top"
shell = {
    "_comment": "flacmn deck pro shell: front face with the top, floor and sides folded back from it. Round 6.",
    "name": "shell", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **sp},
    "panels": [
        {"id": "front", "name": "Front face", "outline": rect("fw", "fh"), "features": [
            {"type": "rect", "size": ["va_w + 1", "va_h + 1"], "at": [sx(f"{va_x0} + va_w/2"), sy(f"{va_z1} - va_h/2")]},
            circ("enc_hole", sx("kb_x"), sy("kb_z")), circ("enc_tab_d", sx("kb_x"), sy("kb_z + enc_tab_r")),
            circ("enc_hole", sx("ks_x"), sy("ks_z")), circ("enc_tab_d", sx("ks_x"), sy("ks_z + enc_tab_r"))]},
        {"id": "top", "name": "Top", "outline": rect("lw", "fl_l")},
        {"id": "floor", "name": "Floor", "outline": rect("lw", "fl_l"), "features": [
            *[circ(2.9, f"{sx(x)} - inset", fv(y)) for x, y in pi_holes]]},
        {"id": "left", "name": "Left side", "outline": rect("fh", "fl_l")},
        {"id": "right", "name": "Right side", "outline": rect("fh", "fl_l")},
        *[{"id": tid, "name": "Back tab", "outline": rect("tab_w", "tab_h"), "features": [circ("nut_hole", "tab_w/2", "nut_v")]}
          for tid in ("tab_t1", "tab_t2", "tab_b1", "tab_b2")],
    ],
    "folds": [
        {"id": "f_top", "parent": "front", "parent_edge": 0, "child": "top", "child_edge": 0, "angle": 90, "direction": "up", "sequence": 1, "recipe": "fold"},
        {"id": "f_floor", "parent": "front", "parent_edge": 2, "child": "floor", "child_edge": 0, "angle": 90, "direction": "up", "sequence": 2, "recipe": "fold"},
        {"id": "f_left", "parent": "front", "parent_edge": 3, "child": "left", "child_edge": 0, "angle": 90, "direction": "up", "sequence": 3, "recipe": "fold"},
        {"id": "f_right", "parent": "front", "parent_edge": 1, "child": "right", "child_edge": 0, "angle": 90, "direction": "up", "sequence": 4, "recipe": "fold"},
        # tabs on the far edge (edge 2 runs from u = lw back to 0): offset = lw - u_centre - tab_w/2
        *[{"id": f"f_{tid}", "parent": par, "parent_edge": 2, "child": tid, "child_edge": 0, "angle": 90, "direction": "up",
           "sequence": 0, "recipe": "fold", "offset": f"lw - ({uc}) - tab_w/2"}
          for tid, par, uc in (("tab_t1", "top", f"fw - inset - {sx('tx1')} + 2*hinge*t"), ("tab_t2", "top", f"fw - inset - {sx('tx2')} + 2*hinge*t"),
                               ("tab_b1", "floor", f"{sx('bx1')} - inset"), ("tab_b2", "floor", f"{sx('bx2')} - inset"))]],
    "recipes": recipes,
    "hardware": [{"name": "PEM CLS-M3-0 clinch nut (back tabs, pressed from inside)", "qty": 4}],
}

# ---- back plate: flat, no folds; stood up behind the tabs. Sheet (x, y) = (x - t - gap, H - t - gap - z)
bu = lambda x: f"({x}) - t - gap"
bv = lambda z: f"H - t - gap - ({z})"
tab_nuts = [("tx1", "H - hinge*t - nut_v"), ("tx2", "H - hinge*t - nut_v"), ("bx1", "hinge*t + nut_v"), ("bx2", "hinge*t + nut_v")]   # nut centres as folded (checked on the built shell)
back = {
    "_comment": "flacmn deck pro back plate: flat, no folds; 4 M3 x 8 from the back into the shell's tabs. Round 7.",
    "name": "back", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": dict(params),
    "panels": [{"id": "back", "name": "Back plate", "outline": rect("pw", "ph"), "features": [
        *[circ("screw_hole", bu(x), bv(z)) for x, z in tab_nuts],
        circ("rca_hole", bu("rca_x1"), bv("rca_z")), circ("rca_hole", bu("rca_x2"), bv("rca_z")),
        circ("jack_hole", bu("jack_x"), bv("jack_z")),
        {"type": "slot", "length": "usbc_w", "width": "usbc_h", "angle": 0, "at": [bu("usbc_x"), bv("usbc_z")]},
        {"type": "slot", "length": "cord_l", "width": "eth_slot", "angle": 0, "at": [bu("cord1_x"), bv("cord_z")]},
        {"type": "slot", "length": "cord_l", "width": "usb_slot", "angle": 0, "at": [bu("cord2_x"), bv("cord_z")]},
        {"type": "slot", "length": "cord_l", "width": "usb_slot", "angle": 0, "at": [bu("cord3_x"), bv("cord_z")]}]}],
    "folds": [], "recipes": recipes, "hardware": [],
}

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
    {"id": "shell", "name": "Shell (front, top, floor, sides)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "shell.json", "stand": True, "at": ["hinge*t", 0, "H - hinge*t"]},
    {"id": "back", "name": "Back plate (flat, removable)", "source": "make", "process": "laser", "material": "5052-H32 1.0",
     "sheet": "back.json", "stand": True, "at": ["t + gap", "D - t", "H - t - gap"]},
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
    {"id": "screw_back", "name": "ISO 4762 M3 x 8 (from the back)", "source": "library", "library": "grindmn_screw_m3x8", "fastener": True,
     "bodies": [cyl("head_d", "head_h", "y", [0, "D", 0])], "instances": [[x, 0, z] for x, z in tab_nuts]},
    {"id": "clinch_nut", "name": "PEM CLS-M3-0 clinch nut (back tabs)", "source": "buy", "fastener": True,
     "bodies": [cyl(6.4, 1.5, "y", [0, "D - 2*t - 1.5", 0])], "instances": [[x, 0, z] for x, z in tab_nuts]},
    {"id": "screw_pi", "name": "M2.5 x 6 screw (Pi, from below)", "source": "buy", "fastener": True,
     "bodies": [cyl(4.5, 1.0, "z", [0, 0, -1.0])], "instances": [[x, y, 0] for x, y in pi_holes]},
    {"id": "screw_dac", "name": "M2.5 screw (DAC Pro kit, on top)", "source": "buy", "fastener": True,
     "bodies": [cyl(4.5, 1.5, "z", [0, 0, "zht"])], "instances": [[x, y, 0] for x, y in pi_holes]},
]

option = {
    "schema_version": "1.0",
    "name": "Folded shell with back tabs + flat back plate",
    "summary": ("Round 7, from the owner's layout at true scale (241 x 88.5 x 100.5). One folded shell: the front "
                "face in the centre with the top, floor and both sides folded back from it, and two tabs folded in "
                "at the back of the top and two at the back of the floor (8 folds). A flat back plate (no folds) "
                "takes four ISO 4762 M3 x 8 from the back face into clinch nuts in the tabs. The 5in DSI screen is "
                "taped behind the front face; both encoders nut into it and the Ø57 and Ø35 caps sit proud on the "
                "shafts. The Pi + DAC sit on the floor at the back right; USB and Ethernet cords thread out through "
                "three cut-outs in the back plate."),
    "architecture": {
        "mechanism": "flat back plate screwed into the shell's tabs from behind; encoders nutted into the front face; Pi on standoffs on the floor; caps pushed on",
        "layout": "screen left, knobs right on the front; Pi flat at the back right, sockets to the back, USB/Ethernet into the free space; cords out the back panel",
        "load_path": "knobs -> front face -> shell -> feet -> shelf",
        "process": "laser-cut flat; shell 8 hand folds on perforated lines (UNTESTED recipe); back plate flat; clinch nuts pressed"},
    "parts": parts,
    "load_path": ["knob_big", "shell", "feet"],
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
        {"id": "tab_vs_pi", "lhs": "bx2 + tab_w/2 + 2", "op": "<=", "rhs": "px0 - jack_oh",
         "why": "Floor tab clear of the Pi"},
        {"id": "top_tab_vs_jumpers", "lhs": "zht + 2.5 + jumper_h + wire_bend", "op": "<=", "rhs": "H - t - tab_h",
         "why": "Encoder wires stay under the top tabs"},
        {"id": "cords_above_tabs", "lhs": "t + tab_h + 1", "op": "<=", "rhs": "cord_z - eth_slot/2",
         "why": "Cord cut-outs clear the floor tabs"},
        {"id": "cords_apart", "lhs": "cord2_x - cord1_x - cord_l", "op": ">=", "rhs": 6, "why": "Webs between the cord cut-outs"},
        {"id": "cords_left_of_pi", "lhs": "cord3_x + cord_l/2 + 10", "op": "<=", "rhs": "px0 - jack_oh",
         "why": "Cord cut-outs in the free space, clear of the Pi"},
        {"id": "sd_vs_wall", "lhs": "px1 + sd_oh + 1", "op": "<=", "rhs": "W - t",
         "why": "microSD clears the right side"},
        {"id": "rca_vs_plate", "lhs": "py1 + rca_len", "op": "<=", "rhs": "D - t",
         "why": "RCA barrels stop at the back plate"},
        {"id": "va_vs_knob", "lhs": "lens_x0 + va_l + va_w + 1", "op": "<=", "rhs": "kb_x - kb_d/2",
         "why": "Large cap leaves the viewing area clear"},
        {"id": "knobs_apart", "lhs": "kb_x + kb_d/2 + 3", "op": "<=", "rhs": "ks_x - ks_d/2", "why": "Caps 3 mm apart"},
        {"id": "small_knob_in_face", "lhs": "ks_x + ks_d/2", "op": "<=", "rhs": "W - 3", "why": "Small cap inside the face"},
        {"id": "big_knob_in_face", "lhs": "kb_z + kb_d/2", "op": "<=", "rhs": "H - 3", "why": "Large cap inside the face height"},
        {"id": "small_knob_top", "lhs": "ks_z + ks_d/2", "op": "<=", "rhs": "H - 3", "why": "Small cap inside the face height"},
        {"id": "enc_vs_screen", "lhs": "lens_x0 + scr_pcb_w + 1", "op": "<=", "rhs": "kb_x - enc_w/2",
         "why": "Large encoder body clears the screen board"},
        {"id": "enc_vs_pi", "lhs": "t + enc_d + 1", "op": "<=", "rhs": "py0", "why": "Encoders in front of the Pi"},
        {"id": "screen_vs_floor", "lhs": "lens_z0", "op": ">=", "rhs": "t + 1",
         "why": "Screen clears the floor"},
        {"id": "screen_vs_top", "lhs": "lens_z0 + lens_h", "op": "<=", "rhs": "H - t - 1",
         "why": "Screen clears the top"},
        {"id": "screen_vs_side", "lhs": "lens_x0", "op": ">=", "rhs": "t + 1",
         "why": "Screen clears the left side"},
        {"id": "feet_vs_heads", "lhs": "head_h + 1", "op": "<=", "rhs": "feet_h", "why": "Feet stand taller than the screw heads"},
        {"id": "nut_catches", "lhs": "t + 2.5", "op": "<=", "rhs": 7, "why": "Encoder bushing takes the tab, washer and M7 nut"},
    ],
    "allowed_interference": [
        ["dac", "jumpers", "wires on the pass-through header"],
        ["pi4", "standoff", "standoffs under the PCB"],
        ["pad", "pi4", "pad compressed under the PCB"],
        ["pad", "shell", "pad compressed on the floor"],
        ["standoff", "shell", "standoffs on the floor"],
        ["enc_big", "shell", "bushing through the Ø7.4 hole"],
        ["enc_small", "shell", "bushing through the Ø7.4 hole"],
        ["enc_big", "knob_big", "shaft and nut in the cap's counterbore"],
        ["enc_small", "knob_small", "shaft and nut in the cap's counterbore"],
        ["screw_pi", "shell", "screw head under the floor"],
    ],
    "costs_vs_A": [],
    "from_inspiration": [],
    "section_y": "(py0 + py1)/2",
}

OUT.mkdir(parents=True, exist_ok=True)
for name, data in (("params.json", params), ("option.json", option), ("shell.json", shell), ("back.json", back)):
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
