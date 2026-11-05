"""Probe: attach to SolidWorks over COM, build a 100x60x30 mm box, measure it.

Test 1 of docs/architecture.md. Usage: .venv\\Scripts\\python scripts\\sw_probe.py [out_dir]
SolidWorks API lengths are in metres.
"""
import json
import pathlib
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
SW_DEFAULT_TEMPLATE_PART = 8  # swUserPreferenceStringValue_e.swDefaultTemplatePart


def connect():
    try:
        return win32com.client.GetActiveObject("SldWorks.Application"), "attached"
    except pythoncom.com_error:
        app = win32com.client.Dispatch("SldWorks.Application")
        app.Visible = True
        return app, "launched"


def main(out_dir: pathlib.Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    app, how = connect()
    app.CommandInProgress = True  # suppress UI refresh during the build
    result = {"connection": how, "revision": app.RevisionNumber}

    template = app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_PART)
    result["template"] = template
    model = app.NewDocument(template, 0, 0, 0)
    if model is None:
        raise RuntimeError(f"NewDocument failed for template {template!r}")

    L, W, H = 0.100, 0.060, 0.030
    ok = model.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
    if not ok:  # localized templates name the plane differently
        ok = model.Extension.SelectByID2("Plane1", "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
    result["plane_selected"] = bool(ok)
    model.SketchManager.InsertSketch(True)
    model.SketchManager.CreateCornerRectangle(0, 0, 0, L, W, 0)
    model.SketchManager.InsertSketch(True)

    feat = model.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, H, 0, False, False, False, False,
        0, 0, False, False, False, False, True, True, True, 0, 0, False)
    result["extrude_ok"] = feat is not None
    if feat is not None:
        feat.Name = "Base_Extrude"

    model.ForceRebuild3(False)
    box = [v * 1000 for v in model.GetPartBox(True)]
    result["bbox_mm"] = [round(box[3] - box[0], 4), round(box[4] - box[1], 4), round(box[5] - box[2], 4)]
    mp = model.Extension.CreateMassProperty  # no-arg methods surface as properties under late binding
    result["volume_mm3"] = round(mp.Volume * 1e9, 3)
    result["expected_volume_mm3"] = 100 * 60 * 30

    path = out_dir / "probe_box.SLDPRT"
    errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    result["saved"] = bool(model.Extension.SaveAs3(str(path.resolve()), 0, 1, NOTHING, NOTHING, errors, warnings))
    result["save_path"] = str(path)
    app.CommandInProgress = False
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "projects/_probe/.staging"))
