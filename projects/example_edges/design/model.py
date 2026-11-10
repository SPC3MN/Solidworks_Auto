"""Kernel probe: fillet and chamfer on edges chosen by geometry (fclib.edges), not by pick points."""
import fclib


def build(app, p):
    part = fclib.Part()
    H = p["height"]
    part.extrude("Block", [fclib.rect(0, 0, p["length"], p["width"])], H)
    part.fillet("Corners", p["corner_r"], select=fclib.edges(parallel="z"))
    part.chamfer("TopRim", p["rim_c"], select=fclib.edges(on=("z", H)))
    part.cut("Hole", [fclib.circle(0, 0, p["hole_d"])])
    part.chamfer("HoleMouth", p["hole_c"], select=fclib.edges(on=("z", H), radius=p["hole_d"] / 2))
    part.link(p, {})
    return part.doc
