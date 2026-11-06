"""Straight plug-and-cable parts built from coaxial segments along -y, with an optional
vertical drop at the cable end.

Local axes: the plug's mating face is the plane y = 0 and the cable runs toward -y.
The cable axis is at x = 0, z = 0. Segment shapes, drawn on Y-normal planes as (x, z) profiles:
  {"shape": "circle", "d", "y0", "len"}       solid cylinder from y0 toward -y
  {"shape": "rect", "w", "h", "y0", "len"}    box (w along x, h along z)
  {"shape": "ring", "od", "id", "y0", "len", "fwd": true}  tube toward +y (a sleeve over a socket)
"lead": {"d", "axis", "at", "path"} is the flexible lead, swept as a round bar along a path of
lines and tangent arcs (swlib.path) drawn on the plane normal to `axis`. The path starts on the end
face of the last segment, so its volume is area × path length.
"""
import math

from swlib import Part, circle, path_length, rect


def area(s):
    if s["shape"] == "circle":
        return math.pi * s["d"] ** 2 / 4
    if s["shape"] == "rect":
        return s["w"] * s["h"]
    return math.pi * (s["od"] ** 2 - s["id"] ** 2) / 4


def profiles(s):
    if s["shape"] == "circle":
        return [circle(0, 0, s["d"])]
    if s["shape"] == "rect":
        return [rect(0, 0, s["w"], s["h"])]
    return [circle(0, 0, s["od"]), circle(0, 0, s["id"])]


def expected(p):
    vol = sum(area(s) * s["len"] for s in p["segments"])
    ld = p.get("lead")
    if ld:  # swept round lead: area x path length (Pappus; bend radii exceed the cable radius)
        vol += math.pi * ld["d"] ** 2 / 4 * path_length(ld["path"])
    return round(vol, 3)


def build(app, p):
    part = Part(app)
    try:
        for i, s in enumerate(p["segments"]):
            name = s.get("name", f"Seg_{i + 1}")
            part.extrude(name, profiles(s), s["len"], z=s["y0"], down=not s.get("fwd"), axis="y")
        ld = p.get("lead")
        if ld:
            part.sweep("Lead", ld["d"], ld["path"], at=ld.get("at", 0), axis=ld["axis"])
    finally:
        part.close_prefs()
    return part.doc
