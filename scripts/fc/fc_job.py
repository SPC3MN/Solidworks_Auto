"""Runs INSIDE FreeCAD (FreeCADCmd): build one project's model.py with fclib, measure it, save
the .FCStd, export STEP and STL, reopen the STEP. Started by pipeline.py --backend freecad
through freecad_run.py, with its arguments as JSON in FC_JOB:

  {"model": ".../design/model.py", "params": {...}, "name": "<project>", "staging": "<dir>",
   "features": ["Feature", "Prefix*", ...], "sections": {"<id>": {"axis": "z", "at": 30}},
   "out_json": "<path>"}

Writes out_json (measurements for the pipeline's checks), or out_json + ".error" with the
traceback when the build fails. The pipeline does the spec checks; this script only measures.
"""
import importlib.util
import json
import os
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import FreeCAD as App  # noqa: E402
import MeshPart  # noqa: E402
import Part as OCC  # noqa: E402

import fc_params  # noqa: E402
import fclib  # noqa: E402

# Model scripts and generators import swlib / sw_params; on this backend those are fclib / fc_params.
sys.modules["swlib"] = fclib
sys.modules["sw_params"] = fc_params


def measure(shape):
    # BoundBox is loose around curved faces (tori, swept tubes: +6 % on an O-ring); the
    # optimal box is tight, like SolidWorks' GetPartBox.
    b = shape.optimalBoundingBox(True, False)
    return {"bbox": [round(b.XLength, 4), round(b.YLength, 4), round(b.ZLength, 4)],
            "bbox_min": [round(b.XMin, 4), round(b.YMin, 4), round(b.ZMin, 4)],
            "volume": round(shape.Volume, 3), "area": round(shape.Area, 3),
            "solid_bodies": len(shape.Solids), "valid": shape.isValid()}


def section(shape, axis, at):
    """Cross-section of the solid by the plane axis = at: its extent along the plane's two
    axes (in fclib's order: (x, y) for z, (x, z) for y, (y, z) for x), its area and its loops."""
    wires = shape.slice(fclib.AXES[axis], at)
    if not wires:
        return None
    b = OCC.makeCompound(wires).optimalBoundingBox(True, False)
    size = [v for k, v in zip("xyz", (b.XLength, b.YLength, b.ZLength)) if k != axis]
    return {"size": [round(v, 4) for v in size], "loops": len(wires),
            "area": round(OCC.makeFace(wires, "Part::FaceMakerBullseye").Area, 4)}


def load_model(path):
    spec = importlib.util.spec_from_file_location("model", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(pathlib.Path(path).parent))
    spec.loader.exec_module(mod)
    return mod


def main(a):
    staging = pathlib.Path(a["staging"])
    part = load_model(a["model"]).build(None, a["params"])
    if isinstance(part, tuple):
        part = part[0]
    shape = part.shape
    m = measure(shape)

    feats = {}
    names = [n for n, _ in part.ops]
    for fname in a.get("features", []):
        group = [n for n in names if n.startswith(fname[:-1])] if fname.endswith("*") else \
            [fname] if fname in names else []
        feats[fname] = round(m["volume"] - part.rebuild(group).Volume, 4) if group else None

    sections = {k: section(shape, v["axis"], v["at"]) for k, v in a.get("sections", {}).items()}

    native = staging / f"{a['name']}.FCStd"
    part.save(native, a["name"])

    step, stl = staging / f"{a['name']}.step", staging / f"{a['name']}.stl"
    shape.exportStep(str(step))
    reopened = None
    if step.exists():
        r = OCC.read(str(step))
        reopened = {"volume": round(r.Volume, 3), "solid_bodies": len(r.Solids)}
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2, Relative=False)
    mesh.write(str(stl))

    return {"freecad_version": ".".join(App.Version()[:3]), "measure": m, "features": feats, "sections": sections,
            "ops": names, "native": str(native), "step": str(step) if step.exists() else None,
            "stl": str(stl) if stl.exists() else None, "step_reopened": reopened}


args = json.loads(os.environ["FC_JOB"])
try:
    out = main(args)
    with open(args["out_json"], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
except Exception:  # noqa: BLE001
    with open(args["out_json"] + ".error", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
