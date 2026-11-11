"""Hand-folded sheet parts: panels joined in a tree by folds, unfolded to a flat pattern and folded
to a rigid 3D model. Standard library only (docs/folded_enclosure_plan.md).

Three layers that stay independent:

  panels    polygons (counter-clockwise, mm, in the panel's own frame, seen from the face that is
            up in the flat pattern) with holes and cutouts. Edge i runs from point i to point i + 1.
  folds     parent panel + edge, child panel + edge, angle, direction, sequence, and a recipe NAME.
            The child's whole edge lies on the parent's edge, centred unless `offset` says where.
  recipes   the manufacturing method and its numbers (fold_patterns.py). A recipe also says where
            the rigid hinge sits through the thickness (`hinge`, 0 = the face away from the fold,
            1 = the face the fold closes toward; 0.5 for bridges that bend at mid-thickness) and
            how much flat length the fold takes (`allowance`, 0 until a coupon has measured it).

Changing a fold's recipe changes the flat pattern and the preview, never the panels or folds.

Flat pattern: the root panel keeps its own frame; each child is laid against its parent's edge.
Folded model: the sheet is z = 0..t in the flat pattern and a fold with direction "up" turns the
child toward +z, so the flat pattern's upper face becomes the inside.
"""
import math
import pathlib

import draft_lib as D
import fold_patterns as FP

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "libraries" / "sheet"
LEVELS = ("geometric", "manufacturable", "experimental")
LEVEL_NAMES = {"geometric": "geometrically valid", "manufacturable": "manufacturable", "experimental": "experimentally validated"}


class SheetError(D.DraftError):
    pass


def profile(kind, name):
    data = D.load_json(LIB / f"{kind}.json")
    if name not in data or name.startswith("_"):
        raise SheetError(f"no {kind} profile '{name}' in {LIB / (kind + '.json')}")
    return data[name]


# ---------------------------------------------------------------- 2D and 3D helpers

def area(pts):
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1])) / 2


def inside(p, poly):
    return len([x for x in D.crossings(poly, p[1], 1) if x > p[0]]) % 2 == 1


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1.0)))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def edge_dist(p, poly):
    return min(seg_dist(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def _apply(xf, p):
    c, s, tx, ty = xf
    return [c * p[0] - s * p[1] + tx, s * p[0] + c * p[1] + ty]


def _move(ent, xf):
    if ent["kind"] == "circle":
        return dict(ent, c=_apply(xf, ent["c"]))
    if ent["kind"] == "stadium":
        return dict(ent, a=_apply(xf, ent["a"]), b=_apply(xf, ent["b"]))
    return dict(ent, pts=[_apply(xf, p) for p in ent["pts"]])


def ent_points(e):
    """Boundary sample points of an entity, and its half-width, for clearance checks."""
    if e["kind"] == "circle":
        return [e["c"]], e["r"]
    if e["kind"] == "stadium":
        return [e["a"], e["b"]], e["w"] / 2
    return e["pts"], 0.0


def rot3(p, o, u, deg):
    """p turned about the line through o along unit vector u (right-hand rule)."""
    a, v = math.radians(deg), [p[k] - o[k] for k in range(3)]
    c, s = math.cos(a), math.sin(a)
    cr = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    dot = sum(u[k] * v[k] for k in range(3))
    return [o[k] + v[k] * c + cr[k] * s + u[k] * dot * (1 - c) for k in range(3)]


# ---------------------------------------------------------------- loading

def _feature(f, ev, what):
    t = f.get("type")
    at = [ev(v) for v in f.get("at", [0, 0])]
    if t == "circle":
        return {"kind": "circle", "c": at, "r": ev(f["d"]) / 2}
    if t == "rect":
        w, h = (ev(v) for v in f["size"])
        return {"kind": "poly", "closed": True, "pts": [[at[0] - w / 2, at[1] - h / 2], [at[0] + w / 2, at[1] - h / 2],
                                                         [at[0] + w / 2, at[1] + h / 2], [at[0] - w / 2, at[1] + h / 2]]}
    if t == "slot":
        length, w, ang = ev(f["length"]), ev(f["width"]), math.radians(ev(f.get("angle", 0)))
        h = (length - w) / 2
        return {"kind": "stadium", "w": w, "a": [at[0] - h * math.cos(ang), at[1] - h * math.sin(ang)],
                "b": [at[0] + h * math.cos(ang), at[1] + h * math.sin(ang)]}
    if t == "polygon":
        return {"kind": "poly", "closed": True, "pts": [[ev(a), ev(b)] for a, b in f["points"]]}
    raise SheetError(f"{what}: unknown feature type {t!r} (circle, rect, slot, polygon)")


def load_sheet(path, names=None):
    """Read and resolve a sheet definition (a file, or a folder holding sheet.json). `names` are
    outside parameter values (a /design option's) that override the sheet's own of the same name."""
    path = pathlib.Path(path)
    path = path / "sheet.json" if path.is_dir() else path
    return resolve(D.load_json(path), names, path.parent.name if path.name == "sheet.json" else path.stem)


def resolve(raw, names=None, name="sheet"):
    raw = D.strip_notes(raw)
    mat, man = profile("materials", raw.get("material", "")), profile("manufacturing", raw.get("manufacturing", ""))
    t = float(mat["thickness"])
    params = D.resolve_params({"t": {"value": t, "src": "given", "note": "sheet thickness, from the material profile"},
                               **raw.get("params", {}), **{k: v for k, v in (names or {}).items() if k != "t"}})
    vals = {k: v["value"] for k, v in params.items()}
    ev = lambda v: D.evaluate(v, vals)  # noqa: E731

    panels = {}
    for p in raw.get("panels", []):
        pid = p.get("id")
        if not pid or pid in panels:
            raise SheetError(f"panel ids must be unique (got {pid!r})")
        outline = [[ev(a), ev(b)] for a, b in p["outline"]]
        if len(outline) < 3 or area(outline) <= 1e-9:
            raise SheetError(f"panel {pid}: the outline must be a counter-clockwise polygon")
        panels[pid] = {"id": pid, "name": p.get("name", pid), "outline": outline,
                       "features": [_feature(f, ev, f"panel {pid}, feature {n}") for n, f in enumerate(p.get("features", []))]}
    if not panels:
        raise SheetError("a sheet needs at least one panel")

    recipes = {}
    for rname, r in raw.get("recipes", {}).items():
        m = r.get("method")
        if m not in FP.METHODS:
            raise SheetError(f"recipe {rname}: method must be one of {FP.METHODS} in this release")
        missing = [k for k in FP.REQUIRED[m] if k not in r]
        if missing:
            raise SheetError(f"recipe {rname}: missing {missing}")
        rec = {**FP.DEFAULTS[m], **{k: (v if k == "method" else ev(v)) for k, v in r.items()}}
        if not 0 <= rec["hinge"] <= 1 or rec["allowance"] < 0 or rec["slot_length"] <= 0 or rec["bridge"] <= 0:
            raise SheetError(f"recipe {rname}: needs slot_length > 0, bridge > 0, 0 <= hinge <= 1 and allowance >= 0")
        recipes[rname] = rec

    folds, child_of = [], {}
    for f in raw.get("folds", []):
        fid = f.get("id")
        for key in ("parent", "child"):
            if f.get(key) not in panels:
                raise SheetError(f"fold {fid}: unknown {key} panel {f.get(key)!r}")
        if f["child"] in child_of:
            raise SheetError(f"panel {f['child']} hangs from two folds ({child_of[f['child']]} and {fid}): panels form a tree")
        if f.get("recipe") not in recipes:
            raise SheetError(f"fold {fid}: unknown recipe {f.get('recipe')!r}")
        if f.get("direction", "up") not in ("up", "down"):
            raise SheetError(f"fold {fid}: direction is up or down")
        child_of[f["child"]] = fid
        folds.append({"id": fid, "parent": f["parent"], "child": f["child"], "parent_edge": int(f["parent_edge"]),
                      "child_edge": int(f.get("child_edge", 0)), "angle": ev(f.get("angle", 90)), "direction": f.get("direction", "up"),
                      "sequence": int(f.get("sequence", 1)), "recipe": f["recipe"],
                      "offset": ev(f["offset"]) if "offset" in f else None})
    if len({f["id"] for f in folds}) != len(folds) or any(not f["id"] for f in folds):
        raise SheetError("fold ids must be unique")
    roots = [p for p in panels if p not in child_of]
    if len(roots) != 1:
        raise SheetError(f"panels must form one tree; panels with no fold above them: {roots or 'none (a loop)'}")

    sheet = {"name": raw.get("name", name), "material": raw["material"], "manufacturing": raw["manufacturing"], "mat": mat, "man": man,
             "t": t, "params": params, "names": vals, "panels": panels, "folds": folds, "recipes": recipes, "root": roots[0],
             "hardware": raw.get("hardware", []), "dims": raw.get("dims", "outside")}
    _place(sheet)
    return sheet


def _place(sheet):
    """Lay every panel into the flat pattern and work out each fold's geometry."""
    panels, t = sheet["panels"], sheet["t"]
    panels[sheet["root"]]["xf"] = (1.0, 0.0, 0.0, 0.0)
    todo, order = list(sheet["folds"]), []
    while todo:
        ready = [f for f in todo if "xf" in panels[f["parent"]]]
        if not ready:
            raise SheetError(f"folds {[f['id'] for f in todo]} are not connected to the root panel {sheet['root']}")
        for f in ready:
            todo.remove(f)
            order.append(f)
            rec, par, ch = sheet["recipes"][f["recipe"]], panels[f["parent"]], panels[f["child"]]
            P = [_apply(par["xf"], p) for p in par["outline"]]
            p0, p1 = P[f["parent_edge"] % len(P)], P[(f["parent_edge"] + 1) % len(P)]
            c0, c1 = ch["outline"][f["child_edge"] % len(ch["outline"])], ch["outline"][(f["child_edge"] + 1) % len(ch["outline"])]
            lp, L = math.dist(p0, p1), math.dist(c0, c1)
            off = (lp - L) / 2 if f["offset"] is None else f["offset"]
            if L > lp + 1e-6 or off < -1e-6 or off + L > lp + 1e-6:
                raise SheetError(f"fold {f['id']}: the child's edge ({L:g}) does not fit on the parent's edge ({lp:g}) at offset {off:g}")
            d = [(p1[0] - p0[0]) / lp, (p1[1] - p0[1]) / lp]
            n, a = [d[1], -d[0]], rec["allowance"]                    # n points out of the parent
            S = [p0[0] + d[0] * off, p0[1] + d[1] * off]
            E = [S[0] + d[0] * L, S[1] + d[1] * L]
            S2, E2 = [S[0] + n[0] * a, S[1] + n[1] * a], [E[0] + n[0] * a, E[1] + n[1] * a]
            ang = math.atan2(S2[1] - E2[1], S2[0] - E2[0]) - math.atan2(c1[1] - c0[1], c1[0] - c0[0])
            c, s = math.cos(ang), math.sin(ang)
            ch["xf"] = (c, s, E2[0] - (c * c0[0] - s * c0[1]), E2[1] - (s * c0[0] + c * c0[1]))
            up = f["direction"] == "up"
            f.update(length=L, d=d, n=n, s=S, e=E, s2=S2, e2=E2,
                     m0=[S[0] + n[0] * a / 2, S[1] + n[1] * a / 2], m1=[E[0] + n[0] * a / 2, E[1] + n[1] * a / 2],
                     hinge_z=(rec["hinge"] if up else 1 - rec["hinge"]) * t, signed=-f["angle"] if up else f["angle"])
    sheet["folds"] = order
    for p in panels.values():
        p["flat"] = [_apply(p["xf"], q) for q in p["outline"]]
        p["flat_features"] = [_move(e, p["xf"]) for e in p["features"]]
    for f in order:      # every panel that moves when this fold moves
        sub, grew = {f["child"]}, True
        while grew:
            more = {g["child"] for g in order if g["parent"] in sub} - sub
            sub, grew = sub | more, bool(more)
        f["subtree"] = sorted(sub)


# ---------------------------------------------------------------- flat pattern

def fold_entities(sheet, f):
    """(perforation entities, relief circles) of one fold, in flat-pattern coordinates."""
    rec, cuts = sheet["recipes"][f["recipe"]], []
    at = lambda s: [f["m0"][0] + f["d"][0] * s, f["m0"][1] + f["d"][1] * s]  # noqa: E731
    for sc, sl in FP.generate(f["length"], rec):
        w = rec["slot_width"]
        if w <= 0:
            cuts.append({"kind": "line", "a": at(sc - sl / 2), "b": at(sc + sl / 2)})
        elif sl <= w + 1e-9:
            cuts.append({"kind": "circle", "c": at(sc), "r": w / 2})
        else:
            cuts.append({"kind": "stadium", "a": at(sc - (sl - w) / 2), "b": at(sc + (sl - w) / 2), "w": w})
    relief = [{"kind": "circle", "c": list(p), "r": rec["relief_d"] / 2} for p in (f["m0"], f["m1"])] if rec["relief_d"] > 0 else []
    return cuts, relief


def flat_extent(sheet):
    pts = [q for p in sheet["panels"].values() for q in p["flat"]]
    return min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts)


# ---------------------------------------------------------------- folded model

def final_angles(sheet):
    return {f["id"]: f["signed"] for f in sheet["folds"]}


def states(sheet, steps=4):
    """The folding sequence as a list of {"label", "angles"}: folds with the same sequence number
    move together, each group swept in `steps` steps with earlier groups folded and later ones flat.
    The last state is the finished part."""
    out, groups = [], sorted({f["sequence"] for f in sheet["folds"]})
    for g in groups:
        for k in range(1, steps + 1):
            out.append({"label": f"step {g}, {round(100 * k / steps)} %", "sequence": g, "done": k == steps,
                        "angles": {f["id"]: f["signed"] * (1 if f["sequence"] < g else k / steps if f["sequence"] == g else 0)
                                   for f in sheet["folds"]}})
    return out or [{"label": "flat", "sequence": 0, "done": True, "angles": {}}]


def chain(sheet, pid):
    """Folds between a panel and the root, nearest the panel first."""
    by_child, out = {f["child"]: f for f in sheet["folds"]}, []
    while pid in by_child:
        out.append(by_child[pid])
        pid = by_child[pid]["parent"]
    return out


def folded_vertices(sheet, angles=None):
    """{panel id: (bottom-face points, top-face points)} in 3D after folding."""
    angles = final_angles(sheet) if angles is None else angles
    out = {}
    for pid, p in sheet["panels"].items():
        faces = []
        for z in (0.0, sheet["t"]):
            pts = [[q[0], q[1], z] for q in p["flat"]]
            for f in chain(sheet, pid):
                o, u = [f["m0"][0], f["m0"][1], f["hinge_z"]], [f["d"][0], f["d"][1], 0.0]
                pts = [rot3(q, o, u, angles.get(f["id"], 0.0)) for q in pts]
            faces.append(pts)
        out[pid] = tuple(faces)
    return out


def folded_bbox(sheet, angles=None):
    pts = [q for bottom, top in folded_vertices(sheet, angles).values() for q in bottom + top]
    return [min(q[k] for q in pts) for k in range(3)], [max(q[k] for q in pts) for k in range(3)]


def draft_bodies(sheet, at=(0.0, 0.0, 0.0)):
    """The folded panels as /design draft bodies (prisms), so a folded part can sit in an option.
    Only panels that end up square to the model axes can be drafted."""
    bodies = []
    for pid, (bottom, top) in folded_vertices(sheet).items():
        nrm = [top[0][k] - bottom[0][k] for k in range(3)]
        k = max(range(3), key=lambda i: abs(nrm[i]))
        if abs(abs(nrm[k]) - sheet["t"]) > 1e-6:
            raise SheetError(f"panel {pid} is not square to the model axes after folding: a draft can only show folds in 90 degree steps")
        i, j = [x for x in range(3) if x != k]
        origin = [0.0, 0.0, 0.0]
        origin[k] = min(bottom[0][k], top[0][k]) + at[k]
        bodies.append({"type": "prism", "op": "add", "axis": "xyz"[k], "h": sheet["t"], "at": origin,
                       "profile": [(q[i] + at[i], q[j] + at[j]) for q in bottom]})
    return bodies


# ---------------------------------------------------------------- validation

def _check(out, cid, level, ok, message):
    out.append({"id": cid, "level": level, "ok": bool(ok), "message": message})


def tested_match(sheet, f):
    """The tested entry of the material profile that covers this fold's recipe, or None."""
    rec = sheet["recipes"][f["recipe"]]
    for e in sheet["mat"].get("tested", []):
        r = e.get("recipe", {})
        near = all(abs(r.get(k, -1e9) - rec[k]) <= max(0.1 * abs(rec[k]), 0.05) for k in ("slot_length", "slot_width", "bridge"))
        if e.get("result") == "held" and r.get("method") == rec["method"] and near and e.get("angle", 0) >= f["angle"] - 1e-6:
            return e
    return None


def checks(sheet):
    """Everything that can be checked without a CAD kernel, each tagged with its level. sheet_cli
    adds the kernel's findings (flat overlap, folded interference, the folding sequence)."""
    out, man = [], sheet["man"]
    for pid, p in sheet["panels"].items():
        for n, e in enumerate(p["features"]):
            pts, half = ent_points(e)
            gap = min(edge_dist(q, p["outline"]) for q in pts) - half
            _check(out, f"feature.{pid}.{n}.inside", "geometric", all(inside(q, p["outline"]) for q in pts) and gap > 0,
                   f"panel {pid}, feature {n} lies inside the panel")
            _check(out, f"feature.{pid}.{n}.web", "manufacturable", gap >= man["min_web"] - 1e-9,
                   f"panel {pid}, feature {n}: {gap:.2f} of material to the panel edge (minimum {man['min_web']:g})")
            if e["kind"] == "circle":
                _check(out, f"feature.{pid}.{n}.size", "manufacturable", 2 * e["r"] >= man["min_hole_d"] - 1e-9,
                       f"panel {pid}, feature {n}: hole Ø{2 * e['r']:g} (minimum {man['min_hole_d']:g})")
    for f in sheet["folds"]:
        rec, s = sheet["recipes"][f["recipe"]], FP.summary(f["length"], sheet["recipes"][f["recipe"]])
        fid = f["id"]
        _check(out, f"fold.{fid}.angle", "geometric", 0 < f["angle"] <= 180, f"fold {fid}: angle {f['angle']:g}°")
        _check(out, f"fold.{fid}.pattern", "geometric", s["slots"] >= 1,
               f"fold {fid}: {s['slots']} slots on {f['length']:g} mm, {s['bridge_share'] * 100:.0f} % of the line left as bridges")
        w = rec["slot_width"]
        _check(out, f"fold.{fid}.slot_width", "manufacturable", man["allow_slit"] if w <= 0 else w >= man["min_slot_width"] - 1e-9,
               f"fold {fid}: " + ("slit of one kerf" if w <= 0 else f"slot width {w:g} (minimum {man['min_slot_width']:g})"))
        _check(out, f"fold.{fid}.bridge", "manufacturable", rec["bridge"] >= man["min_bridge"] - 1e-9,
               f"fold {fid}: bridge {rec['bridge']:g} (minimum {man['min_bridge']:g})")
        _check(out, f"fold.{fid}.end", "manufacturable", s["end_uncut"] >= man["min_end_clearance"] - 1e-9,
               f"fold {fid}: {s['end_uncut']:.2f} uncut at each end (minimum {man['min_end_clearance']:g})")
        ch = sheet["panels"][f["child"]]
        depth = max(abs((q[0] - f["s2"][0]) * f["n"][0] + (q[1] - f["s2"][1]) * f["n"][1]) for q in ch["flat"])
        _check(out, f"fold.{fid}.grip", "manufacturable", depth >= man["min_flange"] - 1e-9,
               f"fold {fid}: panel {f['child']} is {depth:.1f} deep from the fold (minimum to grip {man['min_flange']:g})")
        near = [min(seg_dist(q, f["m0"], f["m1"]) for q in ent_points(e)[0]) - ent_points(e)[1]
                for pid in (f["parent"], f["child"]) for e in sheet["panels"][pid]["flat_features"]]
        if near:
            need = man["min_web"] + w / 2
            _check(out, f"fold.{fid}.features", "manufacturable", min(near) >= need - 1e-9,
                   f"fold {fid}: nearest hole or cutout is {min(near):.2f} from the fold line (minimum {need:g})")
        hit = tested_match(sheet, f)
        _check(out, f"fold.{fid}.tested", "experimental", hit is not None,
               f"fold {fid}: recipe {f['recipe']} " + (f"matches coupon {hit.get('coupon', '?')} ({hit.get('date', '')})" if hit else
                                                       f"has no passing coupon in {sheet['material']} at {f['angle']:g}°"))
    return out


def verdicts(all_checks):
    """{level: True/False}: each level judged on its own checks, never rolled into one word."""
    return {lv: all(c["ok"] for c in all_checks if c["level"] == lv) for lv in LEVELS}


def untested(sheet):
    return any(tested_match(sheet, f) is None for f in sheet["folds"])


# ---------------------------------------------------------------- templates

def tray(length, width, height, flange=0.0, dims="outside", flange_walls=("front", "right", "rear", "left"), hole_d=3.4,
         material="5052-H32_1.0", manufacturing="generic_untested", name="tray"):
    """Definition of an open tray: a base, four walls folded up and, with flange > 0, a return
    flange with two fastener holes on each named wall. Sizes are outside or inside sizes.

    Walls stop short of the corners by the thickness the neighbouring wall takes up, so the folded
    corners are open and nothing collides; flanges stop short of each other the same way."""
    out = dims == "outside"
    fl = flange > 0
    params = {
        "L": {"value": length, "src": "given"}, "W": {"value": width, "src": "given"}, "H": {"value": height, "src": "given"},
        "hinge": {"value": 0.5, "src": "estimated", "note": "bridges bend at mid-thickness until a coupon says otherwise"},
        "allow": {"value": 0.0, "src": "estimated", "note": "flat length taken by a fold; 0 until measured"},
        "corner": {"value": 0.3, "src": "chosen", "note": "clearance between neighbouring walls at a corner"},
        "bl": "L - 2*hinge*t - allow" if out else "L + 2*(1 - hinge)*t - allow",
        "bw": "W - 2*hinge*t - allow" if out else "W + 2*(1 - hinge)*t - allow",
        "wh": ("H - 2*hinge*t - allow" if out else "H + 2*(1 - hinge)*t - allow") if fl else
              ("H - hinge*t - allow/2" if out else "H + (1 - hinge)*t - allow/2"),
        "inset": "(1 - hinge)*t + corner",
    }
    if fl:
        params.update(fw={"value": flange, "src": "given"}, hole_d={"value": hole_d, "src": "chosen", "note": "M3 clearance"},
                      fin="fw + t + corner")
    rect = lambda a, b: [[0, 0], [a, 0], [a, b], [0, b]]  # noqa: E731
    panels = [{"id": "base", "name": "Base", "outline": rect("bl", "bw")}]
    folds = []
    for edge, wall in enumerate(("front", "right", "rear", "left")):
        run = "bl" if edge % 2 == 0 else "bw"
        wl = f"{run} - 2*inset"
        panels.append({"id": wall, "name": f"{wall.capitalize()} wall", "outline": rect(wl, "wh")})
        folds.append({"id": f"f_{wall}", "parent": "base", "parent_edge": edge, "child": wall, "child_edge": 0,
                      "angle": 90, "direction": "up", "sequence": 2 if fl else 1, "recipe": "fold"})
        if fl and wall in flange_walls:
            fln = f"{wl} - 2*fin"
            panels.append({"id": f"{wall}_flange", "name": f"{wall.capitalize()} flange", "outline": rect(fln, "fw"),
                           "features": [{"type": "circle", "d": "hole_d", "at": [f"({fln})*{k}", "fw/2"]} for k in (0.2, 0.8)]})
            folds.append({"id": f"f_{wall}_flange", "parent": wall, "parent_edge": 2, "child": f"{wall}_flange", "child_edge": 0,
                          "angle": 90, "direction": "up", "sequence": 1, "recipe": "fold"})
    return {"name": name, "material": material, "manufacturing": manufacturing, "dims": dims, "params": params, "panels": panels,
            "folds": folds,
            "recipes": {"fold": {"_comment": "A starting guess for 1.0 mm 5052-H32. UNTESTED until a coupon holds.",
                                 "method": "slots", "slot_length": 8.0, "slot_width": 0.5, "bridge": 1.5, "end_clearance": 2.0,
                                 "hinge": "hinge", "allowance": "allow"}},
            "hardware": [{"name": "M3 screw", "qty": 2 * len(flange_walls)}] if fl else []}
