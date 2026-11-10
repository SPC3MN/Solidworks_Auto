"""Kernel probe: a compression spring as a round wire swept along a helix."""
import fclib


def build(app, p):
    part = fclib.Part()
    part.helix("Coil", p["wire_d"], p["coil_r"], p["pitch"], p["height"])
    part.link(p, {})
    return part.doc
