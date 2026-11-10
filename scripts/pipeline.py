"""Build -> validate -> export -> reopen -> promote, for one project.

Usage:
  .venv\\Scripts\\python scripts\\pipeline.py projects\\example_box
  .venv\\Scripts\\python scripts\\pipeline.py projects\\example_box --override outer_length=118
  python3 scripts/pipeline.py projects/example_box --backend freecad

--backend solidworks (default on Windows) or freecad (default elsewhere; CAD_BACKEND overrides
the default). FreeCAD builds model.py with scripts/fc/fclib.py inside FreeCADCmd and the check
renders come from Blender, since headless FreeCAD has no viewport.

spec.json normally carries a hand-computed "volume". A freeform part (a smooth loft) has none:
leave it out and give "sections" instead, {"<id>": {"axis": "z", "at": 30, "size": [24, 24],
"tol": 0.05, "area": 452.39, "area_rel_tol": 0.002}}: the cross-section's extent on the plane's
two axes, and optionally its area, at stated stations (FreeCAD backend).

--override changes a parameter for this run only (to inject an error, test 7).
--no-promote checks only: nothing is copied out of .staging/ (sweeps, backend comparisons).
Every run writes a report to validation/history/. Outputs are copied out of
.staging/ into design/ and exports/ only when every check passes.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import shutil
import struct
import tempfile

try:  # SolidWorks backend: Windows + pywin32 only
    import pythoncom
    import win32com.client
    from win32com.client import VARIANT

    import swlib

    NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
except ImportError:
    pythoncom = None

SCRIPTS = pathlib.Path(__file__).resolve().parent
SW_INPUT_DIM_VAL_ON_CREATE = 10
SW_SOLID_BODY = 0


def connect():
    try:
        return win32com.client.GetActiveObject("SldWorks.Application")
    except pythoncom.com_error:
        app = win32com.client.Dispatch("SldWorks.Application")
        app.Visible = True
        return app


def open_titles(app):
    out, d = [], app.GetFirstDocument
    while d is not None:
        out.append(d.GetTitle)
        d = d.GetNext
    return out


def load_model_script(project):
    spec = importlib.util.spec_from_file_location("model", project / "design" / "model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure(model):
    b = [v * 1000 for v in model.GetPartBox(True)]
    bodies = model.GetBodies2(SW_SOLID_BODY, False) or ()
    return {
        "bbox": [round(b[3] - b[0], 4), round(b[4] - b[1], 4), round(b[5] - b[2], 4)],
        "volume": round(model.Extension.CreateMassProperty.Volume * 1e9, 3),
        "solid_bodies": len(bodies),
    }


def save_as(app, model, path):
    app.CloseDoc(str(path))
    e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    # STL (and other mesh) export writes the ACTIVE document, whichever object
    # SaveAs3 is called on; make sure that is this model.
    # Activate by full path when saved: activating by title can silently fail
    # (seen after a crashed run left a same-named doc behind).
    app.ActivateDoc3(model.GetPathName or model.GetTitle, False, 0, e)
    active = app.ActiveDoc
    if active is None or active.GetTitle != model.GetTitle:
        print(f"could not activate {model.GetTitle} for mesh export (another doc took focus)")
        return False
    w = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    ok = model.Extension.SaveAs3(str(path), 0, 1, NOTHING, NOTHING, e, w)
    return bool(ok) and path.exists()


def stl_volume(path):
    """Volume (mm^3) and watertightness of a binary STL, independent of SolidWorks."""
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    vol, edges = 0.0, {}
    for i in range(n):
        v = struct.unpack_from("<12f", data, 84 + i * 50)[3:]
        a, b, c = v[0:3], v[3:6], v[6:9]
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for p, q in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((tuple(round(x, 5) for x in p), tuple(round(x, 5) for x in q))))
            edges[key] = edges.get(key, 0) + 1
    closed = all(k == 2 for k in edges.values())
    return abs(vol), closed, n


def reopen_step(app, path):
    e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = app.LoadFile4(str(path), "r", NOTHING, e)
    if doc is None:
        return None
    m = measure(doc)
    app.CloseDoc(doc.GetTitle)
    return m


def check(checks, cid, category, measured, expected, tol, hint=None, rel=False):
    lim = tol * abs(expected) if rel else tol
    ok = measured is not None and abs(measured - expected) <= lim
    checks.append({
        "id": cid, "category": category, "status": "pass" if ok else "fail",
        "measured": measured, "expected": expected, "tolerance": lim,
        "message": "" if ok else f"{cid}: measured {measured}, expected {expected} ± {lim:g}",
        **({"hint": hint} if hint and not ok else {}),
    })


def geometry_checks(checks, spec, m):
    check(checks, "solid_bodies", "solid_validity", m["solid_bodies"],
          spec["solid_bodies"]["expected"], 0)
    for i, axis in enumerate("xyz"):
        s = spec[f"bbox.{axis}"]
        check(checks, f"bbox.{axis}", "bounding_dimensions", m["bbox"][i],
              s["expected"], s["tol"], hint={"param": s.get("param")})
    if "volume" in spec:
        check(checks, "volume", "bounding_dimensions", m["volume"],
              spec["volume"]["expected"], spec["volume"]["rel_tol"], rel=True)
    elif not spec.get("sections"):
        raise SystemExit("spec.json needs a hand-computed volume, or sections for a freeform part")


def export_checks(checks, spec, m, step_volume, stl):
    check(checks, "export.step.volume", "export_integrity", step_volume,
          m["volume"], spec["export.step"]["rel_tol"], rel=True)
    if stl is not None and stl.exists():
        vol, closed, tris = stl_volume(stl)
        check(checks, "export.stl.volume", "export_integrity", round(vol, 3),
              m["volume"], spec["export.stl"]["rel_tol"], rel=True)
        checks.append({"id": "export.stl.watertight", "category": "export_integrity",
                       "status": "pass" if closed else "fail", "measured": closed,
                       "expected": True, "message": f"{tris} triangles"})
    else:
        check(checks, "export.stl.volume", "export_integrity", None, m["volume"], 0)


def _plane_axes(axis):
    return [k for k in "xyz" if k != axis]


def native_check(checks, native):
    # SolidWorks has been seen to report success while writing a 0-byte part.
    size = native.stat().st_size if native.exists() else 0
    checks.append({"id": "export.native", "category": "export_integrity",
                   "status": "pass" if size > 1000 else "fail", "measured": size,
                   "expected": "> 1000 bytes", "message": "" if size > 1000 else
                   f"native part file is {size} bytes"})


def build_freecad(project, params, spec, staging):
    """Build, measure and export inside FreeCADCmd (scripts/fc/fc_job.py); check here."""
    import freecad_run
    import render_config
    out = pathlib.Path(tempfile.mkdtemp(prefix="fcjob_")) / "job.json"
    job = {"model": str(project / "design" / "model.py"), "params": params, "name": project.name,
           "staging": str(staging), "features": list(spec.get("features", {})),
           "sections": {k: {"axis": v["axis"], "at": v["at"]} for k, v in spec.get("sections", {}).items()}, "out_json": str(out)}
    proc, cmd = freecad_run.run(SCRIPTS / "fc" / "fc_job.py", "FC_JOB", job)
    err = out.with_name(out.name + ".error")
    if err.exists() or not out.exists():
        detail = err.read_text() if err.exists() else proc.stdout[-3000:] + proc.stderr[-3000:]
        raise RuntimeError(f"FreeCAD build failed ({freecad_run.describe(cmd)}):\n{detail}")
    r = json.loads(out.read_text(encoding="utf-8"))
    m = {k: r["measure"][k] for k in ("bbox", "volume", "solid_bodies")}
    native = pathlib.Path(r["native"])
    checks = []
    native_check(checks, native)
    checks.append({"id": "shape.valid", "category": "solid_validity",
                   "status": "pass" if r["measure"]["valid"] else "fail", "measured": r["measure"]["valid"],
                   "expected": True, "message": "" if r["measure"]["valid"] else "OCCT reports an invalid shape"})
    geometry_checks(checks, spec, m)
    for fname, fs in spec.get("features", {}).items():
        check(checks, f"feature.{fname}.volume", "feature_volume", r["features"].get(fname),
              fs["expected"], fs["rel_tol"], rel=True)
    for sid, ss in spec.get("sections", {}).items():
        got = r["sections"].get(sid) or {"size": [None, None], "area": None}
        for want, have, name in zip(ss["size"], got["size"], _plane_axes(ss["axis"])):
            check(checks, f"section.{sid}.{name}", "section_dimensions", have, want, ss.get("tol", 0.05))
        if "area" in ss:
            check(checks, f"section.{sid}.area", "section_dimensions", got["area"], ss["area"], ss.get("area_rel_tol", 0.002), rel=True)
    step = pathlib.Path(r["step"]) if r["step"] else staging / f"{project.name}.step"
    stl = pathlib.Path(r["stl"]) if r["stl"] else None
    export_checks(checks, spec, m, r["step_reopened"] and r["step_reopened"]["volume"], stl)
    renders = []
    if stl is not None and render_config.blender_exe():
        code, _ = render_config.run_blender("bl_check_views.py", "--stl", stl, "--out", staging / "renders", timeout=600)
        renders = sorted((staging / "renders").glob("*.png")) if code == 0 else []
    if not renders:
        print("no check renders (Blender not found or failed)")
    return native, m, checks, step, stl, renders, {"backend": "freecad", "freecad_version": r["freecad_version"]}


def run(project, overrides, backend, promote=True):
    # A product's part (products/<name>/parts/<part>) is built only from its approved draft.
    if project.parent.name == "parts" and (project.parents[1] / "brief.json").exists():
        import draft_lib
        ok, msg = draft_lib.gate(project.parents[1], project.name)
        if not ok:
            raise SystemExit(msg)
    params = json.loads((project / "parameters" / "params.json").read_text())
    params.update(overrides)
    spec = json.loads((project / "validation" / "spec.json").read_text())
    # Each run gets its own staging folder: SolidWorks can keep a file lock on a
    # closed document, which would block clearing a shared folder. Old run folders
    # are removed when they are no longer locked.
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    root = project / ".staging"
    for old in root.glob("*") if root.exists() else ():
        shutil.rmtree(old, ignore_errors=True) if old.is_dir() else old.unlink(missing_ok=True) \
            if not old.name.endswith(".SLDPRT") else None
    staging = root / stamp
    staging.mkdir(parents=True)
    build = build_freecad if backend == "freecad" else build_solidworks
    native, m, checks, step, stl, renders, info = build(project, params, spec, staging)
    return finish(project, stamp, params, native, m, checks, step, stl, staging, renders, info, promote)


def build_solidworks(project, params, spec, staging):
    if pythoncom is None:
        raise RuntimeError("the SolidWorks backend needs Windows and pywin32; use --backend freecad")
    app = connect()
    prev = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
    checks = []
    try:
        # 1. Build. On failure, save the partial part into this run's staging folder
        # (for debugging) and close it, so failed builds don't pile up as open tabs.
        before = set(open_titles(app))
        try:
            model = load_model_script(project).build(app, params)
        except Exception:
            for t in set(open_titles(app)) - before:
                d = app.GetOpenDocumentByName(t) or app.ActiveDoc
                if d is not None:
                    save_as(app, d, staging / "failed_build.SLDPRT")
                    app.CloseDoc(d.GetTitle)
            raise
        native = staging / f"{project.name}.SLDPRT"
        save_as(app, model, native)
        m = measure(model)
        native_check(checks, native)

        # 2. Validate geometry against the spec
        geometry_checks(checks, spec, m)
        # Features too small for the total-volume tolerance (e.g. copper tracks):
        # suppress each one, measure what it contributed, then restore it.
        # A name ending in "*" covers every feature with that prefix (e.g. "RoundTop*" for a
        # fillet plus its follow-up fixes); they are suppressed together.
        def select_features(fname):
            names = [fname]
            if fname.endswith("*"):
                names, f = [], model.FirstFeature
                while f is not None:
                    if f.Name.startswith(fname[:-1]):
                        names.append(f.Name)
                    f = f.GetNextFeature
            model.ClearSelection2(True)
            return names and all(model.Extension.SelectByID2(n, "BODYFEATURE", 0, 0, 0, i > 0, 0, NOTHING, 0)
                                 for i, n in enumerate(names))

        for fname, fs in spec.get("features", {}).items():
            got = None
            if select_features(fname):
                swlib._invoke(model, "EditSuppress2")
                model.ForceRebuild3(False)
                got = round(m["volume"] - measure(model)["volume"], 4)
                select_features(fname)
                swlib._invoke(model, "EditUnsuppress2")
                model.ForceRebuild3(False)
                model.ClearSelection2(True)
            check(checks, f"feature.{fname}.volume", "feature_volume", got,
                  fs["expected"], fs["rel_tol"], rel=True)

        # Renders, so the result can be compared visually with the brief / photo
        renders = swlib.render(model, staging / "renders")

        # 3. Export, then reopen and compare against the native model
        step, stl = staging / f"{project.name}.step", staging / f"{project.name}.stl"
        step_ok, stl_ok = save_as(app, model, step), save_as(app, model, stl)
        app.CloseDoc(model.GetTitle)
        r = reopen_step(app, step) if step_ok else None
        export_checks(checks, spec, m, r and r["volume"], stl if stl_ok else None)
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, prev)
    return native, m, checks, step, stl, renders, {"backend": "solidworks"}


def finish(project, stamp, params, native, m, checks, step, stl, staging, renders, info, promote=True):
    failed = sum(c["status"] == "fail" for c in checks)
    status = "fail" if failed else "pass"
    report = {
        "schema_version": "1.0", "project": project.name, "timestamp": stamp,
        "model_file": str(native), "status": status, "params_used": params, **info,
        "summary": {"passed": len(checks) - failed, "failed": failed, "warnings": 0},
        "components": {"Body": m}, "checks": checks,
    }
    hist = project / "validation" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{stamp}_{status}.json").write_text(json.dumps(report, indent=2))

    # 4. Promote only on pass; otherwise last validated outputs stay untouched.
    if status == "pass" and promote:
        (project / "exports").mkdir(exist_ok=True)
        shutil.copy2(native, project / "design" / native.name)
        shutil.copy2(step, project / "exports" / step.name)
        shutil.copy2(stl, project / "exports" / stl.name)
        if (staging / "renders").exists():
            shutil.copytree(staging / "renders", project / "renders", dirs_exist_ok=True)
    report["renders"] = [str(p) for p in renders]
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=pathlib.Path)
    ap.add_argument("--override", action="append", default=[], help="name=value (mm)")
    ap.add_argument("--no-promote", action="store_true")
    ap.add_argument("--backend", choices=("solidworks", "freecad"),
                    default=os.environ.get("CAD_BACKEND") or ("solidworks" if os.name == "nt" else "freecad"))
    a = ap.parse_args()
    overrides = {k: float(v) for k, v in (o.split("=", 1) for o in a.override)}
    report = run(a.project.resolve(), overrides, a.backend, not a.no_promote)
    for c in report["checks"]:
        print(f'{c["status"].upper():4}  {c["id"]:24} {c.get("measured")}  {c.get("message", "")}')
    print("renders:", *report["renders"], sep="\n  ")
    print(f'\n{report["status"].upper()}: {report["summary"]}'
          f'{"  -> promoted" if report["status"] == "pass" and not a.no_promote else "  -> not promoted"}')


if __name__ == "__main__":
    main()
