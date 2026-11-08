"""SolidWorks adapter: .SLDASM / .SLDPRT -> STEP per unique part + product manifest.

Runs in the repo venv (pywin32) against a running SolidWorks. The CAD file is opened
read-only and never modified. SolidWorks' STEP options (AP version, appearances) are
restored afterwards, and every document this adapter opens is closed again; documents
the user had open are left alone.

Verified on SOLIDWORKS 2025 (see docs/rendering.md):
- swUserPreferenceIntegerValue_e.swStepAP = 75 takes 203 or 214; 242 is silently ignored by
  Save As (AP203 comes out). AP242 needs PublishSTEP242File and a SOLIDWORKS MBD licence.
- Component2.Transform2.ArrayData: row-vector rotation, translation in metres, then scale.
- Component2.Name2 is unique within the assembly and stays stable until it is restructured.
"""
import pathlib
import re
import sys

from . import common as C

MM = 0.001
SW_STEP_AP = 75
SW_STEP_EXPORT_APPEARANCES = 787
OPEN_SILENT_READONLY = 1 | 2
SW_DEFAULT_RGB = (0.7922, 0.8196, 0.9333)  # appearance of a part nobody coloured
EXTENSIONS = (".sldasm", ".sldprt")
STEP242_ERRORS = {1: "invalid path", 3: "unknown error", 4: "MBD licence not available",
                  5: "edition error", 6: "custom property error"}


def com():
    import pythoncom
    import win32com.client
    from win32com.client import VARIANT
    return pythoncom, win32com.client, VARIANT


def byref():
    pythoncom, _, VARIANT = com()
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def connect():
    pythoncom, client, _ = com()
    try:
        return client.GetActiveObject("SldWorks.Application")
    except pythoncom.com_error:
        sys.exit("SolidWorks is not running. Start it, then rerun.")


def open_titles(app):
    out, d = set(), app.GetFirstDocument
    while d is not None:
        out.add(d.GetTitle)
        d = d.GetNext
    return out


def find_cad(target):
    """The .SLDASM/.SLDPRT for a target file or folder, and the folder that gets render/."""
    t = pathlib.Path(target).resolve()
    if t.is_file():
        return t, t.parent
    for cand in (t / f"{t.name}.SLDASM", t / "design" / f"{t.name}.SLDPRT", t / f"{t.name}.SLDPRT"):
        if cand.exists():
            return cand, t
    found = sorted(t.glob("*.SLDASM")) or sorted(t.glob("design/*.SLDPRT"))
    return (found[0], t) if found else (None, t)


def matrix_from_sw(arr):
    """Component2.Transform2.ArrayData (row-vector rotation, translation in m, scale)
    -> 4x4 column-vector matrix, translation in mm, row-major list of rows."""
    r, t, s = arr[:9], arr[9:12], arr[12] if len(arr) > 12 else 1.0
    return [[r[0] * s, r[3] * s, r[6] * s, t[0] / MM],
            [r[1] * s, r[4] * s, r[7] * s, t[1] / MM],
            [r[2] * s, r[5] * s, r[8] * s, t[2] / MM],
            [0.0, 0.0, 0.0, 1.0]]


def sw_material(doc):
    """SolidWorks material name of a part, or ''. Tries the APIs that exist across versions."""
    for call in (lambda: doc.GetMaterialPropertyName2("", byref()), lambda: doc.MaterialIdName):
        try:
            v = call()
            if isinstance(v, tuple):
                v = v[0]
            if v:
                v = str(v)
                return v.split("|")[1] if v.count("|") >= 2 else v
        except Exception:  # noqa: BLE001 - optional metadata
            pass
    return ""


def sw_appearance(doc):
    """Part-level appearance colour [r, g, b] (0..1), or None when it is the untouched default."""
    try:
        v = list(doc.MaterialPropertyValues or ())
    except Exception:  # noqa: BLE001
        return None
    if len(v) < 9:
        return None
    rgb = C.r4(v[:3])
    return None if all(abs(a - b) < 0.002 for a, b in zip(rgb, SW_DEFAULT_RGB)) else rgb


def export_step(app, doc, out, ap242=False):
    """AP214 through SaveAs3; with ap242, try PublishSTEP242File first and return the fallback reason."""
    pythoncom, _, VARIANT = com()
    nothing = VARIANT(pythoncom.VT_DISPATCH, None)
    out.parent.mkdir(parents=True, exist_ok=True)
    e = byref()
    app.ActivateDoc3(doc.GetPathName or doc.GetTitle, False, 0, e)
    reason = None
    if ap242:
        res = doc.Extension.PublishSTEP242File(str(out.with_suffix(".stp")))
        if res == 0 and out.with_suffix(".stp").exists():
            out.with_suffix(".stp").replace(out)
            return "AP242 (PublishSTEP242File)", None
        reason = STEP242_ERRORS.get(res, f"error {res}")
    ok = doc.Extension.SaveAs3(str(out), 0, 1, nothing, nothing, e, byref())
    if not (ok and out.exists() and out.stat().st_size > 200):
        raise RuntimeError(f"STEP export failed: {out}")
    head = out.read_text(errors="replace")[:4000]
    schema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head)
    return (schema.group(1) if schema else "unknown"), reason


def export(target, render_dir, lib, *, exploded_from=None, explode_axis="z", ap242=False, **_):
    cad, folder = find_cad(target)
    if cad is None:
        sys.exit(f"no .SLDASM or design/*.SLDPRT found in {target}")
    geo = pathlib.Path(render_dir) / "export" / "geometry"
    app = connect()
    before = open_titles(app)
    prev_ap = app.GetUserPreferenceIntegerValue(SW_STEP_AP)
    prev_app = app.GetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES)
    app.SetUserPreferenceIntegerValue(SW_STEP_AP, 214)
    app.SetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES, True)
    name = cad.stem
    man = C.new_manifest(project=folder.name, assembly=name, adapter="solidworks", application="SOLIDWORKS",
                         application_version=str(getattr(app, "RevisionNumber", "")), file=cad,
                         reference="cad_kernel", reference_note="part and assembly bboxes measured by SolidWorks")
    parts, comps = man["parts"], man["components"]
    try:
        is_asm = cad.suffix.lower() == ".sldasm"
        e, w = byref(), byref()
        doc = app.OpenDoc6(str(cad), 2 if is_asm else 1, OPEN_SILENT_READONLY, "", e, w)
        if doc is None:
            raise RuntimeError(f"could not open {cad} (error {e.value})")
        if not is_asm:
            man["hierarchy"][0]["kind"] = "part"

        def add_part(pdoc, path):
            stem = pathlib.Path(path).stem
            if stem not in parts:
                box = list(pdoc.GetPartBox(True))
                parts[stem] = C.part_entry(
                    stem, {"file": C.rel(geo / "parts" / f"{stem}.step", render_dir), "format": "step",
                           "scale_to_m": None, "up_axis": "Z"},
                    [v / MM for v in box[:3]], [v / MM for v in box[3:]],
                    source_material=sw_material(pdoc), source_color=sw_appearance(pdoc), source_path=path, lib=lib)
            return stem

        if is_asm:
            for c in doc.GetComponents(False) or ():
                cid = c.Name2
                par = c.GetParent
                parent = par.Name2 if par is not None else name
                if len(c.GetChildren or ()) > 0:
                    man["hierarchy"].append({"id": cid, "parent": parent, "kind": "subassembly"})
                    continue
                pdoc = c.GetModelDoc2
                part = add_part(pdoc, c.GetPathName) if pdoc is not None else None
                n = cid.rpartition("-")[2]
                comps.append(C.component_entry(
                    cid, part, matrix_from_sw(list(c.Transform2.ArrayData)), parent, parts,
                    visible=c.Visible == 1, suppressed=bool(c.IsSuppressed), occurrence=int(n) if n.isdigit() else None,
                    source={"sw_path": c.GetPathName, "configuration": c.ReferencedConfiguration}))
            box = list(doc.GetBox(0))
        else:
            stem = add_part(doc, cad)
            comps.append(C.component_entry(f"{stem}-1", stem, C.IDENTITY, name, parts, source={"sw_path": str(cad)}))
            box = list(doc.GetPartBox(True))
        man["bbox_mm"] = C.union_bbox([([v / MM for v in box[:3]], [v / MM for v in box[3:]])])
        asm_step = geo / f"{name}.step"
        schema, ap242_fail = export_step(app, doc, asm_step, ap242)
        man["geometry"]["assembly"] = {"file": C.rel(asm_step, render_dir), "format": "step", "scale_to_m": None, "up_axis": "Z"}
        for stem, p in parts.items():
            pdoc = app.OpenDoc6(p["source_path"], 1, OPEN_SILENT_READONLY, "", byref(), byref()) if is_asm else doc
            export_step(app, pdoc, geo / "parts" / f"{stem}.step", ap242)
            if is_asm and pdoc.GetTitle not in before:
                app.CloseDoc(pdoc.GetTitle)
        C.drop_template_material(parts, lib)
        labels = C.labels_from_assembly_json(cad.parent, comps)
        for c in comps:
            if c["id"] in labels:
                c["label"] = labels[c["id"]]
        if doc.GetTitle not in before:  # never close a document the user had open
            app.CloseDoc(doc.GetTitle)
    finally:
        app.SetUserPreferenceIntegerValue(SW_STEP_AP, prev_ap)
        app.SetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES, prev_app)
        for t in open_titles(app) - before:  # leftovers from this run only
            app.CloseDoc(t)
    protocol = "AP242" if schema.startswith("AP242") else {"AUTOMOTIVE_DESIGN": "AP214", "CONFIG_CONTROL_DESIGN": "AP203"}.get(schema, schema)
    man["source"]["details"] = {"step_schema": schema, "step_protocol": protocol, "ap242_requested": ap242,
                                "ap242_fallback_reason": ap242_fail, "appearances": True}
    man["exploded"] = C.explode_from_assembly(comps, exploded_from) if exploded_from else C.explode_auto(comps, explode_axis)
    print(f"STEP {protocol}{' (AP242 failed: ' + ap242_fail + ')' if ap242_fail else ''}")
    return man
