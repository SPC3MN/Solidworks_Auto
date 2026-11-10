"""Runs INSIDE FreeCAD (started by tests/test_kernel.py): builds small shapes with the fclib
kernel ops and writes {"name": [measured, expected]} pairs, the expected side from handcalc."""
import json
import math
import os
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts" / "fc"), str(ROOT / "scripts")]

import fclib  # noqa: E402
import handcalc as hc  # noqa: E402

out, pi = {}, math.pi


def vol(build):
    part = fclib.Part()
    build(part)
    return part.shape.Volume


def bbox(part):
    b = part.shape.optimalBoundingBox(True, False)
    return [round(b.XLength, 4), round(b.YLength, 4), round(b.ZLength, 4)]


def run():
    ring = [(5, 0), (10, 0), (10, 4), (5, 4)]
    # revolve about each axis, partial angles, off-origin axes
    out["revolve_z"] = [vol(lambda p: p.revolve("R", [fclib.polygon(ring)])), hc.revolve_volume(ring)]
    out["revolve_quarter"] = [vol(lambda p: p.revolve("R", [fclib.polygon(ring)], angle=90)), hc.revolve_volume(ring, 90)]
    for about in "xy":
        p = fclib.Part()
        prof = [(t, r) for r, t in ring] if about == "x" else ring     # (x, y): radius is y about x, x about y
        p.revolve("R", [fclib.polygon(prof)], about=about)
        out[f"revolve_{about}"] = [p.shape.Volume, hc.revolve_volume(ring)]
        out[f"revolve_{about}_bbox"] = [bbox(p), [4, 20, 20] if about == "x" else [20, 4, 20]]
    p = fclib.Part()
    p.revolve("R", [fclib.polygon([(30 + r, t) for r, t in ring])], at=(30, 7, 0))
    b = p.shape.BoundBox
    out["revolve_at"] = [[round(p.shape.Volume, 3), round(b.Center.x, 4), round(b.Center.y, 4)], [round(hc.revolve_volume(ring), 3), 30, 7]]
    p = fclib.Part()
    p.extrude("B", [fclib.circle(0, 0, 30)], 10)
    p.revolve("G", [fclib.polygon([(16, 3), (13, 5), (16, 7)])], cut=True)   # runs 1 past the Ø30 surface
    out["revolve_cut"] = [pi * 225 * 10 - p.shape.Volume, hc.revolve_volume([(15, 5 - 4 / 3), (13, 5), (15, 5 + 4 / 3)])]
    try:
        fclib.Part().revolve("X", [fclib.polygon([(-2, 0), (5, 0), (5, 4), (-2, 4)])])
        out["revolve_crossing_refused"] = [False, True]
    except ValueError:
        out["revolve_crossing_refused"] = [True, True]

    # planes: an untilted Plane is the axis plane; a tilted extrude keeps its volume; rotated() pivots
    out["plane_same_as_axis"] = [vol(lambda p: p.extrude("B", [fclib.rect(1, 2, 10, 6)], 5, plane=fclib.plane("y", 3))),
                                 vol(lambda p: p.extrude("B", [fclib.rect(1, 2, 10, 6)], 5, z=3, axis="y"))]
    tilt = fclib.plane("z", origin=(5, 0, 2)).rotated("x", 40)
    out["tilted_extrude"] = [vol(lambda p: p.extrude("B", [fclib.rect(0, 0, 10, 6)], 5, plane=tilt)), 300]
    n = fclib.plane("z").rotated("y", 90).normal
    out["rotated_normal"] = [[round(n.x, 6), round(n.y, 6), round(n.z, 6)], [1, 0, 0]]
    q = fclib.plane("z", origin=(0, 0, 4)).rotated("y", 90, through=(0, 0, 0)).origin
    out["rotated_through"] = [[round(q.x, 6), round(q.y, 6), round(q.z, 6)], [4, 0, 0]]
    out["tilted_hole"] = [48000 - vol(lambda p: (p.extrude("B", [fclib.rect(0, 0, 60, 40)], 20),
                                                 p.cut("H", [fclib.circle(0, 0, 8)], plane=fclib.plane("z", origin=(0, 0, 20)).rotated("x", 25)))),
                          hc.tilted_hole(8, 20, 25)]

    # lofts
    out["loft_cone"] = [vol(lambda p: p.loft("L", [(fclib.circle(0, 0, 40), 0), (fclib.circle(0, 0, 20), 30)], ruled=True)), hc.frustum(40, 20, 30)]
    out["loft_rect"] = [vol(lambda p: p.loft("L", [(fclib.rect(0, 0, 50, 40), 0), (fclib.rect(0, 0, 30, 20), 30)], ruled=True)),
                        hc.prismatoid(2000, 1200, 600, 30)]
    out["loft_three_ruled"] = [vol(lambda p: p.loft("L", [(fclib.circle(0, 0, 40), 0), (fclib.circle(0, 0, 20), 30), (fclib.circle(0, 0, 30), 50)], ruled=True)),
                               hc.frustum(40, 20, 30) + hc.frustum(20, 30, 20)]
    out["loft_y_axis"] = [vol(lambda p: p.loft("L", [(fclib.rect(0, 0, 10, 10), 0), (fclib.rect(0, 0, 10, 10), 25)], ruled=True, axis="y")), 2500]
    p = fclib.Part()
    p.loft("L", [(fclib.rect(0, 0, 40, 30), 0), (fclib.circle(0, 0, 20), 25)])
    out["loft_rect_to_circle_valid"] = [p.shape.isValid() and len(p.shape.Solids) == 1, True]

    # helix, right and left hand
    for left in (False, True):
        p = fclib.Part()
        p.helix("C", 2, 10, 4, 20, z=5, left=left)
        out[f"helix_{'left' if left else 'right'}"] = [p.shape.Volume, hc.helix_volume(2, 10, 4, 20)]
        out[f"helix_{'left' if left else 'right'}_zmin"] = [round(p.shape.optimalBoundingBox(True, False).ZMin, 2), 4.0]

    # edge selection, fillet and chamfer
    p = fclib.Part()
    p.extrude("B", [fclib.circle(0, 0, 20)], 20)
    s = p.shape
    out["cyl_edges_parallel_z_skips_seam"] = [len(fclib.edges(parallel="z")(s)), 0]
    out["cyl_edges_radius"] = [len(fclib.edges(radius=10)(s)), 2]
    out["cyl_edges_top"] = [len(fclib.edges(radius=10, on=("z", 20))(s)), 1]
    p.fillet("F", 2, select=fclib.edges(on=("z", 20)))
    p.chamfer("C", 1.5, select=fclib.edges(on=("z", 0)))
    out["cyl_rim_fillet_chamfer"] = [pi * 100 * 20 - p.shape.Volume, hc.fillet_rim(2, 10) + hc.chamfer_rim(1.5, 10)]
    p = fclib.Part()
    p.extrude("B", [fclib.rect(0, 0, 40, 30)], 10)
    out["box_edges"] = [[len(fclib.edges(parallel=a)(p.shape)) for a in "xyz"] + [len(fclib.edges(on=("z", 10))(p.shape)),
                        len(fclib.edges(box=((-21, -16, 9), (21, -14, 11)))(p.shape))], [4, 4, 4, 4, 1]]
    p.chamfer("C", 2, edge_points=[(0, -15, 10)])
    p.cut("H", [fclib.circle(0, 0, 10)])
    p.fillet("M", 1, select=fclib.edges(radius=5, on=("z", 10)))
    out["box_chamfer_point_and_hole_fillet"] = [12000 - p.shape.Volume, hc.chamfer_edge(2, 40) + pi * 25 * 10 + hc.fillet_rim(1, 5, outside=False)]
    try:
        fclib.Part().extrude("B", [fclib.rect(0, 0, 4, 4)], 4)
        q = fclib.Part()
        q.extrude("B", [fclib.rect(0, 0, 4, 4)], 4)
        q.fillet("F", 1, select=fclib.edges(radius=99))
        out["empty_selection_refused"] = [False, True]
    except RuntimeError:
        out["empty_selection_refused"] = [True, True]


try:
    run()
except Exception:  # noqa: BLE001
    out["error"] = [traceback.format_exc(), ""]
with open(os.environ["FC_JOB"].strip('"'), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
