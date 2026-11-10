"""Kernel probe: ruled lofts. A rectangular hopper, hollowed by a second loft used as a cut."""
import fclib


def build(app, p):
    part = fclib.Part()
    H, t = p["height"], p["wall"]
    part.loft("Hopper", [(fclib.rect(0, 0, p["base_l"], p["base_w"]), 0), (fclib.rect(0, 0, p["top_l"], p["top_w"]), H)], ruled=True)
    part.loft("Bore", [(fclib.rect(0, 0, p["base_l"] - 2 * t, p["base_w"] - 2 * t), 0),
                       (fclib.rect(0, 0, p["top_l"] - 2 * t, p["top_w"] - 2 * t), H)], ruled=True, cut=True)
    part.link(p, {})
    return part.doc
