"""2x20 female GPIO socket under a HAT, modelled in Raspberry Pi board coordinates
(centre (32.5, 52.5)), from the Pi header plastic top (z 4.1) to the HAT bottom (z 12.6)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from swlib import Part, rect  # noqa: E402


def build(app, p):
    part = Part(app)
    try:
        cx, cy, pitch = p["cx"], p["cy"], p["pitch"]
        z0, h = p["z0"], p["z1"] - p["z0"]
        part.extrude("Socket_Body", [rect(cx, cy, 20 * pitch, 2 * pitch)], h, z=z0)
        part.cut("Socket_Holes", [rect(cx + (i - 9.5) * pitch, cy + (j - 0.5) * pitch, p["hole"], p["hole"])
                                  for i in range(20) for j in range(2)])
    finally:
        part.close_prefs()
    return part.doc
