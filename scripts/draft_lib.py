"""Draft options for the /design skill: parameters, simple bodies, their 2D views, the scorecard,
the fit checks and the approval hashes. Standard library only, so it runs on the host Python.

An option is a folder with two files (see .claude/skills/design/references/schemas.md):

  params.json   every driving value in mm: a number, an expression of other parameters, or
                {"value": ..., "src": "given|measured|chosen|estimated", "note": "..."}
  option.json   the parts, each a list of bodies (box, cyl, revolve, prism; op add or cut) whose
                sizes are expressions of the parameters, plus dims, fit checks and the load path

The same resolved bodies feed the sketch (sketch.py), the 3D massing (fc/fc_massing.py) and the
approval hash, so a sketch, its massing and the approved draft cannot disagree.

Axes: z is up. The section plane is always y = section_y (default 0), seen from -y, so lay the
product out with its main axis in the x-z plane. View coordinates are the two remaining axes in
ascending order, as in fclib: normal y -> (x, z), normal x -> (y, z), normal z -> (x, y).
"""
import ast
import hashlib
import json
import math
import operator
import pathlib

AX = {"x": 0, "y": 1, "z": 2}
SOURCES = ("make", "buy", "library")
SRC = ("given", "measured", "chosen", "estimated")
PRIORITIES = ("must", "should", "free")
OPS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge, ">": operator.gt, "==": None}
ARCH_KEYS = ("mechanism", "layout", "load_path", "process")
EPS = 1e-9


class DraftError(ValueError):
    pass


# ---------------------------------------------------------------- expressions

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod}
_FUNCS = {"min": min, "max": max, "abs": abs, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
          "tan": math.tan, "atan2": math.atan2, "radians": math.radians, "degrees": math.degrees,
          "floor": math.floor, "ceil": math.ceil}
_CONSTS = {"pi": math.pi}


def evaluate(expr, names):
    """Value of a number or an arithmetic expression of `names` (no attribute access, no calls
    beyond the maths functions above)."""
    if isinstance(expr, bool) or expr is None:
        raise DraftError(f"not a number: {expr!r}")
    if isinstance(expr, (int, float)):
        return float(expr)

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if isinstance(n, ast.Name):
            if n.id in names:
                return float(names[n.id])
            if n.id in _CONSTS:
                return _CONSTS[n.id]
            raise DraftError(f"unknown name '{n.id}' in '{expr}'")
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return float(_FUNCS[n.func.id](*[ev(x) for x in n.args]))
        raise DraftError(f"not allowed in an expression: '{expr}'")

    try:
        return ev(ast.parse(str(expr), mode="eval").body)
    except (SyntaxError, ZeroDivisionError, ValueError) as e:
        if isinstance(e, DraftError):
            raise
        raise DraftError(f"cannot evaluate '{expr}': {e}") from None


def resolve_params(raw):
    """{name: {"value": float, "expr": as written, "src": ..., "note": ...}}; expressions may use
    other parameters in any order."""
    out, pending = {}, {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        d = dict(v) if isinstance(v, dict) else {"value": v}
        if d.get("src", "chosen") not in SRC:
            raise DraftError(f"parameter {k}: src must be one of {SRC}")
        pending[k] = {"expr": d["value"], "src": d.get("src", "chosen"), "note": d.get("note", "")}
    while pending:
        values = {k: v["value"] for k, v in out.items()}
        done, last = [], None
        for k, d in pending.items():
            try:
                out[k] = dict(d, value=evaluate(d["expr"], values))
                done.append(k)
            except DraftError as e:
                last = e
        if not done:
            raise DraftError(f"parameters {sorted(pending)} cannot be resolved (unknown name or a cycle): {last}")
        for k in done:
            del pending[k]
    return out


# ---------------------------------------------------------------- bodies

def _poly(profile, names, what):
    pts = [(evaluate(a, names), evaluate(b, names)) for a, b in profile]
    if len(pts) < 3:
        raise DraftError(f"{what}: a profile needs at least 3 points")
    return pts


def resolve_body(b, names, what):
    t, op = b.get("type"), b.get("op", "add")
    if op not in ("add", "cut"):
        raise DraftError(f"{what}: op must be add or cut")
    num = lambda v: evaluate(v, names)  # noqa: E731
    out = {"type": t, "op": op, "at": [num(v) for v in b.get("at", [0, 0, 0])]}
    if len(out["at"]) != 3:
        raise DraftError(f"{what}: at needs [x, y, z]")
    if t == "box":
        out["size"] = [num(v) for v in b["size"]]
        out["r"] = num(b.get("r", 0))
        if min(out["size"]) <= 0 or out["r"] < 0 or 2 * out["r"] > min(out["size"][:2]) + EPS:
            raise DraftError(f"{what}: box size must be positive and r at most half the smaller of x, y")
    elif t == "cyl":
        out.update(d=num(b["d"]), h=num(b["h"]), bore=num(b.get("bore", 0)), axis=b.get("axis", "z"))
        if out["d"] <= 0 or out["h"] <= 0 or not 0 <= out["bore"] < out["d"]:
            raise DraftError(f"{what}: cyl needs d > bore >= 0 and h > 0")
    elif t == "revolve":
        out.update(profile=_poly(b["profile"], names, what), axis=b.get("axis", "z"))
        if min(r for r, _ in out["profile"]) < -EPS:
            raise DraftError(f"{what}: a revolve profile is [radius, along-axis] with radius >= 0")
    elif t == "prism":
        out.update(profile=_poly(b["profile"], names, what), h=num(b["h"]), axis=b.get("axis", "z"))
        if out["h"] <= 0:
            raise DraftError(f"{what}: prism needs h > 0")
    elif t == "slab":
        out.update(base=[[num(v) for v in q] for q in b["base"]], vec=[num(v) for v in b["vec"]])
        if len(out["base"]) < 3 or any(len(q) != 3 for q in out["base"]) or len(out["vec"]) != 3:
            raise DraftError(f"{what}: slab needs a base of 3+ [x, y, z] points (relative to at) and a vec [x, y, z]")
    else:
        raise DraftError(f"{what}: unknown body type {t!r} (box, cyl, revolve, prism, slab)")
    if out.get("axis", "z") not in AX:
        raise DraftError(f"{what}: axis must be x, y or z")
    if "rot" in b:
        r = b["rot"]
        out["rot"] = {"axis": r.get("axis", "x"), "deg": num(r["deg"]), "about": [num(v) for v in r.get("about", [0, 0, 0])]}
        if out["rot"]["axis"] not in AX:
            raise DraftError(f"{what}: rot axis must be x, y or z")
    return out


# ---------------------------------------------------------------- tilted bodies
# A body with "rot" (turned about an axis-parallel line through `about`, absolute) or a "slab" (a flat
# convex plate in any orientation, e.g. a sheet panel folded off-square) is drawn from a point cloud:
# its silhouette and its section are convex hulls, exact for the convex bodies used here.

def is_free(body):
    return body["type"] == "slab" or "rot" in body


def _turn(p, rot):
    a = AX[rot["axis"]]
    i, j = [k for k in range(3) if k != a]
    c, s_ = math.cos(math.radians(rot["deg"])), math.sin(math.radians(rot["deg"]))
    q = [p[k] - rot["about"][k] for k in range(3)]
    out = list(q)
    out[i], out[j] = c * q[i] - s_ * q[j], s_ * q[i] + c * q[j]
    return [out[k] + rot["about"][k] for k in range(3)]


def cloud(body, n=48):
    """Points spanning the body (its convex hull is the body for convex bodies), after any rot."""
    at, t = body["at"], body["type"]
    if t == "slab":
        base = [[at[k] + q[k] for k in range(3)] for q in body["base"]]
        pts = base + [[q[k] + body["vec"][k] for k in range(3)] for q in base]
    elif t == "box":
        sx, sy, sz = body["size"]
        pts = [[at[0] + dx * sx / 2, at[1] + dy * sy / 2, at[2] + dz * sz] for dx in (-1, 1) for dy in (-1, 1) for dz in (0, 1)]
    else:
        a = AX[body["axis"]]
        i, j = _plane(body["axis"])
        if t == "cyl":
            rings = [(body["d"] / 2, 0.0), (body["d"] / 2, body["h"])]
        elif t == "revolve":
            rings = [(r, tt) for r, tt in body["profile"]]
        else:
            rings = None
        pts = []
        if rings is not None:
            for r, tt in rings:
                for m in range(n):
                    q = list(at)
                    q[i] += r * math.cos(2 * math.pi * m / n)
                    q[j] += r * math.sin(2 * math.pi * m / n)
                    q[a] += tt
                    pts.append(q)
        else:
            for u, v in body["profile"]:
                for hh in (0.0, body["h"]):
                    q = list(at)
                    q[i] += u
                    q[j] += v
                    q[a] += hh
                    pts.append(q)
    return [_turn(p, body["rot"]) for p in pts] if "rot" in body else pts


def _hull(pts):
    pts = sorted(set((round(u, 9), round(v, 9)) for u, v in pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])  # noqa: E731
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _plane(axis):
    """Indices of the two in-plane axes for a plane normal to `axis`, ascending."""
    return [i for i in range(3) if i != AX[axis]]


def moved(body, offset):
    return dict(body, at=[a + o for a, o in zip(body["at"], offset)])


def bbox3(body):
    if is_free(body):
        pts = cloud(body)
        return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]
    at, t = body["at"], body["type"]
    if t == "box":
        sx, sy, sz = body["size"]
        return [at[0] - sx / 2, at[1] - sy / 2, at[2]], [at[0] + sx / 2, at[1] + sy / 2, at[2] + sz]
    lo, hi = list(at), list(at)
    a = AX[body["axis"]]
    i, j = _plane(body["axis"])
    if t == "cyl":
        r = body["d"] / 2
        lo[i], hi[i], lo[j], hi[j], hi[a] = at[i] - r, at[i] + r, at[j] - r, at[j] + r, at[a] + body["h"]
    elif t == "revolve":
        r = max(p[0] for p in body["profile"])
        ts = [p[1] for p in body["profile"]]
        lo[i], hi[i], lo[j], hi[j] = at[i] - r, at[i] + r, at[j] - r, at[j] + r
        lo[a], hi[a] = at[a] + min(ts), at[a] + max(ts)
    else:
        us, vs = [p[0] for p in body["profile"]], [p[1] for p in body["profile"]]
        lo[i], hi[i], lo[j], hi[j], hi[a] = at[i] + min(us), at[i] + max(us), at[j] + min(vs), at[j] + max(vs), at[a] + body["h"]
    return lo, hi


def union_box(boxes):
    boxes = list(boxes)
    if not boxes:
        return None
    return [min(b[0][k] for b in boxes) for k in range(3)], [max(b[1][k] for b in boxes) for k in range(3)]


# ---------------------------------------------------------------- 2D geometry
# A shape is a list of subpaths drawn as one even-odd path, so an inner subpath is a hole:
#   ("poly", [(u, v), ...])  or  ("circle", (cu, cv), r)

def _rect(u0, v0, u1, v1):
    return ("poly", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _rrect(u0, v0, u1, v1, r, n=6):
    if r <= EPS:
        return _rect(u0, v0, u1, v1)
    pts = []
    for (cu, cv), a0 in (((u1 - r, v0 + r), -90), ((u1 - r, v1 - r), 0), ((u0 + r, v1 - r), 90), ((u0 + r, v0 + r), 180)):
        pts += [(cu + r * math.cos(math.radians(a0 + 90 * k / n)), cv + r * math.sin(math.radians(a0 + 90 * k / n)))
                for k in range(n + 1)]
    return ("poly", pts)


def crossings(poly, c, k):
    """Sorted coordinates (on the other axis) where a closed polygon crosses the line p[k] = c."""
    out, o = [], 1 - k
    for p, q in zip(poly, poly[1:] + poly[:1]):
        if (p[k] > c) != (q[k] > c):
            out.append(p[o] + (c - p[k]) * (q[o] - p[o]) / (q[k] - p[k]))
    return sorted(out)


def _intervals(poly, c, k):
    xs = crossings(poly, c, k)
    return [(a, b) for a, b in zip(xs[::2], xs[1::2]) if b - a > 1e-7]


def _nudge(poly, c, k):
    """Move c off any vertex so the crossing count stays even."""
    span = max(p[k] for p in poly) - min(p[k] for p in poly) or 1.0
    while any(abs(p[k] - c) < 1e-9 * span for p in poly):
        c += 1e-7 * span
    return c


def _revolve_outer(profile):
    """Half silhouette of a revolve seen from the side: [(r_outer, t), ...] with t ascending."""
    ts = sorted({round(t, 9) for _, t in profile})
    out = []
    for t0, t1 in zip(ts, ts[1:]):
        e = (t1 - t0) * 1e-6
        for t in (t0 + e, t1 - e):
            xs = crossings(profile, t, 1)
            if xs:
                out.append((xs[-1], t0 if t < (t0 + t1) / 2 else t1))
    return out


def _uv(view_normal, body_axis):
    """Which view coordinate (0 = u, 1 = v) the body's axis lies along; None when it is the normal."""
    if view_normal == body_axis:
        return None
    return _plane(view_normal).index(AX[body_axis])


def outline(body, normal):
    """(silhouette shape, hidden shapes) of a body seen along `normal`."""
    i, j = _plane(normal)
    if is_free(body):
        return [("poly", _hull([(p[i], p[j]) for p in cloud(body)]))], []
    at, t = body["at"], body["type"]
    cu, cv = at[i], at[j]
    lo, hi = bbox3(body)
    box = _rect(lo[i], lo[j], hi[i], hi[j])
    if t == "box":
        return [_rrect(lo[i], lo[j], hi[i], hi[j], body["r"]) if normal == "z" else box], []
    k = _uv(normal, body["axis"])
    if t == "cyl":
        r, b = body["d"] / 2, body["bore"] / 2
        if k is None:
            return [("circle", (cu, cv), r)], [[("circle", (cu, cv), b)]] if b else []
        hidden = []
        for s in (-b, b) if b else ():
            c = (cv if k == 0 else cu) + s
            hidden.append([("poly", [(lo[i], c), (hi[i], c)] if k == 0 else [(c, lo[j]), (c, hi[j])])])
        return [box], hidden
    if t == "revolve":
        if k is None:
            rs = [p[0] for p in body["profile"]]
            return [("circle", (cu, cv), max(rs))], [[("circle", (cu, cv), min(rs))]] if min(rs) > EPS else []
        half = _revolve_outer(body["profile"])
        a0 = at[AX[body["axis"]]]
        c = cv if k == 0 else cu
        pt = (lambda r, tt: (a0 + tt, c + r)) if k == 0 else (lambda r, tt: (c + r, a0 + tt))
        sil = [pt(r, tt) for r, tt in half] + [pt(-r, tt) for r, tt in reversed(half)]
        steps = [[("poly", [pt(r, tt), pt(-r, tt)])] for r, tt in half[1:-1]]
        return [("poly", sil)], steps
    if k is None:
        return [("poly", [(cu + a, cv + b) for a, b in body["profile"]])], []
    return [box], []


def section(body, s):
    """Shapes cut from a body by the plane y = s, in (x, z); None when the plane misses it, or
    when the cut cannot be drawn exactly (a revolve whose axis is off the plane)."""
    at, t = body["at"], body["type"]
    lo, hi = bbox3(body)
    if not lo[1] - 1e-9 <= s <= hi[1] + 1e-9:
        return None
    if is_free(body):  # the convex cut: where segments between cloud points cross the plane
        pts = cloud(body, n=24)
        cut = [(p[0], p[2]) for p in pts if abs(p[1] - s) < 1e-9]
        for m, p in enumerate(pts):
            for q in pts[m + 1:]:
                if (p[1] - s) * (q[1] - s) < 0:
                    f = (s - p[1]) / (q[1] - p[1])
                    cut.append((p[0] + f * (q[0] - p[0]), p[2] + f * (q[2] - p[2])))
        h = _hull(cut)
        return [[("poly", h)]] if len(h) >= 3 else None
    if t == "box":
        return [[_rect(lo[0], lo[2], hi[0], hi[2])]]
    ax = body["axis"]
    if t == "cyl":
        r, b = body["d"] / 2, body["bore"] / 2
        if ax == "y":
            return [[("circle", (at[0], at[2]), r)] + ([("circle", (at[0], at[2]), b)] if b else [])]
        e = abs(s - at[1])
        if e >= r:
            return None
        wo, wi = math.sqrt(r * r - e * e), math.sqrt(b * b - e * e) if e < b else 0.0
        spans = [(-wo, -wi), (wi, wo)] if wi > 0 else [(-wo, wo)]
        if ax == "z":
            return [[_rect(at[0] + a, lo[2], at[0] + c, hi[2])] for a, c in spans]
        return [[_rect(lo[0], at[2] + a, hi[0], at[2] + c)] for a, c in spans]
    if t == "revolve":
        prof = body["profile"]
        if ax == "y":
            tt = _nudge(prof, s - at[1], 1)
            return [[("circle", (at[0], at[2]), b)] + ([("circle", (at[0], at[2]), a)] if a > 1e-7 else [])
                    for a, b in _intervals(prof, tt, 1)] or None
        if abs(s - at[1]) > 1e-6:
            return None
        if ax == "z":
            return [[("poly", [(at[0] + sg * r, at[2] + tt) for r, tt in prof])] for sg in (1, -1)]
        return [[("poly", [(at[0] + tt, at[2] + sg * r) for r, tt in prof])] for sg in (1, -1)]
    prof = body["profile"]
    if ax == "y":
        return [[("poly", [(at[0] + a, at[2] + b) for a, b in prof])]]
    if ax == "z":  # profile (x, y): strips in x at this y
        c = _nudge(prof, s - at[1], 1)
        return [[_rect(at[0] + a, lo[2], at[0] + b, hi[2])] for a, b in _intervals(prof, c, 1)] or None
    c = _nudge(prof, s - at[1], 0)  # profile (y, z): strips in z at this y
    return [[_rect(lo[0], at[2] + a, hi[0], at[2] + b)] for a, b in _intervals(prof, c, 0)] or None


def shape_points(shape):
    for sub in shape:
        if sub[0] == "poly":
            yield from sub[1]
        else:
            (cu, cv), r = sub[1], sub[2]
            yield from ((cu - r, cv - r), (cu + r, cv + r))


# ---------------------------------------------------------------- options

def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except ValueError as e:
        raise DraftError(f"{path}: {e}") from None


def strip_notes(o):
    """Drop keys starting with _ (notes), so they never affect a hash."""
    if isinstance(o, dict):
        return {k: strip_notes(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [strip_notes(v) for v in o]
    return o


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def _rounded(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, (list, tuple)):
        return [_rounded(v) for v in o]
    if isinstance(o, dict):
        return {k: _rounded(v) for k, v in o.items()}
    return o


def load_option(folder):
    """Read and resolve one option folder. Raises DraftError with the reason when it is not usable."""
    folder = pathlib.Path(folder)
    raw = strip_notes(load_json(folder / "option.json"))
    params = resolve_params(load_json(folder / "params.json"))
    names = {k: v["value"] for k, v in params.items()}
    oid = folder.name if folder.name != "approved" else raw.get("id", "approved")
    for key in ("name", "summary", "parts"):
        if not raw.get(key):
            raise DraftError(f"option {oid}: '{key}' is missing")
    arch = raw.get("architecture") or {}
    if any(not arch.get(k) for k in ARCH_KEYS):
        raise DraftError(f"option {oid}: architecture needs {', '.join(ARCH_KEYS)}")

    parts, seen = [], set()
    for p in raw["parts"]:
        pid = p.get("id")
        if not pid or pid in seen or not pid.replace("_", "").isalnum():
            raise DraftError(f"option {oid}: part ids must be unique snake_case names (got {pid!r})")
        seen.add(pid)
        if p.get("source") not in SOURCES:
            raise DraftError(f"option {oid}, part {pid}: source must be one of {SOURCES}")
        sheet = None
        if p.get("sheet"):      # a hand-folded sheet part: its folded panels are its bodies
            import sheet_lib
            sheet = sheet_lib.load_sheet(folder / p["sheet"], names)
            bodies = sheet_lib.draft_bodies(sheet, [evaluate(v, names) for v in p.get("at", [0, 0, 0])],
                                            stand=bool(p.get("stand")))
            p = {"process": "fold", "material": sheet["material"], "setups": len(sheet["folds"]), **p}
        else:
            bodies = [resolve_body(b, names, f"option {oid}, part {pid}, body {n}") for n, b in enumerate(p.get("bodies", []))]
        if p.get("rot"):        # the whole part turned about an axis-parallel line (e.g. a face leaning back)
            r = p["rot"]
            rot = {"axis": r.get("axis", "x"), "deg": evaluate(r["deg"], names), "about": [evaluate(v, names) for v in r.get("about", [0, 0, 0])]}
            bodies = [dict(b, rot=rot) for b in bodies]
        ops = [b["op"] for b in bodies]
        if not bodies or ops[0] != "add" or ops != sorted(ops):
            raise DraftError(f"option {oid}, part {pid}: list every add body before the cuts (a cut applies to the whole part)")
        inst = [[evaluate(v, names) for v in at] for at in p.get("instances", [[0, 0, 0]])]
        qty = int(p.get("qty", len(inst)))
        if qty < len(inst):
            raise DraftError(f"option {oid}, part {pid}: qty {qty} is less than its {len(inst)} drawn instances")
        parts.append({"id": pid, "name": p.get("name", pid), "source": p["source"], "process": p.get("process", ""),
                      "material": p.get("material", ""), "qty": qty, "setups": int(p.get("setups", 1)),
                      "fastener": bool(p.get("fastener", False)), "library": p.get("library"),
                      "bodies": bodies, "instances": inst, "sheet": sheet, "sheet_file": p.get("sheet"),
                      "sheet_hash": digest(strip_notes(load_json(folder / p["sheet"]))) if sheet else None})
    for pid in raw.get("load_path", []):
        if (pid["part"] if isinstance(pid, dict) else pid) not in seen:
            raise DraftError(f"option {oid}: load_path names an unknown part {pid!r}")

    opt = {"id": oid, "folder": folder, "name": raw["name"], "summary": raw["summary"], "architecture": arch,
           "params": params, "names": names, "parts": parts, "section_y": evaluate(raw.get("section_y", 0), names),
           "load_path": raw.get("load_path", []), "dims": raw.get("dims", []), "fit": raw.get("fit", []),
           "costs_vs_A": raw.get("costs_vs_A", []), "from_inspiration": raw.get("from_inspiration", []),
           "allowed_interference": raw.get("allowed_interference", []), "merged_from": raw.get("merged_from", [])}
    lo, hi = union_box(bbox3(b) for _, b in solids(opt) if b["op"] == "add")
    opt["bbox"] = (lo, hi)
    opt["scorecard"] = scorecard(opt)
    opt["derived"] = {"bbox_x": hi[0] - lo[0], "bbox_y": hi[1] - lo[1], "bbox_z": hi[2] - lo[2],
                      **{k: opt["scorecard"][k] for k in ("parts_total", "parts_make", "parts_buy", "fasteners", "setups")}}
    opt["fit_results"] = [run_check(f, {**names, **opt["derived"]}, f"option {oid}, fit {f.get('id')}") for f in opt["fit"]]
    opt["part_hashes"] = {p["id"]: digest(_rounded({k: p[k] for k in ("source", "process", "material", "qty", "bodies", "instances")
                                                    + (("sheet_hash",) if p["sheet"] else ())})) for p in parts}
    opt["hash"] = digest([{k: v for k, v in raw.items() if k != "id"}, {k: [v["expr"], v["src"]] for k, v in params.items()}]
                         + [p["sheet_hash"] for p in parts if p["sheet"]])
    return opt


def solids(opt):
    """Every drawn body of the option, moved to its instance position: [(part, body), ...]."""
    return [(p, moved(b, at)) for p in opt["parts"] for at in p["instances"] for b in p["bodies"]]


def scorecard(opt):
    parts = opt["parts"]
    make = [p for p in parts if p["source"] == "make"]
    return {
        "parts_total": sum(p["qty"] for p in parts),
        "parts_unique": len(parts),
        "parts_make": sum(p["qty"] for p in make),
        "parts_buy": sum(p["qty"] for p in parts if p["source"] != "make"),
        "fasteners": sum(p["qty"] for p in parts if p["fastener"]),
        "setups": sum(p["setups"] for p in make),
        "processes": sorted({p["process"] for p in make if p["process"]}),
        "load_path_parts": len({e["part"] if isinstance(e, dict) else e for e in opt["load_path"]}),
    }


def run_check(c, names, what):
    """Evaluate {"lhs", "op", "rhs"}: both sides worked out, so the board can show the numbers."""
    if c.get("op") not in OPS or "lhs" not in c or "rhs" not in c:
        raise DraftError(f"{what}: a check needs lhs, op ({', '.join(OPS)}) and rhs")
    lhs, rhs = evaluate(c["lhs"], names), evaluate(c["rhs"], names)
    tol = float(c.get("tol", 1e-6))
    ok = abs(lhs - rhs) <= tol if c["op"] == "==" else OPS[c["op"]](lhs, rhs) or abs(lhs - rhs) <= 1e-9
    return {"id": c.get("id", ""), "lhs_expr": str(c["lhs"]), "rhs_expr": str(c["rhs"]), "op": c["op"],
            "lhs": round(lhs, 4), "rhs": round(rhs, 4), "margin": round(abs(rhs - lhs), 4), "ok": bool(ok),
            "why": c.get("why", c.get("text", ""))}


# ---------------------------------------------------------------- brief

def load_brief(product):
    b = load_json(pathlib.Path(product) / "brief.json")
    ids = set()
    for r in b.get("requirements", []):
        if not r.get("id") or r["id"] in ids or not r.get("text"):
            raise DraftError(f"brief: every requirement needs a unique id and a text ({r})")
        ids.add(r["id"])
        if r.get("priority") not in PRIORITIES:
            raise DraftError(f"brief {r['id']}: priority must be one of {PRIORITIES}")
        if r.get("provenance") not in SRC:
            raise DraftError(f"brief {r['id']}: provenance must be one of {SRC}")
    return b


def brief_hash(brief):
    """What the owner approves of the brief: requirements, bought parts and defaults. Notes,
    open questions and the conversation log can change without reopening the gate."""
    return digest(strip_notes({k: brief.get(k) for k in ("requirements", "bought_parts", "defaults")}))


def requirement_results(brief, opt):
    """Each requirement with a machine check, evaluated on this option."""
    names = {**opt["names"], **opt["derived"]}
    out = []
    for r in brief.get("requirements", []):
        if not r.get("check"):
            continue
        try:
            res = run_check(r["check"], names, f"brief {r['id']}")
        except DraftError as e:
            res = {"ok": False, "error": str(e), "lhs_expr": str(r["check"].get("lhs")), "rhs_expr": str(r["check"].get("rhs")),
                   "op": r["check"].get("op"), "lhs": None, "rhs": None, "margin": None}
        out.append(dict(res, id=r["id"], priority=r["priority"], why=r["text"]))
    return out


# ---------------------------------------------------------------- the approval gate

def gate(product, part=None):
    """(ok, message): may detail modelling run for this product (or this one part of it)?

    The approval binds the brief and the approved option. A changed brief closes the gate for
    every part; a changed option closes it only for the parts whose bodies changed."""
    product = pathlib.Path(product)
    ap = product / "draft" / "approval.json"
    if not ap.exists():
        return False, "NOT APPROVED: no draft approval. Show the owner the board and the massing, then design_cli.py approve."
    a = load_json(ap)
    try:
        if brief_hash(load_brief(product)) != a["brief_hash"]:
            return False, "NOT APPROVED: brief.json changed after the approval. Run a new round and ask again."
        opt = load_option(product / "draft" / "approved")
    except DraftError as e:
        return False, f"NOT APPROVED: the approved draft cannot be read ({e})."
    if part is None:
        changed = sorted(k for k in set(a["parts"]) | set(opt["part_hashes"]) if a["parts"].get(k) != opt["part_hashes"].get(k))
        if opt["hash"] != a["option_hash"] and changed:
            return False, f"NOT APPROVED: the draft changed after the approval for parts {changed}."
        return True, f"approved {a['approved_at']} (option {a['option']}, round {a['round']})"
    if part not in a["parts"]:
        return False, (f"NOT APPROVED: part '{part}' is not in the approved draft ({', '.join(sorted(a['parts']))}). "
                       "Adding a part is a design change: run a new round.")
    if opt["part_hashes"].get(part) != a["parts"][part]:
        return False, f"NOT APPROVED: part '{part}' changed in the draft after the approval."
    # The part's own parameters may add detail, but a value it shares with the draft must be the approved one.
    pp = product / "parts" / part / "parameters" / "params.json"
    mine = load_json(pp) if pp.exists() else {}
    sp = product / "parts" / part / "sheet.json"      # a folded sheet part keeps its parameters in its definition
    if sp.exists():
        # The recipe (how a fold is made) may change at this stage; the panels and folds may not.
        ap_file = next((x["sheet_file"] for x in opt["parts"] if x["id"] == part and x["sheet_file"]), None)
        same = ap_file and all(strip_notes(load_json(sp)).get(k) == strip_notes(load_json(product / "draft" / "approved" / ap_file)).get(k)
                               for k in ("panels", "folds"))
        if not same:
            return False, f"NOT APPROVED: the panels or folds of part '{part}' differ from the approved draft. Change them through a new round."
        mine = {**mine, **{k: (v.get("value") if isinstance(v, dict) else v) for k, v in load_json(sp).get("params", {}).items()}}
    drift = sorted(k for k, v in mine.items() if k in opt["names"] and isinstance(v, (int, float)) and abs(v - opt["names"][k]) > 1e-9)
    if drift:
        return False, (f"NOT APPROVED: part '{part}' uses {', '.join(f'{k} = {mine[k]:g}' for k in drift)}, but the approved draft says "
                       f"{', '.join(f'{opt['names'][k]:g}' for k in drift)}. Change dimensions through a new round, not in the part.")
    return True, f"approved {a['approved_at']}"
