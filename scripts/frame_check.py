"""Check (and pick) how each simplified part sits in its source part's frame.

For every source part in assemblies/x8020_frames.json, build a scratch assembly holding the
original (read-only) and the simplified part, try each candidate local transform, and measure
the overlap volume with interference detection. The best candidate is stored as "chosen";
a source fails when its best overlap is under --min of the smaller of the two volumes.
Scratch assemblies are saved to --scratch and closed.

    .venv\\Scripts\\python scripts\\frame_check.py --scratch <dir> [--only 4332.SLDPRT ...]
"""
import argparse
import json
import pathlib
import sys

import pythoncom
from win32com.client import VARIANT

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import swlib  # noqa: E402
from assembly import byref, open_titles  # noqa: E402
from swlib import _invoke  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRAMES = ROOT / "assemblies" / "x8020_frames.json"
MM = 0.001


def set_xform(app, comp, x):
    data = list(x[:9]) + [v * MM for v in x[9:12]] + [1, 0, 0, 0]
    comp.Transform2 = _invoke(app.GetMathUtility, "CreateTransform",
                              VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data))


def overlap(doc):
    idm = doc.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.TreatSubAssembliesAsComponents = True
    idm.IncludeMultibodyPartInterferences = False
    v = sum(itf.Volume for itf in idm.GetInterferences or ()) / MM ** 3
    idm.Done
    return v


def volume_of(comp):
    m = comp.GetModelDoc2
    if m is None:
        return None
    try:
        return m.Extension.CreateMassProperty.Volume * 1e9
    except Exception:
        return None


def source_path(src_file):
    for cap in (ROOT / "assemblies").glob("*/capture.json"):
        for lf in json.loads(cap.read_text())["leaves"]:
            if lf["file"] == src_file:
                return lf["path"]
    raise SystemExit(f"{src_file} not in any capture.json")


def check_one(app, src_file, fr, scratch, min_frac):
    simple = ROOT / "projects" / fr["part"] / "design" / f"{fr['part']}.SLDPRT"
    src = source_path(src_file)
    src_asm = src.lower().endswith(".sldasm")
    app.OpenDoc6(src, 2 if src_asm else 1, 1 | 2, "", byref(), byref())
    app.OpenDoc6(str(simple), 1, 1, "", byref(), byref())
    doc = app.NewDocument(app.GetUserPreferenceStringValue(9), 0, 0, 0)
    app.ActivateDoc3(doc.GetTitle, False, 0, byref())
    a = doc.AddComponent5(src, 0, "", False, "", 0, 0, 0)
    b = doc.AddComponent5(str(simple), 0, "", False, "", 0, 0, 0)
    set_xform(app, a, [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    vb = volume_of(b)
    va = volume_of(a) if not src_asm else None
    small = min(v for v in (va, vb) if v)
    results = []
    for i, x in enumerate(fr["candidates"]):
        set_xform(app, b, x)
        doc.EditRebuild3
        results.append(round(overlap(doc) / small, 4))
    doc.Extension.SaveAs3(str(scratch / f"frame_{pathlib.Path(src_file).stem}.SLDASM"), 0, 1,
                          swlib.NOTHING, swlib.NOTHING, byref(), byref())
    app.CloseDoc(doc.GetTitle)
    best = max(range(len(results)), key=results.__getitem__)
    return best, results, va, vb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--min", type=float, default=0.85)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    frames = json.loads(FRAMES.read_text())
    app = swlib.connect()
    before = open_titles(app)
    bad = []
    try:
        for f, fr in frames.items():
            if a.only and f not in a.only:
                continue
            best, res, va, vb = check_one(app, f, fr, a.scratch, a.min)
            for t in open_titles(app) - before:
                app.CloseDoc(t)
            fr["chosen"], fr["overlap"] = best, res[best]
            ok = res[best] >= a.min
            bad += [] if ok else [f]
            print(f"{'PASS' if ok else 'FAIL'} {f:40s} -> {fr['part']:28s} overlap {res[best]:.3f} "
                  f"(candidates {res}) vol src {va and round(va)} simple {vb and round(vb)}")
            FRAMES.write_text(json.dumps(frames, indent=1))
    finally:
        for t in open_titles(app) - before:
            app.CloseDoc(t)
    print("FAIL" if bad else "PASS", bad)


if __name__ == "__main__":
    main()
