"""Closed-form volumes and lengths for the expected values in spec.json: the arithmetic a
requirements.md states, as functions, so a spec never takes its numbers from a CAD run.
Standard library only. Each formula was checked against FreeCAD 1.1.4 (docs/freecad_findings.md).

All lengths in mm, volumes in mm^3, angles in degrees.
"""
import math


def polygon_area(points):
    """Area of a closed polygon [(a, b), ...] (positive either way round)."""
    return abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(points, points[1:] + points[:1]))) / 2


def polygon_centroid(points):
    s = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(points, points[1:] + points[:1])) / 2
    cx = sum((p[0] + q[0]) * (p[0] * q[1] - q[0] * p[1]) for p, q in zip(points, points[1:] + points[:1])) / (6 * s)
    cy = sum((p[1] + q[1]) * (p[0] * q[1] - q[0] * p[1]) for p, q in zip(points, points[1:] + points[:1])) / (6 * s)
    return cx, cy


def revolve_volume(points, angle=360.0):
    """Polygon [(radius, along-axis), ...] turned about the axis (Pappus): angle x centroid radius x area."""
    return math.radians(angle) * polygon_centroid(points)[0] * polygon_area(points)


def prismatoid(area_0, area_mid, area_1, height):
    """Ruled loft between two parallel sections: h/6 (A0 + 4 Am + A1). The mid section is the
    section halfway up; for two rectangles or two circles it has the mean sides or the mean radius."""
    return height / 6 * (area_0 + 4 * area_mid + area_1)


def frustum(d0, d1, height):
    """Ruled loft between two coaxial circles."""
    return math.pi * height / 12 * (d0 * d0 + d0 * d1 + d1 * d1)


def fillet_edge(r, length):
    """Removed by a fillet of radius r along a straight convex 90 degree edge (added on a concave one)."""
    return (1 - math.pi / 4) * r * r * length


def chamfer_edge(c, length):
    """Removed by an equal-leg chamfer c along a straight 90 degree edge."""
    return c * c / 2 * length


def fillet_rim(r, rim_radius, outside=True, angle=360.0):
    """Removed by a fillet of radius r on a circular 90 degree edge of radius rim_radius: the
    outer rim of a cylinder (outside=True) or the mouth of a hole (outside=False)."""
    off = r * (10 - 3 * math.pi) / (3 * (4 - math.pi))  # centroid of the removed corner, from the sharp edge
    return math.radians(angle) * (rim_radius - off if outside else rim_radius + off) * (1 - math.pi / 4) * r * r


def chamfer_rim(c, rim_radius, outside=True, angle=360.0):
    """Removed by a chamfer c on a circular 90 degree edge of radius rim_radius (see fillet_rim)."""
    return math.radians(angle) * (rim_radius - c / 3 if outside else rim_radius + c / 3) * c * c / 2


def helix_length(radius, pitch, height):
    return height / pitch * math.hypot(2 * math.pi * radius, pitch)


def helix_volume(d, radius, pitch, height):
    """Round wire of diameter d swept along a helix, ends cut square to the wire."""
    return math.pi * d * d / 4 * helix_length(radius, pitch, height)


def tilted_hole(d, thickness, angle):
    """Removed by a round hole through a plate, its axis `angle` degrees off the plate's normal.
    Holds while both elliptical mouths lie wholly on the plate's faces."""
    return math.pi * d * d / 4 * thickness / math.cos(math.radians(angle))
