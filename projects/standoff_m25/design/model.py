"""M2.5 hex standoff (female-female), centred on the origin, z up from 0."""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from swlib import Part, circle, polygon  # noqa: E402


def hexagon(af):
    r = af / math.sqrt(3)  # corner radius; flats are normal to y
    return [(r * math.cos(math.pi * k / 3), r * math.sin(math.pi * k / 3)) for k in range(6)]


def build(app, p):
    part = Part(app)
    try:
        part.extrude("Hex", [polygon(hexagon(p["af"])), circle(0, 0, p["bore_d"])], p["length"])
        part.link(p, {"D1@Hex": "length"})
    finally:
        part.close_prefs()
    return part.doc
