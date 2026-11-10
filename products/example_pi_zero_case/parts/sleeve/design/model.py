"""Model script for the example case's sleeve (option A of products/example_pi_zero_case).

Every size comes from parameters/params.json, which design_cli.py params writes from the approved draft.
"""
import fclib


def build(app, p):
    part = fclib.Part()
    z_b, open_x = p["z_b"], p["inner_l"] / 2
    part.extrude("Body", [fclib.rect(-p["wall"] / 2, 0, p["inner_l"] + p["wall"], p["outer_w"])], p["outer_h"])
    # both cavity cuts start at the open end (+x) and stop at the closed end's wall
    upper_h = p["inner_h"] - p["under_h"]
    part.cut("Cavity", [fclib.rect(0, z_b + upper_h / 2, p["inner_w"], upper_h)], p["inner_l"], z=open_x, axis="x")
    part.cut("Channel", [fclib.rect(0, p["wall"] + p["under_h"] / 2, p["inner_w"] - 2 * p["rail"], p["under_h"])],
             p["inner_l"], z=open_x, axis="x")
    # port slot through the -y wall, from the HDMI end out to the open end
    slot_l, slot_h = open_x + p["win_l"] / 2, p["comp_h"] + p["head"]
    part.cut("PortSlot", [fclib.rect(open_x - slot_l / 2, z_b + p["pcb_t"] + slot_h / 2, slot_l, slot_h)],
             p["wall"], z=-p["outer_w"] / 2, down=False, axis="y")
    part.link(p, {})
    return part.doc
