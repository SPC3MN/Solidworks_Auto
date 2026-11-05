"""Parameter binding: params.json -> SolidWorks Global Variables + equations.

Test 2 of docs/architecture.md. Builds a box whose sketch and extrusion dimensions
are linked to global variables, then edits the 'width' variable in the model and
checks that the rebuild follows it.

Usage: .venv\\Scripts\\python scripts\\sw_params.py
"""
import json
import pathlib

import pythoncom
import win32com.client
from win32com.client import VARIANT

NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
SW_DEFAULT_TEMPLATE_PART = 8      # swDefaultTemplatePart
SW_INPUT_DIM_VAL_ON_CREATE = 10   # swInputDimValOnCreate (modal dimension box)

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT = ROOT / "projects" / "_probe"


def connect():
    try:
        return win32com.client.GetActiveObject("SldWorks.Application")
    except pythoncom.com_error:
        app = win32com.client.Dispatch("SldWorks.Application")
        app.Visible = True
        return app


def dimension_line(model, seg, offset):
    """Dimension one sketch line, placing the text just outside it. Returns full dim name."""
    p0, p1 = seg.GetStartPoint2, seg.GetEndPoint2
    mx, my = (p0.X + p1.X) / 2, (p0.Y + p1.Y) / 2
    model.ClearSelection2(True)
    seg.Select4(False, NOTHING)
    disp = model.AddDimension2(mx + offset[0], my + offset[1], 0)
    if disp is None:
        return None
    # FullName is "D1@Sketch1@Part3.Part"; equations want "D1@Sketch1".
    return "@".join(disp.GetDimension2(0).FullName.split("@")[:2])


def set_global(eqm, name, value_mm):
    """Add or update a global variable '"name" = <value>mm'."""
    text = f'"{name}" = {value_mm}mm'
    for i in range(eqm.GetCount):
        if eqm.Equation(i).replace(" ", "").startswith(f'"{name}"='):
            # Write the Equation(i) property in place. Delete+Add2 breaks the equations
            # that reference this variable, and SetEquationAndConfigurationOption
            # returns -1 under pywin32.
            dispid = eqm._oleobj_.GetIDsOfNames("Equation")
            eqm._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, 0, i, text)
            return 0
    return eqm.Add2(-1, text, True)


def build(app, params):
    model = app.NewDocument(app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_PART), 0, 0, 0)
    L, W, H = (params[k] / 1000 for k in ("outer_length", "outer_width", "height"))

    model.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
    model.SketchManager.InsertSketch(True)
    segs = model.SketchManager.CreateCornerRectangle(0, 0, 0, L, W, 0)
    sketch = model.SketchManager.ActiveSketch
    sketch_name = sketch.Name if sketch is not None else "Sketch1"

    # Pin the corner at the origin so the sketch can be fully constrained.
    model.ClearSelection2(True)
    model.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT", 0, 0, 0, False, 0, NOTHING, 0)
    corner = next(p for s in segs if hasattr(s, "GetStartPoint2")
                  for p in (s.GetStartPoint2, s.GetEndPoint2)
                  if abs(p.X) < 1e-9 and abs(p.Y) < 1e-9)
    corner.Select4(True, NOTHING)
    model.SketchAddConstraints("sgCOINCIDENT")

    dims = {}
    for seg in segs:
        if seg is None or not hasattr(seg, "GetStartPoint2"):
            continue
        p0, p1 = seg.GetStartPoint2, seg.GetEndPoint2
        horizontal = abs(p0.Y - p1.Y) < 1e-9
        key = "outer_length" if horizontal else "outer_width"
        if key in dims:
            continue
        dims[key] = dimension_line(model, seg, (0, -0.01) if horizontal else (-0.01, 0))
    constrained = sketch.GetConstrainedStatus if sketch is not None else None
    model.SketchManager.InsertSketch(True)

    feat = model.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, H, 0, False, False, False, False,
        0, 0, False, False, False, False, True, True, True, 0, 0, False)
    feat.Name = "Base_Extrude"
    dims["height"] = "D1@Base_Extrude"

    eqm = model.GetEquationMgr
    for name, value in params.items():
        set_global(eqm, name, value)
    for name, dim in dims.items():
        eqm.Add2(-1, f'"{dim}" = "{name}"', True)
    model.ForceRebuild3(False)
    return model, {"sketch": sketch_name, "dims": dims, "sketch_status": constrained}


def measure(model):
    b = [v * 1000 for v in model.GetPartBox(True)]
    return [round(b[3] - b[0], 4), round(b[4] - b[1], 4), round(b[5] - b[2], 4)]


def main():
    params = json.loads((PROJECT / "parameters" / "params.json").read_text())
    app = connect()
    prev = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
    try:
        model, info = build(app, params)
        result = {"build": info, "bbox_initial_mm": measure(model)}

        eqm = model.GetEquationMgr
        result["equations"] = [eqm.Equation(i) for i in range(eqm.GetCount)]
        set_global(eqm, "outer_length", 120)
        eqm.EvaluateAll  # returns -1 even on success; the rebuild is what applies it
        model.EditRebuild3
        result["bbox_after_length_120_mm"] = measure(model)
        result["test2_pass"] = result["bbox_after_length_120_mm"][0] == 120.0

        out = PROJECT / ".staging" / "param_box.SLDPRT"
        out.parent.mkdir(parents=True, exist_ok=True)
        app.CloseDoc(str(out))  # a previous run may still hold this file open
        e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        w = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        result["saved"] = bool(model.Extension.SaveAs3(str(out), 0, 1, NOTHING, NOTHING, e, w))
        result["save_errors"] = e.value
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, prev)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
