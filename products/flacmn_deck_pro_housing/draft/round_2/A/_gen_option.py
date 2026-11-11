"""Write round-1 option A of flacmn_deck_pro_housing: params.json, option.json, tray.json, cover.json."""
import json, sys
from pathlib import Path

OUT = Path(sys.argv[1])

def P(v, src="chosen", note=None):
    d = {"value": v, "src": src}
    if note:
        d["note"] = note
    return d

# ---- one parameter set, shared by the option and both sheets (same names override)
params = {
    "t": P(1.0, "given", "5052-H32 1.0, the only tested-route material profile"),
    "hinge": P(0.5, "estimated", "bridges bend at mid-thickness until a coupon says otherwise"),
    "allow": P(0.0, "estimated", "flat length taken by a fold; 0 until measured"),
    "gap": P(0.3, "chosen", "cover side to tray clearance"),
    "W": "encF_x + knob_d/2 + 3",
    "D": P(81.0, "chosen", "outside depth: screen zone + slide-in travel + Pi + USB-C overhang"),
    "H": P(46.0, "chosen", "outside height without feet: jumper wires on the DAC header"),
    # Pi 4 + DAC Pro stack
    "pcb_l": P(85.0, "given"), "pcb_w": P(56.0, "given"), "pcb_t": P(1.4, "given"),
    "jack_oh": P(2.7, "estimated", "USB/Ethernet past the Pi's PCB edge"),
    "usbc_oh": P(1.2, "estimated", "USB-C and micro-HDMI past the PCB edge"),
    "sd_oh": P(2.5, "estimated", "microSD card past the PCB edge"),
    "h_so": P(3.0, "chosen", "M2.5 standoff under the Pi = thermal pad gap"),
    "h_hat": P(9.0, "given", "DAC Pro standoffs"), "hat_t": P(1.6, "given"),
    "hat_l": P(65.0, "given"), "hat_w": P(56.5, "given"),
    "hat_parts": P(2.0, "estimated", "small parts on the DAC Pro at the SD end"),
    "jumper_h": P(14.0, "estimated", "Dupont housing on the pass-through header"),
    "wire_bend": P(6.0, "estimated", "jumper wire bend above the housing"),
    "rca_len": P(9.0, "given", "projects/rpi_dac_pro: barrels past the HAT edge"),
    "px0": "t + gap + jack_oh", "px1": "px0 + pcb_l",
    "py1": "D - t - usbc_oh", "py0": "py1 - pcb_w",
    "zp": "t + h_so", "zpt": "zp + pcb_t", "zh": "zpt + h_hat", "zht": "zh + hat_t",
    "slide": "py1 + rca_len - (D - t) + 0.5",
    # rear openings (board sockets)
    "rca_x1": "px1 - 18.36", "rca_x2": "px1 - 32.98", "rca_z": "zht + 6.5", "rca_hole": 8.6,
    "jack_x": "px1 - 51.8", "jack_z": "zht + 3", "jack_hole": 6.5,
    "usbc_x": "px1 - 11.2", "usbc_z": "zpt + 1.6", "usbc_w": 11.0, "usbc_h": 5.5,
    # left openings
    "eth_y": "py1 - 45.75", "usb3_y": "py1 - 27", "usb2_y": "py1 - 9",
    "eth_w": 16.5, "eth_h": 14.5, "usb_w": 15.5, "usb_h": 16.5, "jack_z0": "zpt - 0.5",
    # screen and knobs
    "scr_l": P(58.0, "given"), "scr_h": P(35.0, "given"),
    "scr_d": P(11.0, "estimated", "module ~5 + its connector ~6"),
    "scr_x0": 5.0, "scr_z": "H/2",
    "win_w": P(42.0, "given"), "win_h": P(32.0, "given"),
    "win_x": "scr_x0 + scr_l/2", "scr_hole_dx": P(53.0, "estimated"), "scr_hole_dz": P(30.0, "estimated"),
    "enc_w": P(12.5, "estimated"), "enc_h": P(13.4, "estimated"), "enc_d": P(10.1, "estimated", "body 6.6 + pins"),
    "enc_hole": P(7.4, "given"), "enc_tab_r": P(7.5, "estimated", "anti-turn tab offset"), "enc_tab_d": 2.4,
    "encF_x": "win_x + win_w/2 + 3 + knob_d/2", "encF_z": "H/2",
    "encS_y": "D/2", "encS_z": "H/2",
    "knob_d": P("H", "given", "owner: diameter = deck height"), "knob_h": P(5.0, "given", "owner: 5 thick"),
    "bush_out": P(6.0, "estimated", "bushing 7 past the body, less the wall"), "knob_gap": 0.5,
    # microSD + Wi-Fi slot in the right side
    "slot_y0": 22.0, "slot_y1": 60.0, "slot_z0": 2.5, "slot_z1": 10.5,
    # cover fixing
    "tab_w": 10.0, "tab_h": 12.0, "nut_hole": P(4.22, "given", "PEM CLS-M3-0 mounting hole"), "screw_hole": 3.4, "top_gap": 0.2,
    "feet_h": P(4.0, "estimated"), "feet_d": 10.0,
    "soc_x": "px1 - 29", "soc_y": "py1 - 32",
}

# ---- tray: base + front + rear walls, each wall with two top tabs for the cover screws
tp = {
    "bw": "W - 2*t - 2*gap", "bd": "D - 2*hinge*t - allow",
    "wh": "H - t - top_gap - hinge*t - allow",
    "x_off": "t + gap", "inset": "(1 - hinge)*t", "ww": "bw - 2*inset",
}

def front_u(x):           # world x -> front wall local u
    return f"bw - inset - ({x} - x_off)"

def rear_u(x):
    return f"({x}) - x_off - inset"

def wall_v(z):
    return f"({z}) - hinge*t"

rect = lambda w, h: [[0, 0], [w, 0], [w, h], [0, h]]

tray = {
    "_comment": "flacmn deck pro tray: base, front wall (screen + front knob), rear wall (USB-C, RCA, jack). Generated for draft round 1.",
    "name": "tray", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **tp},
    "panels": [
        {"id": "base", "name": "Base", "outline": rect("bw", "bd"), "features": [
            # Pi mounting holes (M2.5 from below) on the 58 x 49 pattern, SD end at +x
            *[{"type": "circle", "d": 2.9, "at": [f"px1 - {hx} - x_off", f"py1 - {hy} - hinge*t"]}
              for hx in (3.5, 61.5) for hy in (3.5, 52.5)]]},
        {"id": "front", "name": "Front wall", "outline": rect("ww", "wh"), "features": [
            {"type": "rect", "size": ["win_w", "win_h"], "at": [front_u("win_x"), wall_v("scr_z")]},
            *[{"type": "circle", "d": 2.4, "at": [front_u(f"win_x + {sx}*scr_hole_dx/2"), wall_v(f"scr_z + {sz}*scr_hole_dz/2")]}
              for sx in (-1, 1) for sz in (-1, 1)],
            {"type": "circle", "d": "enc_hole", "at": [front_u("encF_x"), wall_v("encF_z")]},
            {"type": "circle", "d": "enc_tab_d", "at": [front_u("encF_x"), wall_v("encF_z + enc_tab_r")]}]},
        {"id": "rear", "name": "Rear wall", "outline": rect("ww", "wh"), "features": [
            {"type": "circle", "d": "rca_hole", "at": [rear_u("rca_x1"), wall_v("rca_z")]},
            {"type": "circle", "d": "rca_hole", "at": [rear_u("rca_x2"), wall_v("rca_z")]},
            {"type": "circle", "d": "jack_hole", "at": [rear_u("jack_x"), wall_v("jack_z")]},
            {"type": "slot", "length": "usbc_w", "width": "usbc_h", "angle": 0, "at": [rear_u("usbc_x"), wall_v("usbc_z")]}]},
    ],
    "folds": [
        {"id": "f_front", "parent": "base", "parent_edge": 0, "child": "front", "child_edge": 0,
         "angle": 90, "direction": "up", "sequence": 2, "recipe": "fold"},
        {"id": "f_rear", "parent": "base", "parent_edge": 2, "child": "rear", "child_edge": 0,
         "angle": 90, "direction": "up", "sequence": 2, "recipe": "fold"},
    ],
    "recipes": {"fold": {"_comment": "Starting guess for 1.0 mm 5052-H32. UNTESTED until a coupon holds.",
                         "method": "slots", "slot_length": 8.0, "slot_width": 0.5, "bridge": 1.5,
                         "end_clearance": 2.0, "hinge": "hinge", "allowance": "allow"}},
    "hardware": [{"name": "PEM CLS-M3-0 clinch nut (in the tabs, from inside)", "qty": 4}, {"name": "M2.5 x 6 screw (Pi, from below)", "qty": 4},
                 {"name": "M2 x 6 screw + nut + 2.5 spacer (screen)", "qty": 4}],
}
for wall in ("front", "rear"):
    for edge, off in ((1, "wh - tab_h"), (3, 0)):
        tid = f"{wall}_tab_{'a' if edge == 1 else 'b'}"
        tray["panels"].append({"id": tid, "name": f"{wall} tab", "outline": rect("tab_h", "tab_w"),
                               "features": [{"type": "circle", "d": "nut_hole", "at": ["tab_h/2", "tab_w/2"]}]})
        tray["folds"].append({"id": f"f_{tid}", "parent": wall, "parent_edge": edge, "child": tid, "child_edge": 0,
                              "angle": 90, "direction": "up", "sequence": 1, "recipe": "fold", "offset": off})

# ---- cover: top + left side (USB/Ethernet) + right side (side knob, SD/Wi-Fi slot), folded down
cp = {"cw": "W - 2*hinge*t - allow", "sh": "H - hinge*t - allow"}

def side_v(z):            # world z -> side local v (runs down from the top fold)
    return f"H - hinge*t - ({z})"

def right_u(y):
    return f"D - ({y})"

def left_u(y):
    return f"{y}"

screw_ys = ["0.5 + tab_w/2", "D - 0.5 - tab_w/2"]
screw_z = "H - t - top_gap - tab_h/2"
cover = {
    "_comment": "flacmn deck pro cover: top, left side (USB x4 + Ethernet), right side (side knob, microSD/Wi-Fi slot). Generated for draft round 1.",
    "name": "cover", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **cp},
    "panels": [
        {"id": "top", "name": "Top", "outline": rect("cw", "D"), "features": []},
        {"id": "left", "name": "Left side", "outline": rect("D", "sh"), "features": [
            {"type": "rect", "size": ["eth_w", "eth_h"], "at": [left_u("eth_y"), side_v("jack_z0 + eth_h/2")]},
            {"type": "rect", "size": ["usb_w", "usb_h"], "at": [left_u("usb3_y"), side_v("jack_z0 + usb_h/2")]},
            {"type": "rect", "size": ["usb_w", "usb_h"], "at": [left_u("usb2_y"), side_v("jack_z0 + usb_h/2")]},
            *[{"type": "circle", "d": "screw_hole", "at": [left_u(y), side_v(screw_z)]} for y in screw_ys]]},
        {"id": "right", "name": "Right side", "outline": rect("D", "sh"), "features": [
            {"type": "circle", "d": "enc_hole", "at": [right_u("encS_y"), side_v("encS_z")]},
            {"type": "circle", "d": "enc_tab_d", "at": [right_u("encS_y"), side_v("encS_z + enc_tab_r")]},
            {"type": "rect", "size": ["slot_y1 - slot_y0", "slot_z1 - slot_z0"],
             "at": [right_u("(slot_y0 + slot_y1)/2"), side_v("(slot_z0 + slot_z1)/2")]},
            *[{"type": "circle", "d": "screw_hole", "at": [right_u(y), side_v(screw_z)]} for y in screw_ys]]},
    ],
    "folds": [
        {"id": "f_right", "parent": "top", "parent_edge": 1, "child": "right", "child_edge": 0,
         "angle": 90, "direction": "down", "sequence": 1, "recipe": "fold"},
        {"id": "f_left", "parent": "top", "parent_edge": 3, "child": "left", "child_edge": 0,
         "angle": 90, "direction": "down", "sequence": 1, "recipe": "fold"},
    ],
    "recipes": tray["recipes"],
    "hardware": [{"name": "M3 x 6 button screw", "qty": 4}],
}

# ---- option.json
def box(sx, sy, sz, cx, cy, z):
    return {"type": "box", "size": [sx, sy, sz], "at": [cx, cy, z]}

parts = [
    {"id": "tray", "name": "Tray (base + front + rear)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "tray.json", "at": ["t + gap", 0.5, 0]},
    {"id": "cover", "name": "Cover (top + sides)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "cover.json", "at": [0.5, 0, "H - t"]},
    {"id": "pi4", "name": "Raspberry Pi 4 B", "source": "buy", "bodies": [
        box("pcb_l", "pcb_w", "pcb_t", "px0 + pcb_l/2", "py0 + pcb_w/2", "zp"),
        box("17.4 + jack_oh", "usb2_y - eth_y + 15", 16, "px0 - jack_oh + (17.4 + jack_oh)/2", "(eth_y + usb2_y)/2", "zpt")]},
    {"id": "dac", "name": "Raspberry Pi DAC Pro", "source": "library", "library": "rpi_dac_pro", "bodies": [
        box("hat_l", "hat_w", "hat_t", "px1 - hat_l/2", "py1 - hat_w/2 + 0.25", "zh"),
        box(27.6, 14, 13, "px1 - 25.8", "py1 - 7", "zht"),
        {"type": "cyl", "d": 8, "h": "rca_len", "axis": "y", "at": ["rca_x1", "py1", "rca_z"]},
        {"type": "cyl", "d": 8, "h": "rca_len", "axis": "y", "at": ["rca_x2", "py1", "rca_z"]},
        box(8, 12, 6, "jack_x", "py1 - 6", "zht")]},
    {"id": "jumpers", "name": "Jumper wires on the pass-through header (screen + knobs)", "source": "buy", "bodies": [
        box(51, 5, "2.5 + jumper_h", "px1 - 32.5", "py0 + 3.5", "zht")]},
    {"id": "standoff", "name": "M2.5 standoff 3 mm (Pi)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 5, "h": "h_so", "at": [0, 0, "t"]}],
     "instances": [[f"px1 - {hx}", f"py1 - {hy}", 0] for hx in (3.5, 61.5) for hy in (3.5, 52.5)]},
    {"id": "pad", "name": "Thermal pad 15 x 15 x 3 under the processor", "source": "buy", "bodies": [
        box(15, 15, "h_so", "soc_x", "soc_y", "t")]},
    {"id": "screen", "name": "Waveshare 2in LCD module", "source": "buy", "bodies": [
        box("scr_l", "scr_d", "scr_h", "scr_x0 + scr_l/2", "t + scr_d/2", "scr_z - scr_h/2")]},
    {"id": "enc_front", "name": "PEC11R encoder, front", "source": "library", "library": "encoder_pec11r", "bodies": [
        box("enc_w", "enc_d", "enc_h", "encF_x", "t + enc_d/2", "encF_z - enc_h/2"),
        {"type": "cyl", "d": 6, "h": "20 + t", "axis": "y", "at": ["encF_x", -20, "encF_z"]}]},
    {"id": "enc_side", "name": "PEC11R encoder, side", "source": "library", "library": "encoder_pec11r", "bodies": [
        box("enc_d", "enc_w", "enc_h", "W - t - enc_d/2", "encS_y", "encS_z - enc_h/2"),
        {"type": "cyl", "d": 6, "h": "20 + t", "axis": "x", "at": ["W - t", "encS_y", "encS_z"]}]},
    {"id": "knob_front", "name": "Knob cap, front (46 x 5)", "source": "buy", "bodies": [
        {"type": "cyl", "d": "knob_d", "h": "knob_h", "axis": "y", "at": ["encF_x", "-(bush_out + knob_gap + knob_h)", "encF_z"]}]},
    {"id": "knob_side", "name": "Knob cap, side (46 x 5)", "source": "buy", "bodies": [
        {"type": "cyl", "d": "knob_d", "h": "knob_h", "axis": "x", "at": ["W + bush_out + knob_gap", "encS_y", "encS_z"]}]},
    {"id": "feet", "name": "Rubber foot", "source": "buy",
     "bodies": [{"type": "cyl", "d": "feet_d", "h": "feet_h", "at": [0, 0, "-feet_h"]}],
     "instances": [["10", "10", 0], ["W - 10", "10", 0], ["10", "D - 10", 0], ["W - 10", "D - 10", 0]]},
    {"id": "screw_m3", "name": "M3 x 6 button screw (cover)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 5.7, "h": 1.65, "axis": "x", "at": [-1.65, 0, 0]}],
     "instances": [[0, y, "H - t - top_gap - tab_h/2"] for y in ("0.5 + tab_w/2", "D - 0.5 - tab_w/2")]
                  + [["W + 1.65", y, "H - t - top_gap - tab_h/2"] for y in ("0.5 + tab_w/2", "D - 0.5 - tab_w/2")]},
    {"id": "clinch_nut", "name": "PEM CLS-M3-0 clinch nut (tray tabs)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 6.4, "h": 1.5, "axis": "x", "at": [0, 0, 0]}],
     "instances": [["t + gap + 1", y, "H - t - top_gap - tab_h/2"] for y in ("0.5 + tab_w/2", "D - 0.5 - tab_w/2")]
                  + [["W - t - gap - 2.5", y, "H - t - top_gap - tab_h/2"] for y in ("0.5 + tab_w/2", "D - 0.5 - tab_w/2")]},
    {"id": "screw_pi", "name": "M2.5 x 6 screw (Pi, from below)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 4.5, "h": 1.5, "at": [0, 0, -1.5]}],
     "instances": [[f"px1 - {hx}", f"py1 - {hy}", 0] for hx in (3.5, 61.5) for hy in (3.5, 52.5)]},
    {"id": "screw_dac", "name": "M2.5 x 5 screw (DAC Pro, on top)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 4.5, "h": 1.5, "at": [0, 0, "zht"]}],
     "instances": [[f"px1 - {hx}", f"py1 - {hy}", 0] for hx in (3.5, 61.5) for hy in (3.5, 52.5)]},
    {"id": "screen_fix", "name": "M2 x 6 screw + nut + 2.5 spacer (screen), sets of 3", "source": "buy", "fastener": True, "qty": 12,
     "bodies": [{"type": "cyl", "d": 3.8, "h": 1.2, "axis": "y", "at": [0, -1.2, 0]}],
     "instances": [[f"win_x + {sx}*scr_hole_dx/2", 0, f"scr_z + {sz}*scr_hole_dz/2"] for sx in (-1, 1) for sz in (-1, 1)]},
]

option = {
    "schema_version": "1.0",
    "name": "Two folded shells: tray + U-cover",
    "summary": ("Round 2: 46 x 5 knob caps. Two hand-folded 1.0 mm aluminium sheets. The tray (base, front wall with screen and knob, rear wall "
                "with USB-C, RCA and jack) carries everything; the U-cover (top and both sides) drops over it and "
                "takes 4 screws into clinch nuts in the tray's tabs. USB and Ethernet face the left side; the side knob and "
                "a Wi-Fi slot are on the right side; the microSD is reached with the cover off. Processor heat goes through a pad under the Pi into the base."),
    "architecture": {
        "mechanism": "Pi + DAC stack slides rearward on the base until the RCA barrels pass the rear wall, then 4 screws from below; cover drops on, 4 side screws",
        "layout": "Pi flat, USB-C long side at the rear, USB/Ethernet edge flush with the left side, SD end at the right; screen and front encoder in the 12 mm zone behind the front wall",
        "load_path": "knobs -> walls -> base -> feet -> shelf",
        "process": "laser-cut flat, 6 + 2 hand folds on perforated lines (UNTESTED recipe)"},
    "parts": parts,
    "load_path": ["knob_front", "tray", "feet"],
    "dims": [
        {"view": "section", "dir": "v", "a": "zp", "b": "zht", "at": "W + 6", "text": "stack"},
        {"view": "right", "dir": "h", "a": "py0", "b": "py1", "at": -8, "param": "pcb_w"},
        {"view": "right", "dir": "h", "a": "t", "b": "py0", "at": -14},
        {"view": "top", "dir": "h", "a": "scr_x0", "b": "scr_x0 + scr_l", "at": -8, "param": "scr_l"},
        {"view": "top", "dir": "h", "a": "encF_x", "b": "W", "at": -14},
        {"view": "right", "dir": "v", "a": 0, "b": "encS_z", "at": "D + 8", "param": "encS_z"},
    ],
    "fit": [
        {"id": "jumpers_roof", "lhs": "zht + 2.5 + jumper_h + wire_bend", "op": "<=", "rhs": "H - t",
         "why": "Jumper housings on the pass-through header and their wire bends clear the top"},
        {"id": "rca_proud", "lhs": "py1 + rca_len - D", "op": ">=", "rhs": 5,
         "why": "RCA barrels stand at least 5 proud of the rear wall for the plugs"},
        {"id": "slide_room", "lhs": "py0 - slide", "op": ">=", "rhs": "t + scr_d + 0.5",
         "why": "The stack can sit forward by the slide-in travel without hitting the screen"},
        {"id": "enc_front_vs_pi", "lhs": "t + enc_d + 2", "op": "<=", "rhs": "py0",
         "why": "Front encoder body and pins clear the Pi's front edge"},
        {"id": "enc_side_beside_pi", "lhs": "W - t - enc_d", "op": ">=", "rhs": "px1 + sd_oh + 2",
         "why": "Side encoder body sits beside the Pi and its microSD card"},
        {"id": "side_knob_in_height", "lhs": "encS_z + knob_d/2", "op": "<=", "rhs": "H",
         "why": "Side knob cap within the deck's height"},
        {"id": "side_knob_vs_rear", "lhs": "encS_y + knob_d/2", "op": "<=", "rhs": "D - 3",
         "why": "Side knob cap inside the side face"},
        {"id": "knob_shaft", "lhs": "bush_out + knob_gap + knob_h", "op": "<=", "rhs": "20 - t",
         "why": "Shaft (20 past the body) is long enough for the cap; cut to length"},
        {"id": "enc_side_vs_header", "lhs": "encS_y - enc_w/2", "op": ">=", "rhs": "py0 + 6 + 2",
         "why": "Side encoder clears the jumper row on the header"},
        {"id": "enc_side_roof", "lhs": "encS_z + enc_h/2", "op": "<=", "rhs": "H - t - 1",
         "why": "Side encoder body under the top"},
        {"id": "enc_front_vs_screen", "lhs": "encF_x - enc_w/2", "op": ">=", "rhs": "scr_x0 + scr_l + 1",
         "why": "Front encoder body clears the screen module"},
        {"id": "knob_vs_window", "lhs": "encF_x - knob_d/2", "op": ">=", "rhs": "win_x + win_w/2 + 3",
         "why": "Front knob cap clears the screen window"},
        {"id": "knob_vs_edge", "lhs": "encF_x + knob_d/2", "op": "<=", "rhs": "W - 3",
         "why": "Front knob cap inside the front face"},
        {"id": "side_knob_vs_front", "lhs": "encS_y - knob_d/2", "op": ">=", "rhs": 3,
         "why": "Side knob cap inside the side face"},
        {"id": "screen_in_face", "lhs": "scr_z + scr_h/2", "op": "<=", "rhs": "H - t - 1",
         "why": "Screen module fits the front wall height"},
        {"id": "screen_over_base", "lhs": "scr_z - scr_h/2", "op": ">=", "rhs": "t + 1",
         "why": "Screen module clears the base"},
        {"id": "pi_fits_width", "lhs": "px1 + sd_oh", "op": "<=", "rhs": "W - t - 0.3",
         "why": "Pi with the SD card fits between the sides"},
        {"id": "usbc_under_rca", "lhs": "usbc_z + usbc_h/2 + 3", "op": "<=", "rhs": "rca_z - rca_hole/2",
         "why": "USB-C opening and RCA holes keep a 3 mm web"},
        {"id": "tabs_over_usb", "lhs": "zpt + 16 + 2", "op": "<=", "rhs": "H - t - top_gap - tab_h",
         "why": "Cover-screw tabs sit above the USB jacks"},
        {"id": "nut_vs_screen", "lhs": "t + gap + 1 + 1.5 + 0.5", "op": "<=", "rhs": "scr_x0",
         "why": "Front-left clinch nut clears the screen module"},
        {"id": "nut_catches", "lhs": "t + 2.5", "op": "<=", "rhs": 7,
         "why": "Encoder bushing (7) takes the wall, washer and M7 nut"},
    ],
    "allowed_interference": [
        ["dac", "tray", "RCA barrels and jack nose pass through their rear-wall holes"],
        ["enc_front", "tray", "bushing and shaft pass through the front-wall hole"],
        ["enc_side", "cover", "bushing and shaft pass through the right-side hole"],
        ["pi4", "standoff", "standoffs under the PCB"],
        ["pad", "pi4", "pad compressed under the PCB"],
        ["pad", "tray", "pad compressed on the base"],
        ["enc_front", "knob_front", "cap on the shaft"],
        ["enc_side", "knob_side", "cap on the shaft"],
        ["standoff", "tray", "standoffs on the base"],
        ["dac", "jumpers", "jumpers on the pass-through header"],
        ["clinch_nut", "tray", "nut clinched into the tab"],
        ["screen", "screen_fix", "screws through the module"],
    ],
    "costs_vs_A": [],
    "from_inspiration": [],
    "section_y": "encS_y",
}

OUT.mkdir(parents=True, exist_ok=True)
for name, data in (("params.json", params), ("option.json", option), ("tray.json", tray), ("cover.json", cover)):
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
