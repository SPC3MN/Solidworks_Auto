"""FreeCAD adapter: .FCStd -> STEP per unique part + product manifest.

Runs FreeCAD headless (FreeCADCmd / freecadcmd) with freecad_dump.py, then builds the
manifest here. FreeCAD is found from FREECAD_CMD, config/render.local.json
{"freecad": ".../FreeCADCmd.exe"}, ~/Tools/FreeCAD*/bin, Program Files/FreeCAD*/bin,
/Applications/FreeCAD.app, or PATH.

Colours: a headless FreeCAD has no view providers, so the shape colour is read from the
.FCStd's GuiDocument.xml (ShapeColor, a packed RGBA integer) when present; otherwise the
parts are coloured by the material library alone. STEP from FreeCAD carries no colours.

Status: written against the FreeCAD 0.21 / 1.x Python API; not yet run against a real
FreeCAD on the development machine (none installed). The fallback that is verified: export
STEP from FreeCAD (File > Export, STEP with assembly structure) and use the file adapter.
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from . import common as C

EXTENSIONS = (".fcstd",)
DUMP = pathlib.Path(__file__).with_name("freecad_dump.py")


def freecad_cmd():
    import render_config as rc
    cands = [os.environ.get("FREECAD_CMD"), rc.local_config().get("freecad")]
    home = pathlib.Path.home()
    for base in (home / "Tools", pathlib.Path(r"C:\Program Files"), pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"):
        for exe in ("FreeCADCmd.exe", "freecadcmd.exe"):
            cands += sorted(glob.glob(str(base / "FreeCAD*" / "bin" / exe)), reverse=True)
    cands += ["/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd", shutil.which("freecadcmd"), shutil.which("FreeCADCmd")]
    for c in cands:
        if c and pathlib.Path(c).is_file():
            return pathlib.Path(c)
    return None


def find_file(target):
    t = pathlib.Path(target).resolve()
    if t.is_file():
        return t
    found = sorted(t.glob("*.FCStd")) + sorted(t.glob("*.fcstd")) + sorted(t.glob("design/*.FCStd"))
    return found[0] if found else None


def gui_colors(fcstd):
    """{object name: [r, g, b]} from GuiDocument.xml (ShapeColor, packed 0xRRGGBBAA)."""
    try:
        with zipfile.ZipFile(fcstd) as z:
            root = ET.fromstring(z.read("GuiDocument.xml"))
    except (KeyError, OSError, zipfile.BadZipFile, ET.ParseError):
        return {}
    out = {}
    for vp in root.iter("ViewProvider"):
        for prop in vp.iter("Property"):
            if prop.get("name") == "ShapeColor":
                col = prop.find("PropertyColor")
                if col is not None and col.get("value", "").isdigit():
                    v = int(col.get("value"))
                    out[vp.get("name")] = [round(((v >> s) & 255) / 255, 4) for s in (24, 16, 8)]
    return out


def run_dump(fcstd, render_dir):
    exe = freecad_cmd()
    if exe is None:
        sys.exit("FreeCAD not found. Set FREECAD_CMD or config/render.local.json {\"freecad\": \".../FreeCADCmd.exe\"}, "
                 "or export STEP from FreeCAD and pass the .step file instead (file adapter).")
    geo = pathlib.Path(render_dir) / "export" / "geometry"
    raw = pathlib.Path(tempfile.mkdtemp(prefix="fcdump_")) / "raw.json"
    env = dict(os.environ, RENDER_FC_ARGS=json.dumps({"file": str(fcstd), "parts_dir": str(geo / "parts"),
                                                      "assembly_step": str(geo / f"{fcstd.stem}.step"), "out_json": str(raw)}))
    proc = subprocess.run([str(exe), str(DUMP)], env=env, capture_output=True, text=True, timeout=3600)
    err = raw.with_name(raw.name + ".error")
    if err.exists() or not raw.exists():
        detail = err.read_text() if err.exists() else (proc.stdout[-3000:] + proc.stderr[-3000:])
        sys.exit(f"FreeCAD export failed ({exe}):\n{detail}")
    return json.loads(raw.read_text(encoding="utf-8")), exe


def export(target, render_dir, lib, *, exploded_from=None, explode_axis="z", **_):
    fcstd = find_file(target)
    if fcstd is None:
        sys.exit(f"no .FCStd found in {target}")
    raw, exe = run_dump(fcstd, render_dir)
    man = C.new_manifest(project=pathlib.Path(render_dir).parent.name, assembly=raw["root"], adapter="freecad",
                         application="FreeCAD", application_version=raw["freecad_version"], file=fcstd,
                         reference="cad_kernel", reference_note="part bboxes measured by FreeCAD (OpenCASCADE)",
                         details={"freecad_cmd": str(exe), "warnings": raw["warnings"]})
    man["hierarchy"] = [{k: v for k, v in n.items() if k != "label"} for n in raw["hierarchy"]]
    colors = gui_colors(fcstd)
    for pid, p in raw["parts"].items():
        obj = p["object"].split("#", 1)[1]
        man["parts"][pid] = C.part_entry(
            pid, {"file": C.rel(p["file"], render_dir), "format": "step", "scale_to_m": None, "up_axis": "Z"},
            p["bbox_min"], p["bbox_max"], source_material=p["material_name"], source_color=colors.get(obj),
            source_path=f"{fcstd}#{obj}", lib=lib)
    C.drop_template_material(man["parts"], lib)
    for c in raw["components"]:
        e = C.component_entry(c["id"], c["part"], c["transform"], c["parent"], man["parts"], name=c["name"],
                              label=c.get("label"), visible=c["visible"], source={"object_path": c["id"]})
        e["world_bbox_exact_mm"] = [C.r4(c["world_bbox_mm"][0]), C.r4(c["world_bbox_mm"][1])]
        man["components"].append(e)
    vis = [c for c in man["components"] if c["visible"]]
    if not vis:
        sys.exit("FreeCAD document has no visible solid")
    man["bbox_mm"] = C.union_bbox(c["world_bbox_exact_mm"] for c in vis)
    asm = pathlib.Path(render_dir) / "export" / "geometry" / f"{fcstd.stem}.step"
    if asm.exists():
        man["geometry"]["assembly"] = {"file": C.rel(asm, render_dir), "format": "step", "scale_to_m": None, "up_axis": "Z"}
    ref = raw.get("freecad_bbox")
    if ref:
        ref_size = [h - l for l, h in zip(*ref)]
        ok = all(abs(a - b) <= max(0.5, 0.01 * b) for a, b in zip(man["bbox_mm"]["size"], ref_size))
        man["validation"]["freecad_bbox_check"] = {"pass": ok, "walk": man["bbox_mm"]["size"], "freecad": C.r4(ref_size)}
        if not ok:
            sys.exit(f"the document walk does not reproduce FreeCAD's own bbox ({man['bbox_mm']['size']} vs {C.r4(ref_size)}): "
                     "an unsupported link or container type. Export STEP from FreeCAD and use the file adapter.")
    for w in raw["warnings"]:
        print("WARNING", w)
    man["exploded"] = C.explode_from_assembly(man["components"], exploded_from) if exploded_from \
        else C.explode_auto(man["components"], explode_axis)
    print(f"FreeCAD {raw['freecad_version']} {fcstd.name}: {len(man['parts'])} unique parts, {len(man['components'])} components")
    return man
