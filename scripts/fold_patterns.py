"""Fold-line patterns for hand-folded sheet: pure 2D arithmetic, no CAD. A generator takes the
fold's length and a recipe and returns what to cut along the fold line, in the fold's own
coordinate s (mm from the fold's start). sheet_lib places the result on the flat pattern.

Release 1 has one method, "slots": straight interrupted slots in one row. The gaps between
slots, and the uncut length at each end, are the bridges that bend.

    recipe = {"method": "slots", "slot_length": 8, "slot_width": 0.5, "bridge": 1.5, "end_clearance": 2}

slot_width 0 means a single laser pass (a slit one kerf wide).

A rounded fold (`radius` > 0, the inside bend radius) needs a band of material to bend: `rows` rows of
slots `row_pitch` apart across the band, every other row shifted half a slot period so the bridges of
one row sit against slots of the next. sheet_lib works out the band width from the radius and angle.
"""

METHODS = ("slots",)
DEFAULTS = {"slots": {"slot_width": 0.0, "end_clearance": 0.0, "hinge": 0.5, "allowance": 0.0, "relief_d": 0.0,
                      "radius": 0.0, "rows": 1, "row_pitch": 0.0}}
REQUIRED = {"slots": ("slot_length", "bridge")}


def slots(length, r):
    """[(centre s, slot length), ...]: as many full slots as fit between the end clearances, centred,
    so both ends keep at least end_clearance uncut."""
    usable = length - 2 * r["end_clearance"]
    n = int((usable + r["bridge"] + 1e-9) // (r["slot_length"] + r["bridge"]))
    if n < 1:
        return []
    run = n * r["slot_length"] + (n - 1) * r["bridge"]
    s0 = (length - run) / 2 + r["slot_length"] / 2
    return [(s0 + k * (r["slot_length"] + r["bridge"]), r["slot_length"]) for k in range(n)]


def generate(length, recipe):
    return {"slots": slots}[recipe["method"]](length, recipe)


def rows(length, recipe):
    """[(offset across the fold line, [(centre s, slot length), ...]), ...]: one entry per row. Odd rows
    are shifted half a period and keep only the slots that stay inside the end clearances."""
    base, n = generate(length, recipe), int(recipe.get("rows", 1))
    half, out = (recipe["slot_length"] + recipe["bridge"]) / 2, []
    lo, hi = recipe["end_clearance"], length - recipe["end_clearance"]
    for k in range(n):
        off = (k - (n - 1) / 2) * recipe.get("row_pitch", 0.0)
        if k % 2:
            row = [(c + sgn * half, sl) for c, sl in base for sgn in ((-1, 1) if c == base[-1][0] else (-1,))]
            row = [(c, sl) for c, sl in row if c - sl / 2 >= lo - 1e-9 and c + sl / 2 <= hi + 1e-9]
        else:
            row = list(base)
        out.append((off, row))
    return out


def summary(length, recipe):
    """Numbers the validation and the report use."""
    cuts = generate(length, recipe)
    cut = sum(c[1] for c in cuts)
    end = cuts[0][0] - cuts[0][1] / 2 if cuts else length / 2
    return {"slots": len(cuts), "cut_length": round(cut, 4), "bridge_total": round(length - cut, 4),
            "bridge_share": round(1 - cut / length, 4) if length else 1.0, "end_uncut": round(end, 4)}
