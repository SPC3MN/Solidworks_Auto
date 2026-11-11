"""SVG drawing of a folded sheet part's flat pattern, for the build output and the /design board.
Standard library only. Uses the sketch sheet's colours (sketch.CSS), so it sits beside a sketch.

Reading it: grey = sheet; dashed blue = a fold line, labelled with its direction, angle and place
in the folding sequence; red = what is cut along the fold; circles and outlines = holes and cutouts.
"""
import html

import sheet_lib as S
from sketch import CSS, num

EXTRA = """
.sk .pan{fill:var(--sk-mut);fill-opacity:.16;stroke:none}
.sk .cut{fill:none;stroke:var(--sk-fg);stroke-width:1.4;stroke-linejoin:round}
.sk .hole{fill:var(--sk-bg);stroke:var(--sk-fg);stroke-width:1.1}
.sk .fold{fill:none;stroke:#3f6fc4;stroke-width:1.1;stroke-dasharray:7 4}
.sk .perf{fill:none;stroke:var(--sk-lp);stroke-width:1.6;stroke-linecap:round}
.sk .fl{fill:#3f6fc4;font-size:10.5px}
.sk .warn{fill:var(--sk-lp);font-weight:700}
"""


def flat_svg(sheet, width=760, uid="flat"):
    x0, y0, x1, y1 = S.flat_extent(sheet)
    pad, head, foot = 28, 30, 30
    s = (width - 2 * pad) / max(x1 - x0, 1e-9)
    s = min(s, 520 / max(y1 - y0, 1e-9))
    W, H = (x1 - x0) * s + 2 * pad, (y1 - y0) * s + 2 * pad + head + foot
    pt = lambda p: (pad + (p[0] - x0) * s, head + pad + (y1 - p[1]) * s)  # noqa: E731
    path = lambda pts, close=True: "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in map(pt, pts)) + ("Z" if close else "")  # noqa: E731
    untested = S.untested(sheet)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" class="sk" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
         f'role="img" aria-label="Flat pattern of {html.escape(sheet["name"])}"><style>{CSS}{EXTRA}</style>',
         f'<rect class="bg" width="{W:.0f}" height="{H:.0f}"/>',
         f'<text class="ttl" x="{pad}" y="20">Flat pattern · {html.escape(sheet["name"])}</text>']
    if untested:
        o.append(f'<text class="warn" x="{W - pad:.0f}" y="20" text-anchor="end">UNTESTED FOLDS</text>')
    child_edges = {(f["child"], f["child_edge"]) for f in sheet["folds"]}
    for pid, p in sheet["panels"].items():
        o.append(f'<path class="pan" d="{path(p["flat"])}"/>')
        n = len(p["flat"])
        for k in range(n):
            if (pid, k % n) not in child_edges:
                o.append(f'<path class="cut" d="{path([p["flat"][k], p["flat"][(k + 1) % n]], False)}"/>')
        for e in p["flat_features"]:
            if e["kind"] == "circle":
                (cx, cy) = pt(e["c"])
                o.append(f'<circle class="hole" cx="{cx:.1f}" cy="{cy:.1f}" r="{e["r"] * s:.1f}"/>')
            elif e["kind"] == "stadium":
                o.append(f'<path class="hole" style="stroke-width:{max(e["w"] * s, 1.2):.1f};fill:none;stroke-linecap:round" d="{path([e["a"], e["b"]], False)}"/>')
            else:
                o.append(f'<path class="hole" d="{path(e["pts"])}"/>')
        cx, cy = pt([sum(q[0] for q in p["flat"]) / n, sum(q[1] for q in p["flat"]) / n])
        o.append(f'<text class="mut" x="{cx:.1f}" y="{cy + 4:.1f}" text-anchor="middle">{html.escape(pid)}</text>')
    for f in sheet["folds"]:
        o.append(f'<path class="fold" d="{path([f["m0"], f["m1"]], False)}"/>')
        cuts, relief = S.fold_entities(sheet, f)
        for e in cuts:
            a, b = (e["a"], e["b"]) if e["kind"] != "circle" else (e["c"], e["c"])
            o.append(f'<path class="perf" d="{path([a, b], False)}"/>')
        for e in relief:
            (cx, cy) = pt(e["c"])
            o.append(f'<circle class="hole" cx="{cx:.1f}" cy="{cy:.1f}" r="{e["r"] * s:.1f}"/>')
        mid = [(f["m0"][0] + f["m1"][0]) / 2 - f["n"][0] * 9 / s, (f["m0"][1] + f["m1"][1]) / 2 - f["n"][1] * 9 / s]   # on the parent's side
        lx, ly = pt(mid)
        label = f'{"▲" if f["direction"] == "up" else "▼"} {num(f["angle"])}° · {f["sequence"]}'
        o.append(f'<text class="fl dt" x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle">{label}</text>')
    recs = "; ".join(f'{k}: {r["method"]} {num(r["slot_length"])} long, {num(r["bridge"])} bridge'
                     + (f', {num(r["slot_width"])} wide' if r["slot_width"] > 0 else ", slit") for k, r in sheet["recipes"].items())
    o.append(f'<text class="mut" x="{pad}" y="{H - 10:.0f}">blank {num(x1 - x0)} × {num(y1 - y0)} · {html.escape(sheet["material"])} '
             f'· ▲ folds toward you, then angle and folding order · {html.escape(recs)}</text>')
    o.append("</svg>")
    return "\n".join(o)
