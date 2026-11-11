"""Write round-4 option A of flacmn_deck_pro_housing: params.json, option.json, shell.json, plate.json.

Shell: top + 4 walls folded down, two short inward flanges at the bottom (screws from below).
Plate: the underside; carries the Pi stack and both encoders on two fold-up tabs, so the 5 mm
caps sit flush in the walls. Nothing passes through a wall, so the plate lifts in from below."""
import json, sys
from pathlib import Path

OUT = Path(sys.argv[1])

def P(v, src="chosen", note=None):
    d = {"value": v, "src": src}
    if note:
        d["note"] = note
    return d

params = {
    "t": P(1.0, "given", "5052-H32 1.0, the only material profile"),
    "hinge": P(0.5, "estimated", "bridges bend at mid-thickness until a coupon says otherwise"),
    "allow": P(0.0, "estimated", "flat length taken by a fold; 0 until measured"),
    "corner": P(0.3, "chosen", "gap between neighbouring walls at a corner"),
    "gap": P(0.3, "chosen", "plate edge to wall inner face"),
    "rim": P(3.5, "given", "owner 2026-11-11: knob = height - 7 (3.5 rim in 1 mm folded sheet)"),
    "H": P(46.0, "given", "owner: 46 tall"),
    "knob_d": "H - 2*rim", "knob_h": P(5.0, "given", "owner: 5 thick, flush"),
    "knob_clear": 0.5, "knob_hole": "knob_d + 2*knob_clear",
    "W": P(104.0, "chosen", "side encoder body beside the Pi's microSD end"),
    "D": P(83.0, "chosen", "outside depth: screen zone + left flange + Pi + recessed rear sockets"),
    # Pi 4 + DAC Pro stack (plate top at z = t)
    "pcb_l": P(85.0, "given"), "pcb_w": P(56.0, "given"), "pcb_t": P(1.4, "given"),
    "jack_oh": P(2.7, "estimated", "USB/Ethernet past the Pi's PCB edge"),
    "usbc_oh": P(1.2, "estimated", "USB-C and micro-HDMI past the PCB edge"),
    "sd_oh": P(2.5, "estimated", "microSD card past the PCB edge"),
    "h_so": P(3.0, "chosen", "M2.5 standoff under the Pi = thermal pad gap"),
    "h_hat": P(9.0, "given", "DAC Pro standoffs"), "hat_t": P(1.6, "given"),
    "hat_l": P(65.0, "given"), "hat_w": P(56.5, "given"),
    "jumper_h": P(14.0, "estimated", "Dupont housing on the pass-through header"),
    "wire_bend": P(6.0, "estimated", "jumper wire bend above the housing"),
    "rca_len": P(9.0, "given", "projects/rpi_dac_pro: barrels past the HAT edge"),
    "sock_recess": P(1.0, "chosen", "socket tips stop this far inside the rear wall"),
    "px0": "t + gap + jack_oh", "px1": "px0 + pcb_l",
    "py1": "D - t - sock_recess - rca_len", "py0": "py1 - pcb_w",
    "zp": "t + h_so", "zpt": "zp + pcb_t", "zh": "zpt + h_hat", "zht": "zh + hat_t",
    # rear openings: plugs reach in to the recessed sockets
    "rca_x1": "px1 - 18.36", "rca_x2": "px1 - 32.98", "rca_z": "zht + 6.5",
    "rca_hole": P(13.0, "estimated", "RCA plug shell passes; check with your leads"),
    "jack_x": "px1 - 51.8", "jack_z": "zht + 3", "jack_hole": P(10.0, "estimated", "slim 3.5 mm plug body passes"),
    "usbc_x": "px1 - 11.2", "usbc_z": "zpt + 1.6",
    "usbc_w": P(13.0, "estimated", "USB-C overmold passes"), "usbc_h": P(7.5, "estimated"),
    # left openings: jacks flush behind the wall
    "eth_y": "py1 - 45.75", "usb3_y": "py1 - 27", "usb2_y": "py1 - 9",
    "eth_w": 16.5, "eth_h": 14.5, "usb_w": 15.5, "usb_h": 16.5, "jack_z0": "zpt - 0.5",
    # screen (VHB tape to the front wall) and encoders (on plate tabs)
    "scr_l": P(58.0, "given"), "scr_h": P(35.0, "given"),
    "scr_d": P(11.0, "estimated", "module ~5 + its connector ~6"),
    "win_w": P(42.0, "given"), "win_h": P(32.0, "given"),
    "win_x": "(encF_x - knob_d/2)/2", "scr_z": "H/2",
    "enc_w": P(12.5, "estimated"), "enc_h": P(13.4, "estimated"), "enc_d": P(10.1, "estimated", "body 6.6 + pins"),
    "enc_hole": P(7.4, "given"), "enc_tab_r": P(7.5, "estimated", "anti-turn tab offset"), "enc_tab_d": 2.4,
    "bush_out": P(6.0, "estimated", "bushing 7 past the body, less the tab"),
    "encF_x": "W - rim - knob_d/2", "encF_z": "H/2",
    "encS_y": "D/2", "encS_z": "H/2",
    "cap_back": "bush_out + knob_clear", "cap_front": "cap_back + knob_h",
    # fixing: two M3 screws from below into clinch nuts on the shell flanges
    "fw": 8.0, "fl_left": 13.0, "fl_right": 20.0,
    "nut_hole": P(4.22, "given", "PEM CLS-M3-0 mounting hole"), "screw_hole": 3.4,
    "wifi_x0": 45.0, "wifi_x1": 80.0, "wifi_y0": 22.0, "wifi_y1": 28.0,
    "feet_h": P(4.0, "estimated"), "feet_d": 10.0,
    "soc_x": "px1 - 29", "soc_y": "py1 - 32",
}

rect = lambda w, h: [[0, 0], [w, 0], [w, h], [0, h]]
recipes = {"fold": {"_comment": "Starting guess for 1.0 mm 5052-H32. UNTESTED until a coupon holds.",
                    "method": "slots", "slot_length": 8.0, "slot_width": 0.5, "bridge": 1.5,
                    "end_clearance": 2.0, "hinge": "hinge", "allowance": "allow"}}

# ---- shell: placed at [hinge*t, hinge*t, H - t]; walls hang down from the top
sp = {"tw": "W - 2*hinge*t - allow", "td": "D - 2*hinge*t - allow", "inset": "(1 - hinge)*t + corner",
      "fwid": "tw - 2*inset", "swid": "td - 2*inset", "wl": "H - 2*t - allow",
      "ly_left_hole": "inset + 1 + fl_left/2", "ly_right_hole": "td - inset - 1 - fl_right/2"}
v = lambda z: f"H - hinge*t - ({z})"                      # world z -> wall v (down from the top fold)
fu = lambda x: f"tw - inset - ({x}) + hinge*t"            # world x -> front wall u
ru = lambda x: f"({x}) - hinge*t - inset"                 # world x -> rear wall u
lu = lambda y: f"({y}) - hinge*t - inset"                 # world y -> left wall u
gu = lambda y: f"td - inset - ({y}) + hinge*t"            # world y -> right wall u
knob_front = [{"type": "circle", "d": "enc_hole", "at": [fu("encF_x"), v("encF_z")]},
              {"type": "circle", "d": "enc_tab_d", "at": [fu("encF_x"), v("encF_z + enc_tab_r")]}]
shell = {
    "_comment": "flacmn deck pro shell: top + 4 walls folded down; short inward flanges at the bottom of the side walls take the plate screws; the encoders panel-mount in the front and right walls. Round 4.",
    "name": "shell", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **sp},
    "panels": [
        {"id": "top", "name": "Top", "outline": rect("tw", "td")},
        {"id": "front", "name": "Front wall", "outline": rect("fwid", "wl"), "features": [
            {"type": "rect", "size": ["win_w", "win_h"], "at": [fu("win_x"), v("scr_z")]}, *knob_front]},
        {"id": "rear", "name": "Rear wall", "outline": rect("fwid", "wl"), "features": [
            {"type": "circle", "d": "rca_hole", "at": [ru("rca_x1"), v("rca_z")]},
            {"type": "circle", "d": "rca_hole", "at": [ru("rca_x2"), v("rca_z")]},
            {"type": "circle", "d": "jack_hole", "at": [ru("jack_x"), v("jack_z")]},
            {"type": "slot", "length": "usbc_w", "width": "usbc_h", "angle": 0, "at": [ru("usbc_x"), v("usbc_z")]}]},
        {"id": "left", "name": "Left wall", "outline": rect("swid", "wl"), "features": [
            {"type": "rect", "size": ["eth_w", "eth_h"], "at": [lu("eth_y"), v("jack_z0 + eth_h/2")]},
            {"type": "rect", "size": ["usb_w", "usb_h"], "at": [lu("usb3_y"), v("jack_z0 + usb_h/2")]},
            {"type": "rect", "size": ["usb_w", "usb_h"], "at": [lu("usb2_y"), v("jack_z0 + usb_h/2")]}]},
        {"id": "right", "name": "Right wall", "outline": rect("swid", "wl"), "features": [
            {"type": "circle", "d": "enc_hole", "at": [gu("encS_y"), v("encS_z")]},
            {"type": "circle", "d": "enc_tab_d", "at": [gu("encS_y"), v("encS_z + enc_tab_r")]}]},
        {"id": "left_flange", "name": "Left flange", "outline": rect("fl_left", "fw"), "features": [
            {"type": "circle", "d": "nut_hole", "at": ["fl_left/2", "fw/2"]}]},
        {"id": "right_flange", "name": "Right flange", "outline": rect("fl_right", "fw"), "features": [
            {"type": "circle", "d": "nut_hole", "at": ["fl_right/2", "fw/2"]}]},
    ],
    "folds": [
        {"id": "f_front", "parent": "top", "parent_edge": 0, "child": "front", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold"},
        {"id": "f_right", "parent": "top", "parent_edge": 1, "child": "right", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold"},
        {"id": "f_rear", "parent": "top", "parent_edge": 2, "child": "rear", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold"},
        {"id": "f_left", "parent": "top", "parent_edge": 3, "child": "left", "child_edge": 0, "angle": 90, "direction": "down", "sequence": 2, "recipe": "fold"},
        {"id": "f_left_flange", "parent": "left", "parent_edge": 2, "child": "left_flange", "child_edge": 0, "angle": 90,
         "direction": "down", "sequence": 1, "recipe": "fold", "offset": "swid - fl_left - 1"},
        {"id": "f_right_flange", "parent": "right", "parent_edge": 2, "child": "right_flange", "child_edge": 0, "angle": 90,
         "direction": "down", "sequence": 1, "recipe": "fold", "offset": "swid - fl_right - 1"},
    ],
    "recipes": recipes,
    "hardware": [{"name": "PEM CLS-M3-0 clinch nut (flanges, pressed from inside)", "qty": 2}],
}

# ---- plate: placed at [t + gap, t + gap, 0]; local = world - (t + gap)
pp = {"o": "t + gap", "plw": "W - 2*(t + gap)", "pld": "D - 2*(t + gap)"}
L = lambda e: f"({e}) - o"
pi_holes = [(f"px1 - {hx}", f"py1 - {hy}") for hx in (3.5, 61.5) for hy in (3.5, 52.5)]
screw_left = ("hinge*t + fw/2", "hinge*t + ly_left_hole")
screw_right = ("W - hinge*t - fw/2", "hinge*t + ly_right_hole")
plate = {
    "_comment": "flacmn deck pro base plate: carries the Pi stack; lifts into the shell from below. Round 4.",
    "name": "plate", "material": "5052-H32_1.0", "manufacturing": "generic_untested", "dims": "outside",
    "params": {**params, **sp, **pp},
    "panels": [
        {"id": "plate", "name": "Base plate", "outline": rect("plw", "pld"),
         "features": [
            *[{"type": "circle", "d": 2.9, "at": [L(x), L(y)]} for x, y in pi_holes],
            *[{"type": "circle", "d": "screw_hole", "at": [L(x), L(y)]} for x, y in (screw_left, screw_right)],
            {"type": "rect", "size": ["wifi_x1 - wifi_x0", "wifi_y1 - wifi_y0"],
             "at": [L("(wifi_x0 + wifi_x1)/2"), L("(wifi_y0 + wifi_y1)/2")]}]},
    ],
    "folds": [],
    "recipes": recipes,
    "hardware": [{"name": "M3 x 6 low-head screw (plate to shell flanges, from below)", "qty": 2},
                 {"name": "M2.5 x 6 screw (Pi, from below)", "qty": 4}],
}

def box(sx, sy, sz, cx, cy, z):
    return {"type": "box", "size": [sx, sy, sz], "at": [cx, cy, z]}

parts = [
    {"id": "shell", "name": "Shell (top + 4 walls)", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "shell.json", "at": ["hinge*t", "hinge*t", "H - t"]},
    {"id": "plate", "name": "Base plate with encoder tabs", "source": "make", "process": "fold", "material": "5052-H32 1.0",
     "sheet": "plate.json", "at": ["t + gap", "t + gap", 0]},
    {"id": "pi4", "name": "Raspberry Pi 4 B", "source": "buy", "bodies": [
        box("pcb_l", "pcb_w", "pcb_t", "px0 + pcb_l/2", "py0 + pcb_w/2", "zp"),
        box("17.4 + jack_oh", "usb2_y - eth_y + 15", 16, "px0 - jack_oh + (17.4 + jack_oh)/2", "(eth_y + usb2_y)/2", "zpt")]},
    {"id": "dac", "name": "Raspberry Pi DAC Pro", "source": "library", "library": "rpi_dac_pro", "bodies": [
        box("hat_l", "hat_w", "hat_t", "px1 - hat_l/2", "py1 - hat_w/2 + 0.25", "zh"),
        box(27.6, 14, 13, "px1 - 25.8", "py1 - 7", "zht"),
        {"type": "cyl", "d": 8, "h": "rca_len", "axis": "y", "at": ["rca_x1", "py1", "rca_z"]},
        {"type": "cyl", "d": 8, "h": "rca_len", "axis": "y", "at": ["rca_x2", "py1", "rca_z"]},
        box(8, 12, 6, "jack_x", "py1 - 6", "zht")]},
    {"id": "jumpers", "name": "Jumper wires on the pass-through header", "source": "buy", "bodies": [
        box(51, 5, "2.5 + jumper_h", "px1 - 32.5", "py0 + 3.5", "zht")]},
    {"id": "standoff", "name": "M2.5 standoff 3 mm (Pi)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 5, "h": "h_so", "at": [0, 0, "t"]}],
     "instances": [[x, y, 0] for x, y in pi_holes]},
    {"id": "pad", "name": "Thermal pad 15 x 15 x 3 under the processor", "source": "buy", "bodies": [
        box(15, 15, "h_so", "soc_x", "soc_y", "t")]},
    {"id": "screen", "name": "Waveshare 2in LCD module (VHB to the front wall)", "source": "buy", "bodies": [
        box("scr_l", "scr_d", "scr_h", "win_x", "t + scr_d/2", "scr_z - scr_h/2")]},
    {"id": "enc_front", "name": "PEC11R encoder, front (nut outside the wall)", "source": "library", "library": "encoder_pec11r", "bodies": [
        box("enc_w", "enc_d", "enc_h", "encF_x", "t + enc_d/2", "encF_z - enc_h/2"),
        {"type": "cyl", "d": 7, "h": "bush_out + t", "axis": "y", "at": ["encF_x", "-bush_out", "encF_z"]},
        {"type": "cyl", "d": 6, "h": "knob_h + knob_clear", "axis": "y", "at": ["encF_x", "-cap_front", "encF_z"]}]},
    {"id": "enc_side", "name": "PEC11R encoder, side (nut outside the wall)", "source": "library", "library": "encoder_pec11r", "bodies": [
        box("enc_d", "enc_w", "enc_h", "W - t - enc_d/2", "encS_y", "encS_z - enc_h/2"),
        {"type": "cyl", "d": 7, "h": "bush_out + t", "axis": "x", "at": ["W - t", "encS_y", "encS_z"]},
        {"type": "cyl", "d": 6, "h": "knob_h + knob_clear", "axis": "x", "at": ["W + bush_out", "encS_y", "encS_z"]}]},
    {"id": "knob_front", "name": "Knob cap, front (39 x 5, on the shaft)", "source": "buy", "bodies": [
        {"type": "cyl", "d": "knob_d", "h": "knob_h", "axis": "y", "at": ["encF_x", "-cap_front", "encF_z"]}]},
    {"id": "knob_side", "name": "Knob cap, side (39 x 5, on the shaft)", "source": "buy", "bodies": [
        {"type": "cyl", "d": "knob_d", "h": "knob_h", "axis": "x", "at": ["W + cap_back", "encS_y", "encS_z"]}]},
    {"id": "feet", "name": "Rubber foot", "source": "buy",
     "bodies": [{"type": "cyl", "d": "feet_d", "h": "feet_h", "at": [0, 0, "-feet_h"]}],
     "instances": [["14", "12", 0], ["W - 8", "12", 0], ["14", "D - 23", 0], ["W - 8", "D - 23", 0]]},
    {"id": "screw_m3", "name": "M3 x 6 low-head screw (plate, from below)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 5.5, "h": 1.0, "at": [0, 0, -1.0]}],
     "instances": [[x, y, 0] for x, y in (screw_left, screw_right)]},
    {"id": "clinch_nut", "name": "PEM CLS-M3-0 clinch nut (shell flanges)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 6.4, "h": 1.5, "at": [0, 0, "2*t"]}],
     "instances": [[x, y, 0] for x, y in (screw_left, screw_right)]},
    {"id": "screw_pi", "name": "M2.5 x 6 screw (Pi, from below)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 4.5, "h": 1.0, "at": [0, 0, -1.0]}],
     "instances": [[x, y, 0] for x, y in pi_holes]},
    {"id": "screw_dac", "name": "M2.5 screw (DAC Pro kit, on top)", "source": "buy", "fastener": True,
     "bodies": [{"type": "cyl", "d": 4.5, "h": 1.5, "at": [0, 0, "zht"]}],
     "instances": [[x, y, 0] for x, y in pi_holes]},
]

option = {
    "schema_version": "1.0",
    "name": "Shell + base plate, panel-mount encoders",
    "summary": ("Round 4: one folded shell (top + 4 walls) and one flat base plate. The encoders panel-mount in "
                "the front and right walls through small holes; the 39 x 5 caps slide onto the protruding shafts. Everything else is flush: "
                "rear sockets sit 1 mm inside the wall and plugs reach in. The plate with the Pi stack lifts in from "
                "below and takes 2 screws from underneath; the screen is taped in."),
    "architecture": {
        "mechanism": "encoders nutted into the shell walls; plate with Pi and DAC lifts in from below; 2 screws from underneath; caps pushed on",
        "layout": "Pi flat, USB-C side at the rear, USB/Ethernet flush behind the left wall; front encoder in front of the Pi; side encoder beside the SD end",
        "load_path": "knobs -> walls -> shell -> plate -> feet -> shelf",
        "process": "laser-cut flat, 6 hand folds on perforated lines (UNTESTED recipe); plate is flat"},
    "parts": parts,
    "load_path": ["knob_front", "shell", "plate", "feet"],
    "dims": [
        {"view": "section", "dir": "v", "a": "H/2 - knob_d/2", "b": "H/2 + knob_d/2", "at": "W + 6", "param": "knob_d"},
        {"view": "top", "dir": "h", "a": "encF_x - knob_d/2", "b": "encF_x + knob_d/2", "at": -8, "param": "knob_d"},
        {"view": "right", "dir": "h", "a": "py0", "b": "py1", "at": -8, "param": "pcb_w"},
        {"view": "right", "dir": "v", "a": 0, "b": "encS_z", "at": "D + 8", "param": "encS_z"},
    ],
    "fit": [
        {"id": "jumpers_roof", "lhs": "zht + 2.5 + jumper_h + wire_bend", "op": "<=", "rhs": "H - t",
         "why": "Jumper housings and wire bends clear the top"},
        {"id": "rear_recessed", "lhs": "py1 + rca_len", "op": "<=", "rhs": "D - t - 0.5",
         "why": "RCA barrels stop inside the rear wall (nothing passes through it)"},
        {"id": "rca_web", "lhs": "rca_x1 - rca_x2 - rca_hole", "op": ">=", "rhs": 1.5,
         "why": "Web between the two RCA openings"},
        {"id": "usbc_under_rca", "lhs": "usbc_z + usbc_h/2 + 3", "op": "<=", "rhs": "rca_z - rca_hole/2",
         "why": "USB-C opening and RCA openings keep a 3 mm web"},
        {"id": "knob_in_face", "lhs": "encF_x + knob_d/2", "op": "<=", "rhs": "W - rim",
         "why": "Front cap inside the front face outline"},
        {"id": "knob_in_height", "lhs": "(H - knob_d)/2", "op": ">=", "rhs": "rim",
         "why": "Caps inside the face height"},
        {"id": "enc_front_vs_pi", "lhs": "t + enc_d + 1", "op": "<=", "rhs": "py0",
         "why": "Front encoder body and pins in front of the Pi"},
        {"id": "enc_front_vs_screen", "lhs": "encF_x - knob_d/2", "op": ">=", "rhs": "win_x + win_w/2 + 3",
         "why": "Front cap clears the screen window"},
        {"id": "enc_front_body_vs_screen", "lhs": "encF_x - enc_w/2", "op": ">=", "rhs": "win_x + scr_l/2 + 1",
         "why": "Front encoder body clears the screen module"},
        {"id": "enc_side_beside_pi", "lhs": "W - t - enc_d", "op": ">=", "rhs": "px1 + sd_oh + 1",
         "why": "Side encoder body beside the Pi and its microSD card"},
        {"id": "encs_apart", "lhs": "encS_y - enc_w/2", "op": ">=", "rhs": "t + enc_d + 1",
         "why": "Side encoder behind the front encoder"},
        {"id": "side_knob_in_face", "lhs": "encS_y + knob_d/2", "op": "<=", "rhs": "D - rim",
         "why": "Side cap inside the side face outline"},
        {"id": "pi_front_vs_screen", "lhs": "py0", "op": ">=", "rhs": "t + scr_d + 1",
         "why": "Pi clears the screen module"},
        {"id": "left_flange_vs_pi", "lhs": "hinge*t + inset + 1 + fl_left", "op": "<=", "rhs": "py0 - 0.5",
         "why": "Left flange is in front of the Pi, so the jacks pass it as the plate lifts in"},
        {"id": "screen_in_face", "lhs": "scr_z + scr_h/2", "op": "<=", "rhs": "H - t - 1",
         "why": "Screen module fits the front wall height"},
        {"id": "nut_catches", "lhs": "t + 2.5", "op": "<=", "rhs": 7,
         "why": "Encoder bushing takes the tab, washer and M7 nut"},
    ],
    "allowed_interference": [
        ["dac", "jumpers", "jumpers on the pass-through header"],
        ["pi4", "standoff", "standoffs under the PCB"],
        ["pad", "pi4", "pad compressed under the PCB"],
        ["pad", "plate", "pad compressed on the plate"],
        ["standoff", "plate", "standoffs on the plate"],
        ["enc_front", "shell", "bushing through the Ø7.4 wall hole"],
        ["enc_side", "shell", "bushing through the Ø7.4 wall hole"],
        ["enc_front", "knob_front", "shaft in the cap"],
        ["enc_side", "knob_side", "shaft in the cap"],
        ["clinch_nut", "shell", "nut clinched into the flange"],
        ["screw_m3", "plate", "screw head under the plate"],
        ["screw_pi", "plate", "screw head under the plate"],
    ],
    "costs_vs_A": [],
    "from_inspiration": [],
    "section_y": "encS_y",
}

OUT.mkdir(parents=True, exist_ok=True)
for name, data in (("params.json", {**params, **sp}), ("option.json", option), ("shell.json", shell), ("plate.json", plate)):
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
