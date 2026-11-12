"""Six orthographic views (to scale, mm) of the deck's electronics, for arranging them in the housing.
Writes electronics_views.svg next to this file. Sizes as in the brief and the repo models; ~ = estimate."""
from pathlib import Path

C = {"pcb": "#3f7d4f", "metal": "#b9bfc6", "black": "#2a2b2e", "brass": "#c9a64a", "glass": "#1d2a3a",
     "lit": "#4c6f99", "white": "#e8e8e8"}

def B(name, x0, y0, z0, x1, y1, z1, col):
    return ("box", name, (x0, y0, z0, x1, y1, z1), col)

def CY(name, axis, c, r, a0, a1, col):          # c: centre in the two other axes (sorted xyz order)
    return ("cyl", name, (axis, c, r, a0, a1), col)

def bbox(it):
    if it[0] == "box":
        return it[2]
    axis, c, r, a0, a1 = it[2]
    lo, hi = [0] * 3, [0] * 3
    others = [k for k in range(3) if k != axis]
    for k, v in zip(others, c):
        lo[k], hi[k] = v - r, v + r
    lo[axis], hi[axis] = min(a0, a1), max(a0, a1)
    return (*lo, *hi)

# view: (title, horizontal axis, sign, vertical axis, sign, depth axis, depth sign toward viewer)
VIEWS = [("Top (looking down)", 0, 1, 1, 1, 2, 1), ("Bottom (looking up)", 0, 1, 1, -1, 2, -1),
         ("Front (from −Y)", 0, 1, 2, 1, 1, -1), ("Rear (from +Y)", 0, -1, 2, 1, 1, 1),
         ("Left (from −X)", 1, -1, 2, 1, 0, -1), ("Right (from +X)", 1, 1, 2, 1, 0, 1)]

def view_svg(items, v, labels):
    title, h, hs, vv, vs, d, ds = v
    bbs = [bbox(i) for i in items]
    lo = [min(b[k] for b in bbs) for k in range(3)]
    hi = [max(b[k + 3] for b in bbs) for k in range(3)]
    S, pad = 3.2, 26
    W = (hi[h] - lo[h]) * S + 2 * pad
    H = (hi[vv] - lo[vv]) * S + 2 * pad
    def X(val):
        return pad + ((val - lo[h]) if hs > 0 else (hi[h] - val)) * S
    def Y(val):
        return pad + ((hi[vv] - val) if vs > 0 else (val - lo[vv])) * S
    out = []
    order = sorted(zip(items, bbs), key=lambda p: (p[1][d + 3] if ds > 0 else -p[1][d]))
    for it, b in order:
        col = C[it[3]]
        if it[0] == "cyl" and it[2][0] == d:
            axis, c, r, *_ = it[2]
            others = [k for k in range(3) if k != axis]
            cc = dict(zip(others, c))
            out.append(f'<circle cx="{X(cc[h]):.1f}" cy="{Y(cc[vv]):.1f}" r="{r*S:.1f}" fill="{col}" stroke="#111" stroke-width=".6"><title>{it[1]}</title></circle>')
        else:
            x0, x1 = sorted((X(b[h]), X(b[h + 3])))
            y0, y1 = sorted((Y(b[vv]), Y(b[vv + 3])))
            rx = 1.5 if it[0] == "cyl" else 0
            out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1-x0:.1f}" height="{y1-y0:.1f}" rx="{rx}" fill="{col}" stroke="#111" stroke-width=".6"><title>{it[1]}</title></rect>')
    # overall dimensions
    out.append(f'<text x="{W/2:.0f}" y="{H-6:.0f}" class="dm" text-anchor="middle">{hi[h]-lo[h]:.1f}</text>')
    out.append(f'<text x="8" y="{H/2:.0f}" class="dm" transform="rotate(-90 8 {H/2:.0f})" text-anchor="middle">{hi[vv]-lo[vv]:.1f}</text>')
    out.insert(0, f'<text x="{pad}" y="14" class="vt">{title}</text>')
    return "".join(out), W, H

# ---- Pi 4 + DAC Pro, Pi frame: x along 85 (microSD end x = 0, USB/Ethernet end x = 85), y = 0 at the USB-C side, z up from the Pi PCB underside
zt, zd = 1.4, 1.4 + 9.0
dt = zd + 1.6
stack = [
    B("Pi 4 PCB", 0, 0, 0, 85, 56, 1.4, "pcb"),
    B("microSD card", -2.5, 22, -1.2, 12, 34, -0.2, "black"),
    B("USB 2 (black) ×2", 85 - 17.4, 9 - 7.25, zt, 87.7, 9 + 7.25, zt + 16, "metal"),
    B("USB 3 (blue) ×2", 85 - 17.4, 27 - 7.25, zt, 87.7, 27 + 7.25, zt + 16, "metal"),
    B("Ethernet", 85 - 21, 45.75 - 8, zt, 87.7, 45.75 + 8, zt + 13.5, "metal"),
    B("USB-C power", 11.2 - 4.5, -1.2, zt, 11.2 + 4.5, 6, zt + 3.2, "metal"),
    B("micro-HDMI 0", 26 - 3.75, -1, zt, 26 + 3.75, 6.5, zt + 3, "metal"),
    B("micro-HDMI 1", 39.5 - 3.75, -1, zt, 39.5 + 3.75, 6.5, zt + 3, "metal"),
    B("Pi audio jack", 54 - 3, 0, zt, 54 + 3, 12, zt + 6, "black"),
    *[CY("standoff 9", 2, (x, y), 2.5, zt, zd, "brass") for x in (3.5, 61.5) for y in (3.5, 52.5)],
    B("DAC Pro PCB", 0, -0.25, zd, 65, 56.25, dt, "pcb"),
    B("RCA block", 12, 0, dt, 39.6, 14, dt + 13, "black"),
    CY("RCA L", 1, (18.36, dt + 6.5), 4, -9, 0, "brass"),
    CY("RCA R", 1, (32.98, dt + 6.5), 4, -9, 0, "brass"),
    B("DAC headphone jack", 51.8 - 4, 0, dt, 51.8 + 4, 12, dt + 6, "black"),
    CY("jack nose", 1, (51.8, dt + 3), 2.5, -2.5, 0, "black"),
    B("40-pin pass-through header", 7, 50, dt, 58, 55, dt + 8.5, "black"),
]
stack_labels = [("USB/Eth", (80, 30, 18)), ("USB-C", (11, -2, 5)), ("RCA", (25, -9, 26)),
                ("SD", (-2, 28, -1)), ("Jack", (52, -3, 18)), ("Header", (32, 53, 21))]

# ---- Waveshare 2in LCD module, x along 58, y = 0 at the glass face, z up (35)
screen = [
    B("PCB", 0, 1.6, 0, 58, 3.2, 35, "pcb"),
    B("LCD glass", 4, 0, 1.5, 54, 1.6, 33.5, "glass"),
    B("lit area 40.8 × 30.6", 29 - 20.4, -0.05, 17.5 - 15.3, 29 + 20.4, 0, 17.5 + 15.3, "lit"),
    B("8-pin connector (~)", 20, 3.2, 3, 38, 9, 9, "white"),
    *[CY("M2 hole (~)", 1, (x, z), 1.1, 0, 3.3, "white") for x in (2.5, 55.5) for z in (2.5, 32.5)],
]
screen_labels = [("lit area", (29, -1, 17.5)), ("connector (~)", (29, 10, 6))]

# ---- Bourns PEC11R encoder, body centred, z = 0 at the body bottom, shaft up
enc = [
    B("body", -6.25, -6.7, 0, 6.25, 6.7, 6.6, "metal"),
    CY("M7 bushing", 2, (0, 0), 3.5, 6.6, 13.6, "metal"),
    CY("shaft Ø6, D-flat", 2, (0, 0), 3, 13.6, 33.6, "metal"),
    *[B("pin", x - 0.4, -6.7 - 4, -3.5, x + 0.4, -6.7 - 3.6, 0, "brass") for x in (-2.5, 0, 2.5)],
    *[B("switch pin", x - 0.4, 6.7 + 3.6, -3.5, x + 0.4, 6.7 + 4, 0, "brass") for x in (-2.5, 2.5)],
    B("anti-turn lug (~)", -0.75, 6.7, 6.6, 0.75, 7.5, 7.6, "metal"),
]
enc_labels = [("shaft", (0, 0, 30)), ("pins", (0, -12, -2))]

units = [("Raspberry Pi 4 + DAC Pro", stack), ("Waveshare 2in LCD module", screen), ("Bourns PEC11R encoder", enc)]
body, y, width = [], 10, 0
for title, items in units:
    body.append(f'<text x="10" y="{y + 18}" class="ut">{title}</text>')
    y += 28
    x, row_h = 10, 0
    for v in VIEWS:
        g, W, H = view_svg(items, v, [])
        body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
        x += max(W, 150) + 12
        row_h = max(row_h, H)
    width = max(width, x)
    y += row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("electronics_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("electronics_views.svg"))

# ---- Waveshare 3.5in HDMI LCD (projects/lcd_35_hdmi): x along 85.42, y = 0 at the HDMI edge, z up from the PCB underside
lcd35 = [
    B("PCB", 0, 0, 0, 85.42, 55.92, 1.6, "pcb"),
    B("LCD + touch", (85.42 - 80.5) / 2, 0.5, 1.6, (85.42 + 80.5) / 2, 55.42, 5.8, "glass"),
    B("lit area 73.44 × 48.96", 42.71 - 36.72, 27.96 - 24.48, 5.8, 42.71 + 36.72, 27.96 + 24.48, 5.85, "lit"),
    B("26-pin GPIO socket", 7.1 - 1.27, 52.5 - 2.54, -8.5, 7.1 - 1.27 + 33.02, 52.5 + 2.54, 0, "black"),
    B("HDMI", 32 - 7.5, -0.5, -5.6, 32 + 7.5, 11, 0, "metal"),
    B("3.5 mm jack", 53.5 - 3, 0, -5, 53.5 + 3, 12, 0, "black"),
    CY("jack nose", 1, (53.5, -2.5), 2.5, -2.5, 0, "black"),
]
body, y, width = [], 10, 0
body.append(f'<text x="10" y="{y + 18}" class="ut">Waveshare 3.5in HDMI LCD</text>')
y += 28
x, row_h = 10, 0
for v in VIEWS:
    g, W, H = view_svg(lcd35, v, [])
    body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
    x += max(W, 150) + 12
    row_h = max(row_h, H)
width, y = x, y + row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("lcd35_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("lcd35_views.svg"))

# ---- Waveshare 3.5in DSI LCD (E), 640 x 480, from Waveshare's 2D drawing (2025-11-28).
# x along 77 (seen from the front), y = 0 at the glass, z up (65). Back-side parts are placed from the drawing (~).
dsi = [
    B("cover lens 77.27 × 63.51", -0.135, 0, 65 - 63.51, 77.135, 7.3, 65, "glass"),
    B("viewing area 70.67 × 53.27", 3.3 - 0.135, -0.05, 65 - 2.55 - 53.27, 3.3 - 0.135 + 70.67, 0, 65 - 2.55, "lit"),
    B("PCB 77 × 65", 0, 7.3, 0, 77, 8.9, 65, "pcb"),
    B("FPC tail", 18, 0, -0.6, 60, 1.2, 65 - 63.51, "black"),
    *[CY("M2.5 standoff hole", 1, (x, z), 1.35, 8.9, 12.9, "brass") for x in (77 - 15.6, 77 - 15.6 - 58) for z in (65 - 12.3, 65 - 12.3 - 49)],
    B("15-pin DSI connector (Pi 4) ~", 14, 8.9, 18, 44, 12.9, 24, "white"),
    B("22-pin DSI1 connector (Pi 5) ~", 1, 8.9, 21, 5.5, 12.9, 44, "white"),
    B("I2C / power connector ~", 59, 8.9, 26, 66, 12.9, 33, "white"),
]
body, y = [f'<text x="10" y="28" class="ut">Waveshare 3.5in DSI LCD (E)</text>'], 38
x, row_h = 10, 0
for v in VIEWS:
    g, W, H = view_svg(dsi, v, [])
    body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
    x += max(W, 150) + 12
    row_h = max(row_h, H)
width, y = x, y + row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("lcd35_dsi_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("lcd35_dsi_views.svg"))

# ---- Elecrow 4in square IPS 480 x 480, ST7701S, 3-wire SPI (setup) + RGB (pixels), capacitive touch.
# Outline 84.3 × 84.3 and active area 71.86 × 70.18 from Elecrow's listing; thickness and FPCs estimated (~).
# x along 84.3 (seen from the front), y = 0 at the glass, z up. Bare panel: no mounting holes, held by VHB.
sq = [
    B("touch lens 84.3 × 84.3", 0, 0, 0, 84.3, 1.1, 84.3, "glass"),
    B("active area 71.86 × 70.18", (84.3 - 71.86) / 2, -0.05, (84.3 - 70.18) / 2, (84.3 + 71.86) / 2, 0, (84.3 + 70.18) / 2, "lit"),
    B("LCD panel ~", 1, 1.1, 1, 83.3, 3.6, 83.3, "black"),
    B("40-pin RGB/SPI FPC ~", 32, 3.6, -30, 52, 3.8, 1, "brass"),
    B("touch FPC ~", 58, 3.6, -15, 66, 3.8, 1, "brass"),
]
body, y = [f'<text x="10" y="28" class="ut">Elecrow 4in square 480 × 480 (ST7701S, SPI + RGB)</text>'], 38
x, row_h = 10, 0
for v in VIEWS:
    g, W, H = view_svg(sq, v, [])
    body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
    x += max(W, 150) + 12
    row_h = max(row_h, H)
width, y = x, y + row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("lcd4_square_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("lcd4_square_views.svg"))

# ---- VIEWE 4.0in square MIPI DSI 720 x 720 (dtoverlay=viewe-mipi-4inch), capacitive I2C touch on the same FPC.
# Outline 84 × 84 and active area 71.93 × 71.93 from VIEWE's square-display table; thickness and FPC estimated (~).
# x along 84.3 (seen from the front), y = 0 at the glass, z up. Bare panel: no mounting holes, held by VHB.
dsq = [
    B("touch lens 84 × 84", 0, 0, 0, 84, 1.1, 84, "glass"),
    B("active area 71.93 × 71.93", 6.035, -0.05, 6.035, 77.965, 0, 77.965, "lit"),
    B("LCD panel ~", 1, 1.1, 1, 83, 3.6, 83, "black"),
    B("22-pin DSI FPC (video + touch + power) ~", 34, 3.6, -40, 50, 3.8, 1, "brass"),
]
body, y = [f'<text x="10" y="28" class="ut">VIEWE 4in square 720 × 720 MIPI DSI</text>'], 38
x, row_h = 10, 0
for v in VIEWS:
    g, W, H = view_svg(dsq, v, [])
    body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
    x += max(W, 150) + 12
    row_h = max(row_h, H)
width, y = x, y + row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("lcd4_square_dsi_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("lcd4_square_dsi_views.svg"))

# ---- Waveshare 5inch DSI LCD, 800 x 480, from Waveshare's 2D drawing. x along 121 (seen from the front), y = 0 at
# the glass, z up (76). Lens + LCD 5.4, back of PCB 9.0, parts to 13.0. Back-side connectors scaled off the drawing (~).
w5 = [
    B("lens 120.7 × 77.2 (TP + LCD 5.4)", 0.15, 0, -0.6, 120.85, 5.4, 76.6, "glass"),
    B("viewing area 109 × 65.8", 6.0, -0.05, 73.5 - 65.8, 115.0, 0, 73.5, "lit"),
    B("frame", 1, 5.4, 1, 120, 7.4, 75, "black"),
    B("PCB 121 × 76", 0, 7.4, 0, 121, 9.0, 76, "pcb"),
    *[CY("M2.5 hole, 113 × 68", 1, (x, z), 1.25, 9.0, 13.0, "brass") for x in (4, 117) for z in (4, 72)],
    *[CY("M2.5 Pi standoff, 58 × 49", 1, (x, z), 1.25, 9.0, 13.0, "brass") for x in (37.4, 95.4) for z in (13.5, 62.5)],
    B("15-pin DSI FFC (Pi 4) ~", 22.7, 9.0, 24, 48.4, 13.0, 45, "white"),
    B("22-pin DSI1 (Pi 5) ~", 11, 9.0, 27, 17, 13.0, 47, "white"),
    B("I2C / power connector ~", 98, 9.0, 28, 105, 13.0, 34, "white"),
]
body, y = [f'<text x="10" y="28" class="ut">Waveshare 5inch DSI LCD, 800 × 480</text>'], 38
x, row_h = 10, 0
for v in VIEWS:
    g, W, H = view_svg(w5, v, [])
    body.append(f'<g transform="translate({x:.0f},{y:.0f})">{g}</g>')
    x += max(W, 150) + 12
    row_h = max(row_h, H)
width, y = x, y + row_h + 16
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" height="{y:.0f}">'
       '<style>text{font-family:sans-serif}.ut{font-size:16px;font-weight:700}.vt{font-size:11px;font-weight:600}.dm{font-size:11px;fill:#333}</style>'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(body)}</svg>')
Path(__file__).with_name("lcd5_dsi_views.svg").write_text(svg, encoding="utf-8")
print("wrote", Path(__file__).with_name("lcd5_dsi_views.svg"))
