"""Open-top tray with four floor holes. Fuse first (block), then hollow, then cut."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from swlib import Part, circle, rect  # noqa: E402


def build(app, p):
    part = Part(app)
    try:
        part.extrude("Body_Block", [rect(0, 0, p["length"], p["width"], p["corner_radius"])],
                     p["height"])
        part.shell("Body_Shell", p["wall"], open_face_points=[(0, 0, p["height"])])
        dx, dy, d = p["hole_dx"], p["hole_dy"], p["hole_d"]
        part.cut("Floor_Holes", [circle(sx * dx, sy * dy, d) for sx in (-1, 1) for sy in (-1, 1)],
                 depth=None, z=0, down=False)
        part.link(p, {"D1@Body_Block": "height", "D1@Body_Shell": "wall"})
    finally:
        part.close_prefs()
    return part.doc
