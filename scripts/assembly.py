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
"""
import argparse
import datetime as dt
import json
import math
import pathlib
import sys

import pythoncom
import win32com.client as w
from win32com.client import VARIANT

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import swlib  # noqa: E402
from swlib import _invoke  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MM = 0.001
BG, FG = (245, 242, 234), (44, 46, 50)  # off-white background, charcoal lines


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


def transform(math_util, at, rot_z):
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
        path = pathlib.Path(c["file"]) if "file" in c else ROOT / "projects" / c["part"] / "design" / f"{c['part']}.SLDPRT"
        if str(path) not in opened:
            app.OpenDoc6(str(path), 1, 1, "", byref(), byref())
            opened.append(str(path))
        app.ActivateDoc3(doc.GetTitle, False, 0, byref())
        comp = asm.AddComponent5(str(path), 0, "", False, "", 0, 0, 0)
        if comp is None:
            raise RuntimeError(f"could not insert {path.name}")
        comp.Transform2 = transform(mu, c.get("at", (0, 0, 0)), c.get("rot_z", 0))
        comps.append((c.get("label") or c["part"], comp))
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


def interferences(doc):
    idm = doc.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.TreatSubAssembliesAsComponents = True
    idm.IncludeMultibodyPartInterferences = False
    found = []
    for itf in idm.GetInterferences or ():
        names = sorted(c.Name2.rsplit("-", 1)[0] for c in itf.Components)
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
    allowed = [sorted(p) for p in exp.get("allowed_interference", [])]
    for itf in interferences(doc):
        check("interference " + " / ".join(itf["pair"]), itf["pair"] in allowed, **itf,
              note="allowed" if itf["pair"] in allowed else "unexpected")
    if not any(c["id"].startswith("interference") for c in checks):
        check("interference", True, note="none found")

    path = folder / f"{name}.SLDASM"
    e = byref()
    doc.Extension.SaveAs3(str(path), 0, 1, swlib.NOTHING, swlib.NOTHING, e, byref())
    (folder / "exports").mkdir(exist_ok=True)
    doc.Extension.SaveAs3(str(folder / "exports" / f"{name}.step"), 0, 1, swlib.NOTHING, swlib.NOTHING, byref(), byref())
    renders = swlib.render(doc, folder / "renders")
    _invoke(doc, "ViewDisplayWireframe")
    wf = swlib.render(doc, folder / "renders" / "wireframe", views=("isometric", "front"))
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=pathlib.Path)
    run(ap.parse_args().folder.resolve())
