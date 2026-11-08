"""CAD source adapters for the render pipeline.

An adapter turns one CAD source into the source-neutral product package:
    <folder>/render/export/product_manifest.json   (schema in common.py)
    <folder>/render/export/geometry/parts/*        one geometry file per unique part
Everything after that (Blender import, materials, scenes, approval, finals) is the same for
every source.

    solidworks  .SLDASM / .SLDPRT     live SolidWorks over COM (Windows)
    freecad     .FCStd                FreeCADCmd headless
    file        .step .stp .glb .gltf .obj .stl .ply .fbx .usd*   via Blender; any other CAD
                                      system exports STEP (best) or glTF and uses this

Adding a source = one module with EXTENSIONS and
    export(target, render_dir, lib, **options) -> manifest dict
built from common.new_manifest / part_entry / component_entry. See docs/rendering.md.
"""
import importlib
import json
import pathlib

from . import common

ADAPTERS = ("solidworks", "freecad", "mesh_file")
NAMES = {"solidworks": "solidworks", "freecad": "freecad", "file": "mesh_file", "mesh_file": "mesh_file"}


def module(name):
    return importlib.import_module(f"{__name__}.{NAMES[name]}")


def detect(target):
    """Adapter name for a target file or folder (a folder: the first CAD file found in it)."""
    t = pathlib.Path(target)
    if t.is_file():
        ext = t.suffix.lower()
        for a in ADAPTERS:
            if ext in module(a).EXTENSIONS:
                return "file" if a == "mesh_file" else a
        raise SystemExit(f"no adapter for {t.suffix} files (known: SolidWorks, FreeCAD, {', '.join(common.FORMATS)})")
    if t.is_dir():
        if any(t.glob("*.SLDASM")) or any(t.glob("design/*.SLDPRT")) or any(t.glob("*.SLDPRT")):
            return "solidworks"
        if any(t.glob("*.FCStd")) or any(t.glob("design/*.FCStd")):
            return "freecad"
        if module("mesh_file").find_file(t):
            return "file"
    raise SystemExit(f"no CAD file found in {t}")


def workspace(target, out=None):
    """The folder that gets render/: --out, else the target folder, else the file's folder."""
    if out:
        return pathlib.Path(out).resolve()
    t = pathlib.Path(target).resolve()
    return t.parent if t.is_file() else t


def export(target, out=None, source=None, **options):
    """Run the adapter for `target` and write the manifest. Returns the manifest."""
    import render_config as rc
    name = source or detect(target)
    folder = workspace(target, out)
    rdir = rc.render_dir(folder)
    lib = json.loads((rc.LIB / "materials.json").read_text(encoding="utf-8"))
    man = module(name).export(target, rdir, lib, **options)
    man["project"] = folder.name
    common.finish(man)
    path = common.save(man, rc.path(folder, "manifest"))
    print(f"{name}: {len(man['parts'])} unique parts, {len(man['components'])} components, bbox {man['bbox_mm']['size']} mm")
    print(f"manifest -> {path}")
    return man
