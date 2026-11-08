"""Generic file adapter: a STEP, glTF/GLB, OBJ, STL, PLY, FBX or USD file -> product manifest.

The way in for any CAD system without its own adapter: export STEP (preferred: exact
geometry, units, assembly structure, colours) or glTF from that system and point the
pipeline at the file. Blender reads it (scripts/blender/bl_ingest.py), recovers components,
instances and subassemblies, and writes one GLB per unique part.

OBJ, STL and PLY carry no units and no up axis: pass --units (default mm) and --up (default Z,
the CAD convention). Because the expected sizes come from the same file that is imported,
the import checks prove the round trip and the placement but not the scale: give one known
dimension with --expect-size X,Y,Z (mm, overall) and it is checked here.
"""
import json
import pathlib
import shutil
import sys
import tempfile

from . import common as C

EXTENSIONS = tuple(C.FORMATS)


def find_file(target):
    t = pathlib.Path(target).resolve()
    if t.is_file():
        return t
    for ext in (".step", ".stp", ".glb", ".gltf", ".fbx", ".usdz", ".usd", ".obj", ".stl", ".ply"):
        found = sorted(t.glob(f"*{ext}"))
        if found:
            return found[0]
    return None


def run_ingest(src, render_dir, fmt, scale, up, tol_linear=None, tol_angular=None):
    import render_config as rc
    raw = pathlib.Path(tempfile.mkdtemp(prefix="ingest_")) / "raw.json"
    args = ["--source", src, "--render-dir", render_dir, "--format", fmt, "--up", up, "--out-json", raw]
    if scale is not None:
        args += ["--scale-to-m", scale]
    if tol_linear:
        args += ["--tol-linear", tol_linear]
    if tol_angular:
        args += ["--tol-angular", tol_angular]
    code, _ = rc.run_blender("bl_ingest.py", *args)
    if code or not raw.exists():
        sys.exit(f"could not read {src} in Blender (see output above)")
    return json.loads(raw.read_text(encoding="utf-8"))


def check_size(size, expect):
    """expect: [x, y, z] in mm (0 or None = unknown axis). 2 % tolerance per axis."""
    bad = [(i, s, e) for i, (s, e) in enumerate(zip(size, expect)) if e and abs(s - e) > max(0.02 * e, 0.2)]
    return not bad, bad


def export(target, render_dir, lib, *, units="mm", up="Z", expect_size=None, exploded_from=None, explode_axis="z",
           tol_linear=None, tol_angular=None, **_):
    src = find_file(target)
    if src is None:
        sys.exit(f"no geometry file found in {target} (known: {', '.join(EXTENSIONS)})")
    fmt = C.geometry_format(src)
    scale = C.UNIT_TO_M[units] if fmt in ("obj", "stl", "ply") else None
    raw = run_ingest(src, render_dir, fmt, scale, up, tol_linear, tol_angular)
    unitless = fmt in ("obj", "stl", "ply")
    man = C.new_manifest(
        project=pathlib.Path(render_dir).parent.name, assembly=raw["root"], adapter="file",
        application=f"{fmt.upper()} file", application_version="", file=src, reference="source_file",
        reference_note=("expected sizes were measured from the imported file itself: the import checks prove the "
                        "round trip and placement, not the scale" + ("; units assumed " + units if unitless else "")),
        details={"format": fmt, "units_assumed": units if unitless else None, "up_axis_assumed": up if unitless else None,
                 "read_with": f"Blender {raw['blender']}"})
    man["hierarchy"] = raw["hierarchy"]
    for pid, p in raw["parts"].items():
        man["parts"][pid] = C.part_entry(pid, {"file": p["file"], "format": "gltf", "scale_to_m": None, "up_axis": "Z"},
                                         p["bbox_min"], p["bbox_max"], source_material=p["material_name"],
                                         source_color=p["color"], source_path=str(src), lib=lib)
    C.drop_template_material(man["parts"], lib)
    for c in raw["components"]:
        e = C.component_entry(c["id"], c["part"], c["transform"], c["parent"], man["parts"], name=c["name"],
                              visible=c["visible"], source=c["source"])
        e["world_bbox_exact_mm"] = [C.r4(c["world_bbox_mm"][0]), C.r4(c["world_bbox_mm"][1])]
        man["components"].append(e)
    lo, hi = raw["bbox_mm"]["min"], raw["bbox_mm"]["max"]
    man["bbox_mm"] = {"min": C.r4(lo), "max": C.r4(hi), "size": C.r4([h - l for l, h in zip(lo, hi)])}
    # keep a copy of the source in the workspace, so it is self-contained (and the STEP serves the cross-check)
    keep = pathlib.Path(render_dir) / "export" / "geometry" / f"source{src.suffix.lower()}"
    if src.resolve() != keep.resolve():
        shutil.copy2(src, keep)
    man["source"]["details"]["copy"] = C.rel(keep, render_dir)
    if fmt == "step":
        man["geometry"]["assembly"] = {"file": C.rel(keep, render_dir), "format": "step", "scale_to_m": None, "up_axis": "Z"}
    size = man["bbox_mm"]["size"]
    if expect_size:
        ok, bad = check_size(size, expect_size)
        man["validation"]["expected_size_mm"] = expect_size
        man["validation"]["size_check"] = "pass" if ok else f"FAIL {bad}"
        if not ok:
            sys.exit(f"overall size {size} mm does not match --expect-size {expect_size}: wrong --units or --up? "
                     f"(axis, measured, expected): {bad}")
    elif max(size) < 1 or max(size) > 20000:
        print(f"WARNING overall size {size} mm looks wrong: check --units (given {units})")
    man["exploded"] = C.explode_from_assembly(man["components"], exploded_from) if exploded_from \
        else C.explode_auto(man["components"], explode_axis)
    print(f"{fmt.upper()} {src.name}: {len(man['parts'])} unique parts, {len(man['components'])} components")
    return man
