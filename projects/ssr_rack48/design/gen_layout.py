"""Generate parameters/layout.json for the SSR-RACK48 (run after changing any value here).

Board 17 x 4.5 in and 1.5 in overall height: given (OMEGA listing). Positions are ESTIMATED from
the top-view photo in the Digilent datasheet (Jan 2026), scaled to the given board size. Module
details (hold-down screw at the header end, 2x2 LED cluster toward the terminals) follow the
user's photo of WRC 1781 quad modules. Axes: x along the 17 in edge from the module-48 end,
y = 0 at the screw-terminal edge, z up from the PCB bottom.
"""
import json
import pathlib

P = pathlib.Path(__file__).resolve().parents[1]
L, W, T = 431.8, 114.3, 1.6
H_TOP = 38.1                     # given: 1.5 in overall with relays
MOD_L, MOD_W = 30.0, 64.0        # quad module footprint (x by y), estimated
DOT_H = 0.5                      # LED dome / screw head height above the module top
MOD_H = H_TOP - T - DOT_H        # module body, so the LEDs top out at 38.1
MOD_Y = 48.0                     # module centre y (modules span y 16..80)
PITCH = 34.5                     # module pitch inside a group of 4
GROUPS = [L / 6, L / 2, 5 * L / 6]
TB_W, TB_H, TB_Y, TB_N, TB_P = 9.0, 10.0, 7.5, 24, 5.08   # terminal strips: depth, height, centre y, positions, pitch


def build_layout():
    blocks, cyls, cuts = [], [], []
    mods = [g + k * PITCH for g in GROUPS for k in (-1.5, -0.5, 0.5, 1.5)]
    z_top = round(T + MOD_H, 3)
    for i, x in enumerate(mods, 1):
        x = round(x, 3)
        blocks.append({"ref": f"SSR{i}", "x": x, "y": MOD_Y, "l": MOD_L, "w": MOD_W, "h": round(MOD_H, 3), "z0": T})
        for dx in (-6, 6):
            for dy in (-24, -14):  # LED cluster toward the terminal end
                cyls.append({"ref": f"SSR{i}_LED", "x": x + dx, "y": MOD_Y + dy, "d": 3.0, "h": DOT_H, "z0": z_top})
        cyls.append({"ref": f"SSR{i}_screw", "x": x, "y": MOD_Y + 26, "d": 5.0, "h": DOT_H, "z0": z_top})
    for gi, g in enumerate(GROUPS, 1):
        blocks.append({"ref": f"TB{gi}", "x": round(g, 3), "y": TB_Y, "l": round(TB_N * TB_P, 3), "w": TB_W,
                       "h": TB_H, "z0": T})
        for k in range(TB_N):
            xk = round(g + (k - (TB_N - 1) / 2) * TB_P, 3)
            # screw access from the top; wire entry in the front (-y) face, cut from inside toward -y
            cuts.append({"ref": f"TB{gi}_screw", "axis": "z", "at": T + TB_H, "a": xk, "b": TB_Y + 1.0,
                         "l": 2.8, "w": 2.8, "depth": 3.0})
            cuts.append({"ref": f"TB{gi}_wire", "axis": "y", "at": TB_Y - TB_W / 2 + 4.0, "a": xk, "b": T + 3.5,
                         "l": 3.2, "w": 3.2, "depth": 4.0})
    blocks.append({"ref": "P_50pin_header", "x": 186.0, "y": 104.0, "l": 66.0, "w": 9.0, "h": 9.0, "z0": T})
    cuts.append({"ref": "P_50pin_cavity", "axis": "z", "at": T + 9.0, "a": 186.0, "b": 104.0, "l": 62.0, "w": 5.0,
                 "depth": 7.0})
    for i, x in enumerate((40.0, 95.0, 128.0, 250.0, 300.0, 392.0), 1):
        blocks.append({"ref": f"U_buf{i}", "x": x, "y": 90.0, "l": 25.0, "w": 7.6, "h": 4.5, "z0": T})
    blocks.append({"ref": "P20_molex", "x": 353.0, "y": 105.5, "l": 21.0, "w": 9.0, "h": 11.0, "z0": T})
    cuts.append({"ref": "P20_shroud", "axis": "z", "at": T + 11.0, "a": 353.0, "b": 105.5, "l": 19.0, "w": 7.0,
                 "depth": 8.0})
    for i, x in enumerate((14.0, 418.0), 1):
        blocks.append({"ref": f"SW{i}_dip4", "x": x, "y": 99.0, "l": 11.0, "w": 10.0, "h": 5.0, "z0": T})
    inset = 4.8
    holes = [{"x": round(x, 3), "y": y, "d": 3.5} for x in (inset, L / 3, 2 * L / 3, L - inset) for y in (inset, W - inset)]
    return {"_comment": __doc__.strip().replace("\n", " "),
            "board": {"l": L, "w": W}, "pcb": {"t": T, "r": 0},
            "parts": [], "holes": holes, "blocks": blocks, "cyls": cyls, "cuts": cuts}


if __name__ == "__main__":
    (P / "parameters").mkdir(exist_ok=True)
    (P / "parameters" / "layout.json").write_text(json.dumps(build_layout(), indent=1))
    (P / "parameters" / "params.json").write_text(json.dumps({"pcb_t": T}, indent=1))
    print("wrote layout.json")
