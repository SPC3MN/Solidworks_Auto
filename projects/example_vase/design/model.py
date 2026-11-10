"""Kernel probe: a freeform part. A vase lofted smoothly through four circles and hollowed by a
second smooth loft. It has no hand volume; the spec checks its sections at the stations."""
import fclib


def build(app, p):
    part = fclib.Part()
    H, t = p["height"], p["wall"]
    stations = [(p["d0"], 0), (p["d1"], p["z1"]), (p["d2"], p["z2"]), (p["d3"], H)]
    part.loft("Body", [(fclib.circle(0, 0, d), z) for d, z in stations])
    # The inside passes through the same stations 2 x wall smaller; it starts at the floor and runs 1 mm past the rim.
    inside = [(p["d0"] - 2 * t - 3, p["floor"]), (p["d1"] - 2 * t, p["z1"]), (p["d2"] - 2 * t, p["z2"]), (p["d3"] - 2 * t, H + 1)]
    part.loft("Inside", [(fclib.circle(0, 0, d), z) for d, z in inside], cut=True)
    part.link(p, {})
    return part.doc
