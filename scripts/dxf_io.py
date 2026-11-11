"""A small layered DXF writer (R12 ASCII, mm) and a reader for the read-back check. Standard
library only.

Entities are dicts in flat-pattern coordinates:
    {"kind": "line", "a": [x, y], "b": [x, y]}
    {"kind": "circle", "c": [x, y], "r": r}
    {"kind": "poly", "pts": [[x, y], ...], "closed": True, "bulges": [0, ...]}   bulge of the edge leaving each point
    {"kind": "stadium", "a": [x, y], "b": [x, y], "w": w}                        a slot with round ends, a and b the end centres
Closed outlines are written as POLYLINEs (arcs as bulges), which cutting services expect.
"""
import math

# name -> AutoCAD colour index. Laser and CNC geometry never share a layer.
LAYERS = {"CUT_THROUGH": 7, "FOLD_PERFORATION": 1, "CNC_GROOVE": 5, "ENGRAVING": 3, "REFERENCE": 8, "FOLD_DIRECTION": 4}


def stadium_poly(e):
    (ax, ay), (bx, by), h = e["a"], e["b"], e["w"] / 2
    n = math.hypot(bx - ax, by - ay) or 1.0
    nx, ny = -(by - ay) / n * h, (bx - ax) / n * h      # left of a -> b
    return {"kind": "poly", "closed": True, "pts": [[ax - nx, ay - ny], [bx - nx, by - ny], [bx + nx, by + ny], [ax + nx, ay + ny]],
            "bulges": [0, 1, 0, 1]}


def _g(*pairs):
    return "".join(f"{c}\n{v}\n" for c, v in pairs)


def _n(v):
    return f"{v:.4f}"


def write(path, layers):
    """layers: {layer name: [entity, ...]}. Unknown layer names are refused."""
    out = [_g((0, "SECTION"), (2, "HEADER"), (9, "$ACADVER"), (1, "AC1009"), (9, "$INSUNITS"), (70, 4), (0, "ENDSEC")),
           _g((0, "SECTION"), (2, "TABLES"), (0, "TABLE"), (2, "LAYER"), (70, len(LAYERS)))]
    for name, colour in LAYERS.items():
        out.append(_g((0, "LAYER"), (2, name), (70, 0), (62, colour), (6, "CONTINUOUS")))
    out.append(_g((0, "ENDTAB"), (0, "ENDSEC"), (0, "SECTION"), (2, "ENTITIES")))
    for layer, ents in layers.items():
        if layer not in LAYERS:
            raise ValueError(f"unknown DXF layer {layer}")
        for e in ents:
            if e["kind"] == "stadium":
                e = stadium_poly(e)
            if e["kind"] == "line":
                out.append(_g((0, "LINE"), (8, layer), (10, _n(e["a"][0])), (20, _n(e["a"][1])), (11, _n(e["b"][0])), (21, _n(e["b"][1]))))
            elif e["kind"] == "circle":
                out.append(_g((0, "CIRCLE"), (8, layer), (10, _n(e["c"][0])), (20, _n(e["c"][1])), (40, _n(e["r"]))))
            else:
                bulges = e.get("bulges") or [0] * len(e["pts"])
                out.append(_g((0, "POLYLINE"), (8, layer), (66, 1), (70, 1 if e.get("closed", True) else 0)))
                for (x, y), b in zip(e["pts"], bulges):
                    out.append(_g((0, "VERTEX"), (8, layer), (10, _n(x)), (20, _n(y)), *(((42, f"{b:.6f}"),) if b else ())))
                out.append(_g((0, "SEQEND"), (8, layer)))
    out.append(_g((0, "ENDSEC"), (0, "EOF")))
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("".join(out))


def read(path):
    """{layer: [entity, ...]} of the LINE, CIRCLE and POLYLINE entities, in the form write() takes."""
    with open(path, encoding="ascii") as f:
        lines = [ln.strip() for ln in f]
    pairs = [(int(c), v) for c, v in zip(lines[::2], lines[1::2])]
    start = next(i for i, p in enumerate(pairs) if p == (2, "ENTITIES"))
    layers, cur, poly = {}, None, None
    for c, v in pairs[start + 1:]:
        if c == 0:
            if cur and cur["type"] == "VERTEX":
                poly["pts"].append([cur.get(10, 0.0), cur.get(20, 0.0)])
                poly["bulges"].append(cur.get(42, 0.0))
            elif cur and cur["type"] == "LINE":
                layers.setdefault(cur["layer"], []).append({"kind": "line", "a": [cur[10], cur[20]], "b": [cur[11], cur[21]]})
            elif cur and cur["type"] == "CIRCLE":
                layers.setdefault(cur["layer"], []).append({"kind": "circle", "c": [cur[10], cur[20]], "r": cur[40]})
            elif cur and cur["type"] == "POLYLINE":
                poly = {"kind": "poly", "closed": bool(int(cur.get(70, 0)) & 1), "pts": [], "bulges": []}
                layers.setdefault(cur["layer"], []).append(poly)
            cur = {"type": v}
            if v in ("ENDSEC", "EOF"):
                break
        elif c == 8:
            cur["layer"] = v
        elif c in (10, 20, 11, 21, 40, 42, 70):
            cur[c] = float(v)
    return layers


def extent(layers):
    """(xmin, ymin, xmax, ymax) over every entity (arcs counted by their end points and circles in full)."""
    xs, ys = [], []
    for ents in layers.values():
        for e in ents:
            if e["kind"] == "stadium":
                e = stadium_poly(e)
            if e["kind"] == "circle":
                pts = [[e["c"][0] - e["r"], e["c"][1] - e["r"]], [e["c"][0] + e["r"], e["c"][1] + e["r"]]]
            else:
                pts = e["pts"] if e["kind"] == "poly" else [e["a"], e["b"]]
            xs += [p[0] for p in pts]
            ys += [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def counts(layers):
    return {k: len(v) for k, v in layers.items() if v}


# ---------------------------------------------------------------- stroke text
# Cutting services often drop DXF TEXT, so labels are drawn as plain lines: digits as seven
# segments, and the few letters the pipeline writes. A glyph is a list of polylines in a
# 0.6 x 1 box.

_SEG = {"a": [(0, 1), (0.6, 1)], "b": [(0.6, 1), (0.6, 0.5)], "c": [(0.6, 0.5), (0.6, 0)], "d": [(0, 0), (0.6, 0)],
        "e": [(0, 0), (0, 0.5)], "f": [(0, 0.5), (0, 1)], "g": [(0, 0.5), (0.6, 0.5)]}
_DIGITS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgecd", "7": "abc",
           "8": "abcdefg", "9": "abfgcd"}
GLYPHS = {**{ch: [_SEG[s] for s in segs] for ch, segs in _DIGITS.items()},
          "U": [[(0, 1), (0, 0), (0.6, 0), (0.6, 1)]], "N": [[(0, 0), (0, 1), (0.6, 0), (0.6, 1)]],
          "T": [[(0, 1), (0.6, 1)], [(0.3, 1), (0.3, 0)]], "E": [[(0.6, 1), (0, 1), (0, 0), (0.6, 0)], [(0, 0.5), (0.45, 0.5)]],
          "S": [_SEG[s] for s in "afgcd"], "D": [[(0, 0), (0, 1), (0.35, 1), (0.6, 0.75), (0.6, 0.25), (0.35, 0), (0, 0)]],
          "-": [[(0.1, 0.5), (0.5, 0.5)]], " ": []}


def text(s, x, y, height):
    """Line entities spelling `s` with its lower-left corner at (x, y). Characters without a glyph are refused."""
    out = []
    for k, ch in enumerate(s):
        if ch not in GLYPHS:
            raise ValueError(f"no stroke glyph for {ch!r}")
        for poly in GLYPHS[ch]:
            pts = [[x + (k * 0.9 + px) * height, y + py * height] for px, py in poly]
            out += [{"kind": "line", "a": a, "b": b} for a, b in zip(pts, pts[1:])]
    return out


def bulge(a, b, mid):
    """DXF bulge of the arc from a to b through its mid point (positive = counter-clockwise)."""
    cx, cy = b[0] - a[0], b[1] - a[1]
    chord = math.hypot(cx, cy)
    side = (cx * (mid[1] - a[1]) - cy * (mid[0] - a[0])) / chord     # > 0: mid is left of a -> b, so the arc runs clockwise
    return -2 * side / chord
