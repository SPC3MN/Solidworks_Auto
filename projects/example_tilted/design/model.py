"""Kernel probe: sketches on tilted planes. A block with a hole drilled 30 deg off vertical and
a round boss standing 20 deg off vertical the other way."""
import fclib


def build(app, p):
    part = fclib.Part()
    H = p["height"]
    part.extrude("Block", [fclib.rect(0, 0, p["length"], p["width"])], H)
    # The plane's origin is where the hole's axis meets the top face; the circle is drawn at (0, 0) on it.
    hole = fclib.plane("z", origin=(p["hole_x"], 0, H)).rotated("y", p["hole_angle"])
    part.cut("TiltHole", [fclib.circle(0, 0, p["hole_d"])], plane=hole)
    # The boss starts boss_root below the surface, so its tilted root disc is wholly inside the block:
    # tilt the plane about the point where the boss's axis meets the top face.
    boss = fclib.plane("z", origin=(p["boss_x"], 0, H - p["boss_root"])).rotated("y", -p["boss_angle"], through=(p["boss_x"], 0, H))
    part.extrude("TiltBoss", [fclib.circle(0, 0, p["boss_d"])], p["boss_root"] + p["boss_len"], plane=boss)
    part.link(p, {})
    return part.doc
