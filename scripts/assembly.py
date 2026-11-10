"""Build a SolidWorks assembly from assemblies/<name>/assembly.json, check it and render it.

Each component is a promoted part (projects/<part>/design/<part>.SLDPRT) placed
by a translation in mm and a rotation about Z in degrees. All components are
fixed in place: placement is by coordinates, not mates. Checks:
  - every component was inserted
  - the assembly bounding box against `expected.bbox`
  - interference detection: any interference between a pair of components
    that is not listed in `expected.allowed_interference` fails the run
A JSON report goes to validation/history/. Renders go to renders/ (shaded) and
renders/wireframe/ (off-white lines on charcoal).

    .venv\\Scripts\\python scripts\\assembly.py assemblies\\pi5_dac_hat
    python3 scripts/assembly.py assemblies/grindmn --backend freecad

--backend freecad (the default off Windows; CAD_BACKEND overrides it) places the parts' promoted STEP
files in FreeCADCmd (scripts/fc/fc_assembly.py) and renders the check views in Blender. It checks the
component count, bbox and interference the same way; vendor-assembly options (baseline_interference,
faces_before, explode lines) are SolidWorks only.
"""
import argparse
import datetime as dt
import json
import math
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
try:  # SolidWorks backend: Windows + pywin32 only
    import pythoncom
    import win32com.client as w
    from win32com.client import VARIANT

    import swlib  # noqa: E402
    from swlib import _invoke  # noqa: E402
except ImportError:
    pythoncom = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
MM = 0.001
BG, FG = (40, 42, 46), (238, 234, 222)  # charcoal background, off-white lines


def byref():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def recolor(png, bg=BG, fg=FG):
    """Map a black-on-white wireframe render to fg lines on a bg background."""
    from PIL import Image
    im = Image.open(png).convert("L")
    # SolidWorks' light background gradient (grey >= 190) becomes flat bg; darker = line.
    ink = [max(0.0, (190 - v) / 190) ** 0.6 for v in range(256)]
    lut = [[round(b + (f - b) * k) for k in ink] for b, f in zip(bg, fg)]
    Image.merge("RGB", [im.point(l) for l in lut]).save(png)


def transform(math_util, at, rot_z, xform=None):
    """Placement from at + rot_z, or from a full xform: 9 rotation numbers (row-vector form,
    p' = p R + t, as in Component2.Transform2) then the translation in mm."""
    if xform is not None:
        data = list(xform[:9]) + [v * MM for v in xform[9:12]] + [1, 0, 0, 0]
        return _invoke(math_util, "CreateTransform", VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data))
    c, s = math.cos(math.radians(rot_z)), math.sin(math.radians(rot_z))
    data = [c, s, 0, -s, c, 0, 0, 0, 1, at[0] * MM, at[1] * MM, at[2] * MM, 1, 0, 0, 0]
    return _invoke(math_util, "CreateTransform", VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data))


def explode_lines(app, spec, folder):
    """Build the explode-line part: thin rods (spec["lines"]["d"] mm) from (x, y, z0) to z1,
    in assembly coordinates. These are annotation geometry, not hardware."""
    ln = spec["lines"]
    part = swlib.Part(app)
    try:
        groups = {}
        for x, y, z0, z1 in ln["rods"]:
            groups.setdefault((z0, z1), []).append(swlib.circle(x, y, ln["d"]))
        for i, ((z0, z1), profs) in enumerate(sorted(groups.items())):
            part.extrude(f"Line_{i + 1}", profs, z1 - z0, z=z0)
    finally:
        part.close_prefs()
    path = folder / "explode_lines.SLDPRT"
    part.doc.Extension.SaveAs3(str(path), 0, 1, swlib.NOTHING, swlib.NOTHING, byref(), byref())
    app.CloseDoc(part.doc.GetTitle)
    return path


def build(app, spec, folder):
    extra = []
    if "lines" in spec:
        extra = [{"file": str(explode_lines(app, spec, folder)), "label": "explode_lines"}]
    template = app.GetUserPreferenceStringValue(9)  # swDefaultTemplateAssembly
    doc = app.NewDocument(template, 0, 0, 0)
    asm = doc
    mu = app.GetMathUtility
    opened, comps = [], []
    for c in spec["components"] + extra:
        path = (ROOT / c["file"] if not pathlib.Path(c["file"]).is_absolute() else pathlib.Path(c["file"])) if "file" in c else ROOT / "projects" / c["part"] / "design" / f"{c['part']}.SLDPRT"
        if str(path) not in opened:
            app.OpenDoc6(str(path), 1, 1, "", byref(), byref())
            opened.append(str(path))
        app.ActivateDoc3(doc.GetTitle, False, 0, byref())
        comp = asm.AddComponent5(str(path), 0, "", False, "", 0, 0, 0)
        if comp is None:
            raise RuntimeError(f"could not insert {path.name}")
        comp.Transform2 = transform(mu, c.get("at", (0, 0, 0)), c.get("rot_z", 0), c.get("xform"))
        comps.append((c.get("label") or c.get("part") or path.stem, comp))
    # Fix every component so nothing floats, then rebuild
    doc.ClearSelection2(True)
    for _, comp in comps:
        comp.Select4(True, swlib.NOTHING, False)
    _invoke(asm, "FixComponent")
    doc.ClearSelection2(True)
    doc.EditRebuild3
    for path in opened:  # parts stay loaded through the assembly; drop their own tabs
        app.CloseDoc(pathlib.Path(path).name)
    return doc, comps


def interferences(doc, labels=None):
    """Colliding pairs, named by part (or by the component labels, when given {Name2: label})."""
    idm = doc.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.TreatSubAssembliesAsComponents = True
    idm.IncludeMultibodyPartInterferences = False
    found = []
    for itf in idm.GetInterferences or ():
        names = sorted(labels.get(c.Name2, c.Name2) if labels else c.Name2.rsplit("-", 1)[0] for c in itf.Components)
        found.append({"pair": names, "volume_mm3": round(itf.Volume / MM ** 3, 4)})
    idm.Done
    return found


def run(folder):
    spec = json.loads((folder / "assembly.json").read_text())
    exp = spec.get("expected", {})
    app = swlib.connect()
    before = open_titles(app)
    try:
        return _run(app, folder, spec, exp)
    finally:  # close anything this run left open (failed builds included)
        for t in open_titles(app) - before:
            app.CloseDoc(t)


def open_titles(app):
    out, d = set(), app.GetFirstDocument
    while d is not None:
        out.add(d.GetTitle)
        d = d.GetNext
    return out


def _run(app, folder, spec, exp):
    doc, comps = build(app, spec, folder)
    name = folder.name
    checks = []

    def check(cid, ok, **kw):
        checks.append({"id": cid, "pass": bool(ok), **kw})

    n_exp = len(spec["components"]) + ("lines" in spec)
    check("components", len(comps) == n_exp, expected=n_exp, actual=len(comps))
    box = doc.GetBox(0)
    size = [round((box[i + 3] - box[i]) / MM, 3) for i in range(3)]
    for ax, e, a in zip("xyz", exp.get("bbox", []), size):
        check(f"bbox.{ax}", abs(a - e) <= exp.get("bbox_tol", 0.1), expected=e, actual=a)
    if "baseline_interference" in exp:
        # rebuilt assembly: only pairs that already collide in the original are allowed
        base = {tuple(sorted(p)) for p in exp["baseline_interference"]}
        found = interferences(doc, {comp.Name2: label for label, comp in comps})
        # "interference_ignore": {"below_mm3": touching noise, "parts": [[prefix_a, prefix_b]]}
        # pairs of simplified parts known to collide by design (e.g. bolts into a slot with no T-cavity)
        ign = exp.get("interference_ignore", {})
        part_of = {label: (c.get("part") or pathlib.Path(c.get("file", "")).stem)
                   for label, c in zip([lb for lb, _ in comps], spec["components"])}

        def ignored(i):
            if i["volume_mm3"] < ign.get("below_mm3", 0):
                return True
            a, b = (part_of.get(n, n) for n in i["pair"])
            return any((a.startswith(x) and b.startswith(y)) or (a.startswith(y) and b.startswith(x))
                       for x, y in ign.get("parts", []))
        new = [i for i in found if tuple(i["pair"]) not in base and not ignored(i)]
        for itf in new:
            check("interference " + " / ".join(itf["pair"]), False, **itf, note="not in the original")
        check("interference", not new, found=len(found), baseline=len(base), new=len(new))
    else:
        allowed = [sorted(p) for p in exp.get("allowed_interference", [])]
        for itf in interferences(doc):
            check("interference " + " / ".join(itf["pair"]), itf["pair"] in allowed, **itf,
                  note="allowed" if itf["pair"] in allowed else "unexpected")
        if not any(c["id"].startswith("interference") for c in checks):
            check("interference", True, note="none found")
    if "faces_before" in exp:
        faces, seen = 0, {}
        for _, comp in comps:
            p = comp.GetPathName
            if p not in seen:
                m = comp.GetModelDoc2
                seen[p] = sum(b.GetFaceCount() for b in (m.GetBodies2(0, False) or ())) if m else 0
            faces += seen[p]
        check("faces", faces < exp["faces_before"], before=exp["faces_before"], after=faces,
              ratio=round(exp["faces_before"] / max(faces, 1), 2))

    path = folder / f"{name}.SLDASM"
    e = byref()
    doc.Extension.SaveAs3(str(path), 0, 1, swlib.NOTHING, swlib.NOTHING, e, byref())
    (folder / "exports").mkdir(exist_ok=True)
    doc.Extension.SaveAs3(str(folder / "exports" / f"{name}.step"), 0, 1, swlib.NOTHING, swlib.NOTHING, byref(), byref())
    views = tuple(exp.get("views", ("isometric", "top", "front", "right")))
    renders = swlib.render(doc, folder / "renders", views=views)
    _invoke(doc, "ViewDisplayWireframe")
    wf = swlib.render(doc, folder / "renders" / "wireframe", views=views[:2] if len(views) > 1 else views)
    for png in wf:
        recolor(png)
    _invoke(doc, "ViewDisplayShaded")
    doc.Save3(1, byref(), byref())
    app.CloseDoc(doc.GetTitle)

    ok = all(c["pass"] for c in checks)
    report = {"assembly": name, "time": dt.datetime.now().isoformat(timespec="seconds"), "pass": ok,
              "checks": checks, "bbox_mm": size, "files": [str(path)],
              "renders": [str(p) for p in renders + wf]}
    hist = folder / "validation" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{dt.datetime.now():%Y%m%dT%H%M%S}.json").write_text(json.dumps(report, indent=1))
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"], {k: v for k, v in c.items() if k not in ("id", "pass")})
    print("PASS" if ok else "FAIL", name)
    return report


def placement_matrix(c):
    """4 x 4 rows (mm) from at + rot_z, or from xform (row-vector R then t, as for SolidWorks above)."""
    if c.get("xform") is not None:
        r, t = c["xform"][:9], c["xform"][9:12]
    else:
        a = math.radians(c.get("rot_z", 0))
        r, t = [math.cos(a), math.sin(a), 0, -math.sin(a), math.cos(a), 0, 0, 0, 1], c["at"]
    return [r[0], r[3], r[6], t[0], r[1], r[4], r[7], t[1], r[2], r[5], r[8], t[2], 0, 0, 0, 1]


def run_freecad(folder):
    import freecad_run
    import render_config
    spec = json.loads((folder / "assembly.json").read_text())
    exp = spec.get("expected", {})
    name, checks, comps, counts = folder.name, [], [], {}

    def check(cid, ok, **kw):
        checks.append({"id": cid, "pass": bool(ok), **kw})

    for c in spec["components"]:
        part = c.get("part")
        # a product's own parts (products/<name>/parts), then the shared library, then the flat projects
        homes = [folder.parent / "parts", ROOT / "library", ROOT / "projects"]
        step = next((s for s in (h / str(part) / "exports" / f"{part}.step" for h in homes) if s.exists()), homes[-1] / str(part))
        if not part or not step.exists():
            check(f"component {part or c.get('file')}", False, note="no promoted STEP (run the pipeline first)")
            continue
        counts[part] = counts.get(part, 0) + 1
        comps.append({"part": part, "label": c.get("label") or f"{part}-{counts[part]}", "step": str(step),
                      "matrix": placement_matrix(c)})
    out = pathlib.Path(tempfile.mkdtemp(prefix="fcasm_")) / "asm.json"
    stl = out.with_name(f"{name}.stl")
    (folder / "exports").mkdir(exist_ok=True)
    job = {"components": comps, "fcstd": str(folder / f"{name}.FCStd"), "step": str(folder / "exports" / f"{name}.step"),
           "stl": str(stl), "out_json": str(out)}
    proc, cmd = freecad_run.run(pathlib.Path(__file__).parent / "fc" / "fc_assembly.py", "FC_JOB", job)
    err = out.with_name(out.name + ".error")
    if err.exists() or not out.exists():
        sys.exit(f"FreeCAD assembly failed ({freecad_run.describe(cmd)}):\n" +
                 (err.read_text() if err.exists() else proc.stdout[-3000:] + proc.stderr[-3000:]))
    r = json.loads(out.read_text())

    n_exp = len(spec["components"])
    check("components", r["components"] == n_exp, expected=n_exp, actual=r["components"])
    for ax, e, a in zip("xyz", exp.get("bbox") or [], r["bbox"]):
        check(f"bbox.{ax}", abs(a - e) <= exp.get("bbox_tol", 0.1), expected=e, actual=a)
    allowed = [sorted(p) for p in exp.get("allowed_interference", [])]
    for itf in r["interference"]:
        ok = itf["pair"] in allowed
        check("interference " + " / ".join(itf["labels"]), ok, **itf, note="allowed" if ok else "unexpected")
    if not r["interference"]:
        check("interference", True, note="none found")

    views = tuple(exp.get("views", ("isometric", "top", "front", "right")))
    renders = []
    if render_config.blender_exe():
        code, _ = render_config.run_blender("bl_check_views.py", "--stl", stl, "--out", folder / "renders",
                                            "--views", ",".join(views), timeout=900)
        renders = [folder / "renders" / f"{v}.png" for v in views] if code == 0 else []
    ok = all(c["pass"] for c in checks)
    report = {"assembly": name, "time": dt.datetime.now().isoformat(timespec="seconds"), "pass": ok,
              "backend": "freecad", "freecad_version": r["freecad_version"], "checks": checks,
              "bbox_mm": r["bbox"], "bbox_min_mm": r["bbox_min"], "files": [job["fcstd"], job["step"]],
              "renders": [str(p) for p in renders]}
    hist = folder / "validation" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{dt.datetime.now():%Y%m%dT%H%M%S}.json").write_text(json.dumps(report, indent=1))
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"], {k: v for k, v in c.items() if k not in ("id", "pass")})
    print("PASS" if ok else "FAIL", name)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=pathlib.Path)
    ap.add_argument("--backend", choices=("solidworks", "freecad"),
                    default=os.environ.get("CAD_BACKEND") or ("solidworks" if os.name == "nt" else "freecad"))
    a = ap.parse_args()
    (run_freecad if a.backend == "freecad" else run)(a.folder.resolve())
