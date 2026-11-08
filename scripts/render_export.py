"""Export a SolidWorks assembly (or part) for rendering: STEP files + product manifest.

    .venv\\Scripts\\python scripts\\render_export.py assemblies\\grindmn
    .venv\\Scripts\\python scripts\\render_export.py projects\\rpi5
    .venv\\Scripts\\python scripts\\render_export.py path\\to\\Some.SLDASM --out some\\folder
    ... --exploded-from assemblies\\grindmn_exploded   (explode offsets from a designed exploded assembly)

Writes into <folder>/render/export/:
  step/<name>.step            the whole assembly (AP214 with appearances; AP242 with --ap242 on an MBD seat)
  step/parts/<part>.step      one file per unique part (what Blender imports)
  product_manifest.json       components, hierarchy, transforms, materials, explode offsets

The CAD file is opened read-only and never modified. SolidWorks' STEP options
(AP version, appearances) are restored after the export. Every document this
script opens is closed again; documents the user had open are left alone.
"""
import argparse
import datetime as dt
import json
import math
import pathlib
import re
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import render_config as rc  # noqa: E402

NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
MM = 0.001
# Values read from swconst.tlb (SOLIDWORKS 2025), see docs/rendering.md
SW_STEP_AP = 75                 # swUserPreferenceIntegerValue_e.swStepAP: 203 or 214 (242 is ignored)
SW_STEP_EXPORT_APPEARANCES = 787  # swUserPreferenceToggle_e.swStepExportAppearances
OPEN_SILENT_READONLY = 1 | 2
SW_DEFAULT_RGB = (0.7922, 0.8196, 0.9333)  # appearance of a part nobody coloured (read from these parts)


def byref():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def connect():
    try:
        return win32com.client.GetActiveObject("SldWorks.Application")
    except pythoncom.com_error:
        sys.exit("SolidWorks is not running. Start it, then rerun.")


def open_titles(app):
    out, d = set(), app.GetFirstDocument
    while d is not None:
        out.add(d.GetTitle)
        d = d.GetNext
    return out


def find_cad(target):
    t = pathlib.Path(target).resolve()
    if t.is_file():
        return t, t.parent
    for cand in (t / f"{t.name}.SLDASM", t / "design" / f"{t.name}.SLDPRT", t / f"{t.name}.SLDPRT"):
        if cand.exists():
            return cand, t
    found = sorted(t.glob("*.SLDASM")) or sorted(t.glob("design/*.SLDPRT"))
    if found:
        return found[0], t
    sys.exit(f"no .SLDASM or design/*.SLDPRT found in {t}")


def matrix_from_sw(arr):
    """Component2.Transform2.ArrayData (row-vector rotation, translation in m, scale)
    -> 4x4 column-vector matrix, translation in mm, row-major list of rows."""
    r, t, s = arr[:9], arr[9:12], arr[12] if len(arr) > 12 else 1.0
    return [[r[0] * s, r[3] * s, r[6] * s, t[0] / MM],
            [r[1] * s, r[4] * s, r[7] * s, t[1] / MM],
            [r[2] * s, r[5] * s, r[8] * s, t[2] / MM],
            [0.0, 0.0, 0.0, 1.0]]


def apply(m, p):
    return [sum(m[i][j] * p[j] for j in range(3)) + m[i][3] for i in range(3)]


def world_bbox(m, bmin, bmax):
    pts = [apply(m, (x, y, z)) for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1]) for z in (bmin[2], bmax[2])]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def r4(v):
    return [round(x, 4) for x in v]


def sw_material(doc):
    """SolidWorks material name of a part, or ''. Tries the APIs that exist across versions."""
    for call in (lambda: doc.GetMaterialPropertyName2("", byref()),
                 lambda: doc.MaterialIdName):
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
    """Part-level appearance colour [r, g, b] (0..1) and transparency, or None."""
    try:
        v = list(doc.MaterialPropertyValues or ())
    except Exception:  # noqa: BLE001
        return None
    if len(v) < 9:
        return None
    return {"rgb": r4(v[:3]), "transparency": round(v[7], 3)}


def propose_material(part_name, sw_mat, lib):
    """Library material for a part: SolidWorks material first, then name rules, then the default."""
    if sw_mat:
        for key, mat in lib["solidworks_material_map"].items():
            if not key.startswith("_") and key in sw_mat.lower():
                return {"material": mat, "source": "solidworks_material", "sw_material": sw_mat, "confidence": "medium"}
    for pattern, mat in lib["name_rules"]["rules"]:
        if re.search(pattern, part_name, re.I):
            return {"material": mat, "source": "name_rule", "rule": pattern, "confidence": "low"}
    return {"material": lib["name_rules"]["default"], "source": "default", "confidence": "low"}


STEP242_ERRORS = {1: "invalid path", 3: "unknown error", 4: "MBD licence not available",
                  5: "edition error", 6: "custom property error"}


def export_step(app, doc, out, ap242=False):
    """STEP export. AP214 through SaveAs3 (the AP242 preference value is ignored by plain
    Save As on SOLIDWORKS 2025 and silently falls back to AP203). With ap242=True, try
    the MBD route PublishSTEP242File first (needs a SOLIDWORKS MBD licence); on failure
    fall back to AP214 and return the reason."""
    out.parent.mkdir(parents=True, exist_ok=True)
    e = byref()
    app.ActivateDoc3(doc.GetPathName or doc.GetTitle, False, 0, e)
    if ap242:
        res = doc.Extension.PublishSTEP242File(str(out.with_suffix(".stp")))
        if res == 0 and out.with_suffix(".stp").exists():
            out.with_suffix(".stp").replace(out)
            return "AP242 (PublishSTEP242File)", None
        reason = STEP242_ERRORS.get(res, f"error {res}")
    ok = doc.Extension.SaveAs3(str(out), 0, 1, NOTHING, NOTHING, e, byref())
    if not (ok and out.exists() and out.stat().st_size > 200):
        raise RuntimeError(f"STEP export failed: {out}")
    head = out.read_text(errors="replace")[:4000]
    schema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head)
    schema = schema.group(1) if schema else "unknown"
    return schema, (reason if ap242 else None)


def labels_from_assembly_json(folder, comps):
    """Map SolidWorks Name2 -> label from assemblies/<name>/assembly.json (insertion order per part)."""
    spec = folder / "assembly.json"
    if not spec.exists():
        return {}
    entries = json.loads(spec.read_text()).get("components", [])
    by_part = {}
    for e in entries:
        part = e.get("part") or pathlib.Path(e.get("file", "")).stem
        by_part.setdefault(part.lower(), []).append(e.get("label") or part)
    out = {}
    for c in comps:
        part, _, n = c["id"].rpartition("-")
        lst = by_part.get(part.lower())
        if lst and n.isdigit() and int(n) <= len(lst):
            out[c["id"]] = lst[int(n) - 1]
    return out


# ------------------------------------------------------------ explode offsets

def explode_auto(comps, parts, axis="z", gap=None):
    """Axial stack explode from the assembled positions: components are ranked by their centre
    along `axis` (components at the same level share a rank) and each rank moves by
    rank * gap, relative to the largest component, which stays put. Offsets only, in mm;
    the assembled transforms are never changed."""
    ax = "xyz".index(axis)
    vis = [c for c in comps if c["visible"] and not c["suppressed"] and c["part"]]
    if not vis:
        return {}
    centres, sizes = {}, {}
    for c in vis:
        lo, hi = c["world_bbox_mm"]
        centres[c["id"]] = (lo[ax] + hi[ax]) / 2
        sizes[c["id"]] = math.prod(max(h - l, 1e-3) for l, h in zip(lo, hi))
    span = max(c["world_bbox_mm"][1][ax] for c in vis) - min(c["world_bbox_mm"][0][ax] for c in vis)
    gap = gap or round(max(span * 0.07, 5.0), 1)
    tol = max(span * 0.01, 0.5)
    order = sorted(vis, key=lambda c: centres[c["id"]])
    ranks, rank, last = {}, -1, None
    for c in order:
        if last is None or centres[c["id"]] - last > tol:
            rank += 1
        last = centres[c["id"]]
        ranks[c["id"]] = rank
    anchor = max(vis, key=lambda c: sizes[c["id"]])["id"]
    out = {}
    for c in vis:
        off = [0.0, 0.0, 0.0]
        off[ax] = round((ranks[c["id"]] - ranks[anchor]) * gap, 3)
        out[c["id"]] = off
    return {"method": "auto_axial", "axis": axis, "gap_mm": gap, "anchor": anchor, "offsets_mm": out}


def explode_from_assembly(comps, other_folder):
    """Offsets from a designed exploded assembly (assemblies/<name>_exploded/assembly.json):
    components are matched by label, else by part and occurrence order."""
    spec = json.loads((pathlib.Path(other_folder) / "assembly.json").read_text())
    entries, seen = [], {}
    for e in spec["components"]:
        part = (e.get("part") or pathlib.Path(e.get("file", "")).stem).lower()
        seen[part] = seen.get(part, 0) + 1
        entries.append((e.get("label"), part, seen[part], e))
    out, unmatched = {}, []
    for c in comps:
        if not c["part"]:
            continue
        part, _, n = c["id"].rpartition("-")
        hit = next((e for lb, p, k, e in entries if c.get("label") and lb == c.get("label")), None) or \
            next((e for lb, p, k, e in entries if p == part.lower() and str(k) == n), None)
        if hit is None:
            unmatched.append(c["id"])
            continue
        if "xform" in hit:
            tgt = [hit["xform"][9 + i] for i in range(3)]
        else:
            tgt = list(hit.get("at", (0, 0, 0)))
        cur = [c["transform"][i][3] for i in range(3)]
        out[c["id"]] = [round(t - k, 3) for t, k in zip(tgt, cur)]
    return {"method": "from_assembly", "source": str(other_folder), "offsets_mm": out, "unmatched": unmatched,
            "note": "translation only; a rotated component keeps its assembled rotation"}


# ------------------------------------------------------------ main export

def run(target, out_folder=None, exploded_from=None, explode_axis="z", ap242=False):
    cad, folder = find_cad(target)
    folder = pathlib.Path(out_folder).resolve() if out_folder else folder
    lib = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))
    step_dir = rc.path(folder, "step")
    app = connect()
    before = open_titles(app)
    prev_ap = app.GetUserPreferenceIntegerValue(SW_STEP_AP)
    prev_app = app.GetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES)
    app.SetUserPreferenceIntegerValue(SW_STEP_AP, 214)
    app.SetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES, True)
    try:
        is_asm = cad.suffix.lower() == ".sldasm"
        e, w = byref(), byref()
        doc = app.OpenDoc6(str(cad), 2 if is_asm else 1, OPEN_SILENT_READONLY, "", e, w)
        if doc is None:
            raise RuntimeError(f"could not open {cad} (error {e.value})")
        name = cad.stem
        parts, comps, hierarchy = {}, [], [{"id": name, "parent": None, "kind": "assembly" if is_asm else "part"}]

        def add_part(pdoc, path):
            stem = pathlib.Path(path).stem
            if stem in parts:
                return stem
            box = list(pdoc.GetPartBox(True)) if pdoc is not None else [0] * 6
            mat = sw_material(pdoc) if pdoc is not None else ""
            parts[stem] = {
                "part_id": stem, "sw_path": str(path),
                "bbox_mm": {"min": r4([v / MM for v in box[:3]]), "max": r4([v / MM for v in box[3:]])},
                "sw_material": mat, "sw_appearance": sw_appearance(pdoc) if pdoc is not None else None,
                "material": propose_material(stem, mat, lib),
                "step": None,
            }
            return stem

        if is_asm:
            for c in doc.GetComponents(False) or ():
                cid = c.Name2
                par = c.GetParent
                children = c.GetChildren or ()
                pdoc = c.GetModelDoc2
                is_sub = len(children) > 0
                xf = matrix_from_sw(list(c.Transform2.ArrayData))
                entry = {"id": cid, "name": cid.split("/")[-1], "parent": par.Name2 if par is not None else name,
                         "transform": [r4(row) for row in xf], "suppressed": bool(c.IsSuppressed),
                         "visible": c.Visible == 1, "configuration": c.ReferencedConfiguration,
                         "sw_path": c.GetPathName}
                if is_sub:
                    hierarchy.append({"id": cid, "parent": entry["parent"], "kind": "subassembly"})
                    continue
                entry["part"] = add_part(pdoc, c.GetPathName) if pdoc is not None else None
                if entry["part"]:
                    bb = parts[entry["part"]]["bbox_mm"]
                    lo, hi = world_bbox(xf, bb["min"], bb["max"])
                    entry["world_bbox_mm"] = [r4(lo), r4(hi)]
                comps.append(entry)
            box = list(doc.GetBox(0))
        else:
            stem = add_part(doc, cad)
            bb = parts[stem]["bbox_mm"]
            ident = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
            comps.append({"id": f"{stem}-1", "name": f"{stem}-1", "parent": name, "part": stem, "transform": ident,
                          "suppressed": False, "visible": True, "configuration": "", "sw_path": str(cad),
                          "world_bbox_mm": [bb["min"], bb["max"]]})
            box = list(doc.GetPartBox(True))
        # assembly STEP (for archive and the import cross-check), then one STEP per unique part
        asm_step = step_dir / f"{name}.step"
        schema, ap242_fail = export_step(app, doc, asm_step, ap242)
        for stem, p in parts.items():
            pdoc = app.OpenDoc6(p["sw_path"], 1, OPEN_SILENT_READONLY, "", byref(), byref()) if is_asm else doc
            out = step_dir / "parts" / f"{stem}.step"
            export_step(app, pdoc, out, ap242)
            p["step"] = str(out.relative_to(rc.render_dir(folder))).replace("\\", "/")
            if is_asm and pdoc.GetTitle not in before:
                app.CloseDoc(pdoc.GetTitle)
        # The part template gives every part the same material ("Steel") and the default
        # appearance colour. That is not design intent: fall back to the name rules.
        mats = {p["sw_material"] for p in parts.values()}
        for p in parts.values():
            app_rgb = (p["sw_appearance"] or {}).get("rgb")
            p["sw_appearance_is_default"] = bool(app_rgb) and all(abs(a - b) < 0.002 for a, b in zip(app_rgb, SW_DEFAULT_RGB))
            if p["sw_material"] and len(parts) > 1 and len(mats) == 1:
                p["material"] = propose_material(p["part_id"], "", lib)
                p["material"]["note"] = f"every part has SolidWorks material '{p['sw_material']}' (template default), ignored"
        labels = labels_from_assembly_json(cad.parent, comps)
        for c in comps:
            if c["id"] in labels:
                c["label"] = labels[c["id"]]
        app.CloseDoc(doc.GetTitle)
    finally:
        app.SetUserPreferenceIntegerValue(SW_STEP_AP, prev_ap)
        app.SetUserPreferenceToggle(SW_STEP_EXPORT_APPEARANCES, prev_app)
        for t in open_titles(app) - before:  # leftovers from this run only
            app.CloseDoc(t)

    exploded = explode_from_assembly(comps, exploded_from) if exploded_from else explode_auto(comps, parts, explode_axis)
    manifest = {
        "schema_version": "1.0",
        "project": folder.name,
        "assembly": name,
        "source_cad": str(cad),
        "exported": dt.datetime.now().isoformat(timespec="seconds"),
        "units": {"length": "mm", "up_axis": "Z"},
        "step": {"assembly": str(asm_step.relative_to(rc.render_dir(folder))).replace("\\", "/"),
                 "schema": schema, "protocol": "AP242" if schema.startswith("AP242") else {"AUTOMOTIVE_DESIGN": "AP214", "CONFIG_CONTROL_DESIGN": "AP203"}.get(schema, schema), "ap242_requested": ap242, "ap242_fallback_reason": ap242_fail, "appearances": True},
        "bbox_mm": {"min": r4([v / MM for v in box[:3]]), "max": r4([v / MM for v in box[3:]]),
                    "size": r4([(box[i + 3] - box[i]) / MM for i in range(3)])},
        "hierarchy": hierarchy,
        "parts": parts,
        "components": comps,
        "exploded": exploded,
        "_notes": [
            "transform: 4x4, column-vector convention, translation in mm, relative to the top assembly",
            "component id = SolidWorks Name2 (unique, stable while the assembly is not restructured)",
            "material = proposal; per-component overrides live in render/settings/scene.json and survive re-export",
        ],
    }
    mpath = rc.path(folder, "manifest")
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(f"STEP schema {schema}{' (AP242 failed: ' + ap242_fail + ')' if ap242_fail else ''}; {len(parts)} unique parts, {len(comps)} components")
    print(f"bbox {manifest['bbox_mm']['size']} mm")
    print(f"manifest -> {mpath}")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="assembly/project folder, or a .SLDASM/.SLDPRT file")
    ap.add_argument("--out", help="folder that gets render/ (default: the CAD file's folder)")
    ap.add_argument("--exploded-from", help="folder with assembly.json of a designed exploded assembly")
    ap.add_argument("--explode-axis", default="z", choices="xyz")
    ap.add_argument("--ap242", action="store_true", help="try AP242 via PublishSTEP242File (needs SOLIDWORKS MBD)")
    a = ap.parse_args()
    run(a.target, a.out, a.exploded_from, a.explode_axis, a.ap242)
