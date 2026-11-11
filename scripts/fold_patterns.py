"""Fold-line patterns for hand-folded sheet: pure 2D arithmetic, no CAD. A generator takes the
fold's length and a recipe and returns what to cut along the fold line, in the fold's own
coordinate s (mm from the fold's start). sheet_lib places the result on the flat pattern.

Release 1 has one method, "slots": straight interrupted slots in one row. The gaps between
slots, and the uncut length at each end, are the bridges that bend.

    recipe = {"method": "slots", "slot_length": 8, "slot_width": 0.5, "bridge": 1.5, "end_clearance": 2}

slot_width 0 means a single laser pass (a slit one kerf wide).
"""

METHODS = ("slots",)
DEFAULTS = {"slots": {"slot_width": 0.0, "end_clearance": 0.0, "hinge": 0.5, "allowance": 0.0, "relief_d": 0.0}}
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


def summary(length, recipe):
    """Numbers the validation and the report use."""
    cuts = generate(length, recipe)
    cut = sum(c[1] for c in cuts)
    end = cuts[0][0] - cuts[0][1] / 2 if cuts else length / 2
    return {"slots": len(cuts), "cut_length": round(cut, 4), "bridge_total": round(length - cut, 4),
            "bridge_share": round(1 - cut / length, 4) if length else 1.0, "end_uncut": round(end, 4)}
