"""FreeCAD counterpart of sw_params.build (registered as `sw_params` by fc_job.py): a box with
its corner at the origin, outer_length x outer_width x height."""
from fclib import Part, rect


def build(app, params):
    L, W, H = (params[k] for k in ("outer_length", "outer_width", "height"))
    part = Part(app)
    part.extrude("Base_Extrude", [rect(L / 2, W / 2, L, W)], H)
    dims = {"outer_length": "outer_length", "outer_width": "outer_width", "height": "D1@Base_Extrude"}
    part.link(params, dims)
    return part, {"sketch": "Base_Extrude", "dims": dims, "sketch_status": None}
