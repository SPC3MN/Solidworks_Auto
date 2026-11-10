"""To-scale SVG sheet of one draft option: the section at y = section_y, the right and top
outlines, the dimensions, the load path and the part legend. Standard library only.

    python3 scripts/sketch.py products/<name>/draft/round_1/A        # writes A/sketch.svg

Every view uses one scale (px per mm, printed on the sheet with a scale bar), so sizes can be
compared by eye, and design_cli.py draws all options of a round at the same scale. Geometry comes
from draft_lib.load_option, the same resolved bodies the 3D massing is built from.

Reading the sheet: hatched = cut by the section plane; grey = bought; thin outline = behind the
plane; dashed = hidden or removed material. Dimension text: bold = given or measured,
regular = chosen by the skill, italic with ~ = estimated.
"""
import html
import math
import pathlib
import sys

import draft_lib as D

PALETTE = ["#3f6fc4", "#d17a22", "#2f9462", "#a94fa0", "#b8961c", "#2b98ab", "#c25050", "#6d62c8"]
BUY = "#868c96"
M, PAD, GAP, HEAD, FOOT = 16, 46, 14, 44, 34
CHAR = 6.4  # px per character at the sheet's 12 px text

CSS = """
.sk{--sk-bg:#fff;--sk-fg:#1b2230;--sk-mut:#667085;--sk-lp:#d92d20;font:12px ui-sans-serif,system-ui,sans-serif}
@media (prefers-color-scheme:dark){.sk{--sk-bg:#14171c;--sk-fg:#e7e9ee;--sk-mut:#98a2b3;--sk-lp:#ff6b5e}}
.sk text{fill:var(--sk-fg)}
.sk .bg{fill:var(--sk-bg)}
.sk .mut{fill:var(--sk-mut)}
.sk .ttl{font-size:15px;font-weight:600}
.sk .vt{fill:var(--sk-mut);font-size:10.5px;letter-spacing:.08em}
.sk .edge{fill:none;stroke:var(--sk-fg);stroke-width:2.6;stroke-linejoin:round}
.sk .cutedge{fill:none;stroke:var(--sk-fg);stroke-width:1.3}
.sk .ol{stroke:var(--sk-fg);stroke-width:1.1;fill-opacity:.14}
.sk .behind{fill:none;stroke:var(--sk-mut);stroke-width:.9}
.sk .hid{fill:none;stroke:var(--sk-mut);stroke-width:.9;stroke-dasharray:4 3}
.sk .hl{stroke:var(--sk-fg);stroke-width:1}
.sk .dim{fill:none;stroke:var(--sk-mut);stroke-width:.8}
.sk .dt{font-size:11.5px;paint-order:stroke;stroke:var(--sk-bg);stroke-width:3.5px;stroke-linejoin:round}
.sk .given{font-weight:700}
.sk .estimated{font-style:italic}
.sk .lp{fill:none;stroke:var(--sk-lp);stroke-width:1.8;stroke-dasharray:7 3}
.sk .lpn{fill:var(--sk-lp)}
.sk .lpt{fill:var(--sk-lp);font-size:11px;font-weight:600}
"""


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class View:
    """One orthographic view: a window (mm) placed on the sheet at one scale."""

    def __init__(self, title, pts):
        self.title = title
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        self.ulo, self.uhi, self.vlo, self.vhi = min(us), max(us), min(vs), max(vs)

    def widen(self, other, u=False, v=False):
        if u:
            self.ulo, self.uhi = min(self.ulo, other.ulo), max(self.uhi, other.uhi)
        if v:
            self.vlo, self.vhi = min(self.vlo, other.vlo), max(self.vhi, other.vhi)

    def place(self, x0, y0, s):
        self.x0, self.y0, self.s = x0, y0, s
        self.w, self.h = (self.uhi - self.ulo) * s, (self.vhi - self.vlo) * s

    def pt(self, u, v):
        return self.x0 + (u - self.ulo) * self.s, self.y0 + (self.vhi - v) * self.s

    def d(self, shape):
        out = []
        for sub in shape:
            if sub[0] == "poly":
                pts = [self.pt(*p) for p in sub[1]]
                out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + ("Z" if len(pts) > 2 else ""))
            else:
                (x, y), r = self.pt(*sub[1]), sub[2] * self.s
                out.append(f"M{x - r:.1f},{y:.1f}a{r:.1f},{r:.1f} 0 1,0 {2 * r:.1f},0a{r:.1f},{r:.1f} 0 1,0 {-2 * r:.1f},0Z")
        return "".join(out)


def _dims(opt, view_name):
    out = []
    for n, d in enumerate(opt["dims"]):
        if d.get("view", "section") != view_name:
            continue
        what = f"option {opt['id']}, dim {n}"
        if d.get("dir") not in ("h", "v"):
            raise D.DraftError(f"{what}: dir must be h or v")
        try:
            a, b, at = (D.evaluate(d[k], opt["names"]) for k in ("a", "b", "at"))
        except KeyError as e:
            raise D.DraftError(f"{what}: missing {e}") from None
        src = opt["params"].get(d.get("param"), {}).get("src", d.get("src", "chosen"))
        text = d.get("text") or ("Ø" if d.get("dia") else "") + num(abs(b - a))
        out.append({"dir": d["dir"], "a": a, "b": b, "at": at, "src": src,
                    "frm": D.evaluate(d["from"], opt["names"]) if "from" in d else None,
                    "text": ("~" if src == "estimated" else "") + text})
    return out


def _dim_svg(view, d, box):
    """Dimension line with tick ends and extension lines back to the product's outline."""
    ulo, vlo, uhi, vhi = box
    a, b, at, frm = d["a"], d["b"], d["at"], d["frm"]
    horiz = d["dir"] == "h"
    lo, hi = (vlo, vhi) if horiz else (ulo, uhi)
    if frm is None:
        frm = hi if at > hi else lo if at < lo else at
    p1, p2 = (view.pt(a, at), view.pt(b, at)) if horiz else (view.pt(at, a), view.pt(at, b))
    out = [f'<path class="dim" d="M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}"/>']
    for c, p in ((a, p1), (b, p2)):
        f = view.pt(c, frm) if horiz else view.pt(frm, c)
        k = 4 if (p[1] < f[1] if horiz else p[0] > f[0]) else -4
        if abs(frm - at) > 1e-9:
            end = (p[0], p[1] - k) if horiz else (p[0] + k, p[1])
            out.append(f'<path class="dim" d="M{f[0]:.1f},{f[1]:.1f}L{end[0]:.1f},{end[1]:.1f}"/>')
        out.append(f'<path class="dim" style="stroke-width:1.4" d="M{p[0] - 3.5:.1f},{p[1] + 3.5:.1f}L{p[0] + 3.5:.1f},{p[1] - 3.5:.1f}"/>')
    length = abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
    fits = length > len(d["text"]) * CHAR + 10
    t = html.escape(d["text"])
    if horiz:
        x, anchor = ((p1[0] + p2[0]) / 2, "middle") if fits else (max(p1[0], p2[0]) + 7, "start")
        out.append(f'<text class="dt {d["src"]}" x="{x:.1f}" y="{p1[1] - 5:.1f}" text-anchor="{anchor}">{t}</text>')
    else:
        y, anchor = ((p1[1] + p2[1]) / 2, "middle") if fits else (min(p1[1], p2[1]) - 7, "start")
        out.append(f'<text class="dt {d["src"]}" transform="translate({p1[0] - 5:.1f},{y:.1f}) rotate(-90)" text-anchor="{anchor}">{t}</text>')
    return "".join(out)


def _collect(opt):
    """Per view: what to draw for each part, and every point drawn (for the view windows)."""
    sy = opt["section_y"]
    main = {"cut": {}, "behind": [], "pts": []}
    side = {n: {"items": [], "pts": []} for n in ("x", "z")}
    for i, p in enumerate(opt["parts"]):
        sec = {"add": [], "cut": []}
        for at in p["instances"]:
            for b0 in p["bodies"]:
                b = D.moved(b0, at)
                shapes = D.section(b, sy)
                if shapes:
                    sec[b["op"]] += shapes
                elif b["op"] == "add":
                    sil, _ = D.outline(b, "y")
                    main["behind"].append(sil)
                for n in ("x", "z"):
                    sil, hidden = D.outline(b, n)
                    side[n]["items"].append((i, b["op"], sil, hidden))
                    if b["op"] == "add":
                        side[n]["pts"] += list(D.shape_points(sil))
        if sec["add"]:
            main["cut"][i] = sec
    lo, hi = opt["bbox"]
    main["pts"] = [(lo[0], lo[2]), (hi[0], hi[2])]
    return main, side


def content_size(opt):
    """(mm across, mm down) that the three views need, for choosing a common scale."""
    ex = _extents(opt)
    return ex["section"].uhi - ex["section"].ulo + ex["right"].uhi - ex["right"].ulo, \
        ex["section"].vhi - ex["section"].vlo + ex["top"].vhi - ex["top"].vlo


def _extents(opt):
    main, side = _collect(opt)
    views = {"section": View(f"SECTION y = {num(opt['section_y'])}", main["pts"]),
             "right": View("RIGHT", side["x"]["pts"]), "top": View("TOP", side["z"]["pts"])}
    for name, v in views.items():
        for d in _dims(opt, name):
            pts = [(d["a"], d["at"]), (d["b"], d["at"])] if d["dir"] == "h" else [(d["at"], d["a"]), (d["at"], d["b"])]
            v.widen(View("", pts), u=True, v=True)
    views["section"].widen(views["top"], u=True)
    views["top"].widen(views["section"], u=True)
    views["section"].widen(views["right"], v=True)
    views["right"].widen(views["section"], v=True)
    return views


def fit_scale(opt, width=1040, max_height=860):
    across, down = content_size(opt)
    return min((width - 2 * M - GAP - 4 * PAD) / across, (max_height - HEAD - FOOT - GAP - 4 * PAD) / down)


def render(opt, scale=None, uid=None):
    """SVG text of the sheet. `uid` prefixes the ids, so several sheets can sit in one HTML page."""
    uid = uid or f"sk{opt['id']}"
    s = scale or fit_scale(opt)
    main, side = _collect(opt)
    views = _extents(opt)
    sec, right, top = views["section"], views["right"], views["top"]
    sec.place(M + PAD, HEAD + PAD, s)
    right.place(sec.x0 + sec.w + 2 * PAD + GAP, sec.y0, s)
    top.place(sec.x0, sec.y0 + sec.h + 2 * PAD + GAP, s)

    parts = opt["parts"]
    colour = [PALETTE[i % len(PALETTE)] if p["source"] == "make" else BUY for i, p in enumerate(parts)]
    legend = [f"{p['id']}: {p['name']}" + (f" ×{p['qty']}" if p["qty"] > 1 else "") + " · "
              + " · ".join(x for x in (p["source"] if p["source"] != "make" else p["process"] or "make", p["material"]) if x)
              for p in parts]
    lx, ly = right.x0 - PAD + 6, top.y0 - PAD + 16
    W = max(right.x0 + right.w + PAD, lx + max(len(t) for t in legend) * CHAR + 30) + M
    H = max(top.y0 + top.h + PAD, ly + 18 * (len(parts) + 1) + 8) + FOOT

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" class="sk" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
         f'role="img" aria-label="Option {html.escape(opt["id"])} sketch"><style>{CSS}</style>',
         f'<rect class="bg" width="{W:.0f}" height="{H:.0f}"/><defs>']
    for k, ang in enumerate((45, 135)):
        o.append(f'<pattern id="{uid}-h{k}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate({ang})">'
                 '<line class="hl" x1="0" y1="0" x2="0" y2="6"/></pattern>')
    for i, c in main["cut"].items():
        adds, cuts = "".join(f'<path d="{sec.d(sh)}"/>' for sh in c["add"]), "".join(f'<path fill-rule="evenodd" d="{sec.d(sh)}"/>' for sh in c["cut"])
        # ma: the cuts, grown a little, hide the add edges they remove. mb: the adds, shrunk a
        # little, keep cut outlines only where they run inside material.
        o.append(f'<mask id="{uid}-ma{i}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H:.0f}">'
                 f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/><g fill="#000" stroke="#000" stroke-width="3">{cuts}</g></mask>')
        o.append(f'<mask id="{uid}-mb{i}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H:.0f}">'
                 f'<g fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="3">{adds}</g></mask>')
    o.append("</defs>")
    o.append(f'<text class="ttl" x="{M}" y="26">{html.escape(opt["id"])} · {html.escape(opt["name"])}</text>')

    for v in (sec, right, top):
        o.append(f'<text class="vt" x="{v.x0:.1f}" y="{v.y0 - PAD + 13:.1f}">{v.title}</text>')

    # section view: parts behind the plane, then the parts it cuts
    for sil in main["behind"]:
        o.append(f'<path class="behind" d="{sec.d(sil)}"/>')
    for i, c in main["cut"].items():
        hatch = parts[i]["source"] == "make"
        ds = [sec.d(sh) for sh in c["add"]]
        o.append(f'<g mask="url(#{uid}-ma{i})">' + "".join(f'<path class="edge" d="{d}"/>' for d in ds)
                 + "".join(f'<path class="bg" fill-rule="evenodd" d="{d}"/>' for d in ds)
                 + f'<g opacity=".34" fill="{colour[i]}">' + "".join(f'<path fill-rule="evenodd" d="{d}"/>' for d in ds) + "</g>"
                 + (f'<g opacity=".4" fill="url(#{uid}-h{i % 2})">' + "".join(f'<path fill-rule="evenodd" d="{d}"/>' for d in ds) + "</g>" if hatch else "")
                 + "</g>")
        if c["cut"]:
            o.append(f'<g mask="url(#{uid}-mb{i})">' + "".join(f'<path class="cutedge" d="{sec.d(sh)}"/>' for sh in c["cut"]) + "</g>")

    # outline views
    for v, n in ((right, "x"), (top, "z")):
        for i, op, sil, hidden in side[n]["items"]:
            if op == "add":
                o.append(f'<path class="ol" fill="{colour[i]}" d="{v.d(sil)}"/>')
            else:
                o.append(f'<path class="hid" d="{v.d(sil)}"/>')
            o += [f'<path class="hid" d="{v.d(h)}"/>' for h in hidden]

    # dimensions: overall sizes automatically, the rest from option.json
    lo, hi = opt["bbox"]
    off = 26 / s
    boxes = {"section": (lo[0], lo[2], hi[0], hi[2]), "right": (lo[1], lo[2], hi[1], hi[2]), "top": (lo[0], lo[1], hi[0], hi[1])}
    auto = {"section": [("h", lo[0], hi[0], sec.vhi + off), ("v", lo[2], hi[2], sec.ulo - off)],
            "right": [("h", lo[1], hi[1], right.vhi + off)], "top": []}
    for name, v in views.items():
        for dr, a, b, at in auto[name]:
            o.append(_dim_svg(v, {"dir": dr, "a": a, "b": b, "at": at, "frm": None, "src": "chosen", "text": num(b - a)}, boxes[name]))
        for d in _dims(opt, name):
            o.append(_dim_svg(v, d, boxes[name]))

    # load path through the section view
    nodes = []
    for e in opt["load_path"]:
        pid = e["part"] if isinstance(e, dict) else e
        if isinstance(e, dict) and "at" in e:
            nodes.append(sec.pt(*(D.evaluate(c, opt["names"]) for c in e["at"])))
        else:
            p = next(p for p in parts if p["id"] == pid)
            blo, bhi = D.union_box(D.bbox3(D.moved(b, at)) for at in p["instances"] for b in p["bodies"] if b["op"] == "add")
            nodes.append(sec.pt((blo[0] + bhi[0]) / 2, (blo[2] + bhi[2]) / 2))
    if len(nodes) > 1:
        o.append('<path class="lp" d="M' + "L".join(f"{x:.1f},{y:.1f}" for x, y in nodes) + '"/>')
        o += [f'<circle class="lpn" cx="{x:.1f}" cy="{y:.1f}" r="3"/>' for x, y in nodes[:-1]]
        (x0, y0), (x1, y1) = nodes[-2], nodes[-1]
        n = math.hypot(x1 - x0, y1 - y0) or 1.0
        ux, uy = (x1 - x0) / n, (y1 - y0) / n
        o.append(f'<path class="lpn" d="M{x1:.1f},{y1:.1f}L{x1 - 10 * ux - 4.5 * uy:.1f},{y1 - 10 * uy + 4.5 * ux:.1f}'
                 f'L{x1 - 10 * ux + 4.5 * uy:.1f},{y1 - 10 * uy - 4.5 * ux:.1f}Z"/>')
        o.append(f'<text class="lpt dt" x="{nodes[0][0] + 8:.1f}" y="{nodes[0][1] - 7:.1f}">load path</text>')

    # legend, scale bar, footer
    o.append(f'<text class="vt" x="{lx:.1f}" y="{ly:.1f}">PARTS</text>')
    for i, t in enumerate(legend):
        y = ly + 18 * (i + 1)
        o.append(f'<rect x="{lx:.1f}" y="{y - 10:.1f}" width="14" height="11" fill="{colour[i]}" fill-opacity=".5" stroke="{colour[i]}"/>'
                 f'<text x="{lx + 21:.1f}" y="{y:.1f}">{html.escape(t)}</text>')
    bar = next(b for b in (200, 100, 50, 20, 10, 5, 2, 1) if b * s <= 180 or b == 1)
    by = H - 14
    o.append(f'<path class="dim" style="stroke-width:1.6" d="M{M},{by - 5}v5h{bar * s:.1f}v-5"/>'
             f'<text class="mut" x="{M + bar * s + 8:.1f}" y="{by:.1f}">{bar} mm · scale {s:.2f} px/mm · '
             f'envelope {num(hi[0] - lo[0])} × {num(hi[1] - lo[1])} × {num(hi[2] - lo[2])} · draft {opt["hash"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def write(opt, scale=None, uid=None):
    svg = render(opt, scale, uid)
    (opt["folder"] / "sketch.svg").write_text(svg, encoding="utf-8", newline="\n")
    return svg


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        try:
            write(D.load_option(folder))
            print(pathlib.Path(folder) / "sketch.svg")
        except D.DraftError as e:
            sys.exit(f"{folder}: {e}")
