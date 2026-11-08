"""Source-neutral product manifest: the one contract between CAD adapters and Blender.

Every adapter (SolidWorks, FreeCAD, a plain STEP/glTF/OBJ/STL file, ...) writes the same
`render/export/product_manifest.json` plus one geometry file per unique part. Nothing after
the adapter knows which CAD system the product came from. Pure Python (no CAD, no bpy), so
it is imported by the adapters, by render_cli.py and by the Blender scripts alike.

Schema 2.0 (see docs/rendering.md, "Product manifest"):

    schema_version  "2.0"
    project         workspace folder name
    assembly        product name (also names the .blend files)
    source          {adapter, application, application_version, file, exported, details{...}}
    units           {"length": "mm", "up_axis": "Z"}   always: adapters convert
    bbox_mm         {min, max, size}  of the visible product
    hierarchy       [{id, parent, kind: assembly|subassembly|part}]   first entry is the root
    parts           {part_id: {part_id, geometry{file, format, scale_to_m, up_axis}, bbox_mm{min,max},
                     source_material, source_color, material{material, source, confidence, ...}, source_path}}
    components      [{id, name, label?, parent, part, transform 4x4 (column vectors, mm),
                     visible, suppressed, world_bbox_mm [min, max], source{...}}]
    geometry        {"assembly": {file, format, ...} | null}   whole product, for the import cross-check
    exploded        {method, offsets_mm{component id: [dx, dy, dz]}, ...}
    validation      {reference: cad_kernel | source_file, note}

`validation.reference` says how independent the import checks are: "cad_kernel" means the
expected bboxes were measured by the CAD system itself (SolidWorks, FreeCAD/OCC); "source_file"
means they were measured from the same file that is imported, so the checks prove the
round trip and the placement, not the scale. Pass a known size (`--expect-size`) then.
"""
import datetime as dt
import json
import math
import pathlib
import re

SCHEMA_VERSION = "2.0"
IDENTITY = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
# geometry formats the Blender import knows (scripts/blender/bl_import.py: IMPORTERS)
FORMATS = {".step": "step", ".stp": "step", ".glb": "gltf", ".gltf": "gltf", ".obj": "obj", ".stl": "stl",
           ".ply": "ply", ".fbx": "fbx", ".usd": "usd", ".usda": "usd", ".usdc": "usd", ".usdz": "usd"}
UNIT_TO_M = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254, "ft": 0.3048}


# ------------------------------------------------------------------ maths

def apply(m, p):
    return [sum(m[i][j] * p[j] for j in range(3)) + m[i][3] for i in range(3)]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def world_bbox(m, bmin, bmax):
    pts = [apply(m, (x, y, z)) for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1]) for z in (bmin[2], bmax[2])]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def r4(v):
    return [round(float(x), 4) for x in v]


def union_bbox(boxes):
    boxes = list(boxes)
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    return {"min": r4(lo), "max": r4(hi), "size": r4([h - l for l, h in zip(lo, hi)])}


def rgb_hex(rgb):
    """sRGB 0..1 triple -> '#RRGGBB' (the form every source colour takes in the manifest)."""
    if not rgb:
        return None
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in list(rgb)[:3])


def geometry_format(path):
    fmt = FORMATS.get(pathlib.Path(path).suffix.lower())
    if fmt is None:
        raise ValueError(f"unsupported geometry format: {path} (known: {', '.join(sorted(FORMATS))})")
    return fmt


# ------------------------------------------------------------------ materials

def material_map(lib):
    """CAD material name (substring) -> library material. `solidworks_material_map` is the old name."""
    return lib.get("cad_material_map") or lib.get("solidworks_material_map") or {}


GENERIC_MATERIAL = re.compile(r"^(mat|material|default|defaultmaterial|none|color|colour)?[ _.-]*\d*$", re.I)


def meaningful_material(name):
    """'' for the placeholder names exporters invent (mat_0, Material.001, DefaultMaterial)."""
    return "" if not name or GENERIC_MATERIAL.match(name.strip()) else name


def propose_material(part_name, cad_material, lib):
    """Library material for a part: the CAD material name first, then name rules, then the default.
    Every proposal carries its source and a confidence, so the skill knows what to review."""
    cad_material = meaningful_material(cad_material)
    if cad_material:
        for key, mat in material_map(lib).items():
            if not key.startswith("_") and key in cad_material.lower():
                return {"material": mat, "source": "cad_material", "cad_material": cad_material, "confidence": "medium"}
    for pattern, mat in lib["name_rules"]["rules"]:
        if re.search(pattern, part_name, re.I):
            return {"material": mat, "source": "name_rule", "rule": pattern, "confidence": "low"}
    return {"material": lib["name_rules"]["default"], "source": "default", "confidence": "low"}


def drop_template_material(parts, lib):
    """When every part carries the same CAD material (a template default such as SolidWorks'
    "Steel"), it says nothing about design intent: fall back to the name rules. The same for
    a colour every part shares (an uncoloured model's default appearance)."""
    cols = {p.get("source_color") for p in parts.values()}
    if len(parts) > 1 and len(cols) == 1 and next(iter(cols)):
        for p in parts.values():
            p["source_color_note"] = f"every part has colour {p['source_color']} (default appearance), ignored"
            p["source_color"] = None
    mats = {p.get("source_material") for p in parts.values()}
    if len(parts) > 1 and len(mats) == 1 and next(iter(mats)):
        only = next(iter(mats))
        for p in parts.values():
            p["material"] = propose_material(p["part_id"], "", lib)
            p["material"]["note"] = f"every part has CAD material '{only}' (template default), ignored"


# ------------------------------------------------------------------ explode offsets

def explode_auto(comps, axis="z", gap=None):
    """Axial stack explode from the assembled positions: components are ranked by their centre
    along `axis` (components at the same level share a rank) and each rank moves by
    rank * gap, relative to the largest component, which stays put. Offsets only, in mm;
    the assembled transforms are never changed."""
    ax = "xyz".index(axis)
    vis = [c for c in comps if c["visible"] and not c["suppressed"] and c.get("part")]
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


def explode_from_layout(comps, layout):
    """Offsets from a designed exploded layout: `layout` is a list of {part, label?, at|xform}
    in assembly order (this repo's assemblies/<name>_exploded/assembly.json). Components are
    matched by label, else by part and occurrence order. Translation only."""
    entries, seen = [], {}
    for e in layout:
        part = (e.get("part") or pathlib.Path(e.get("file", "")).stem).lower()
        seen[part] = seen.get(part, 0) + 1
        entries.append((e.get("label"), part, seen[part], e))
    occ, out, unmatched = {}, {}, []
    for c in comps:
        if not c.get("part"):
            continue
        part = c["part"].lower()
        occ[part] = occ.get(part, 0) + 1
        n = c.get("occurrence") or occ[part]
        hit = next((e for lb, p, k, e in entries if c.get("label") and lb == c.get("label")), None) or \
            next((e for lb, p, k, e in entries if p == part and k == n), None)
        if hit is None:
            unmatched.append(c["id"])
            continue
        tgt = [hit["xform"][9 + i] for i in range(3)] if "xform" in hit else list(hit.get("at", (0, 0, 0)))
        cur = [c["transform"][i][3] for i in range(3)]
        out[c["id"]] = [round(t - k, 3) for t, k in zip(tgt, cur)]
    return {"method": "from_layout", "offsets_mm": out, "unmatched": unmatched,
            "note": "translation only; a rotated component keeps its assembled rotation"}


def explode_from_assembly(comps, other_folder):
    spec = json.loads((pathlib.Path(other_folder) / "assembly.json").read_text())
    ex = explode_from_layout(comps, spec["components"])
    ex["source"] = str(other_folder)
    return ex


def labels_from_assembly_json(folder, comps):
    """Component labels from this repo's assemblies/<name>/assembly.json (insertion order per part)."""
    spec = pathlib.Path(folder) / "assembly.json"
    if not spec.exists():
        return {}
    by_part = {}
    for e in json.loads(spec.read_text()).get("components", []):
        part = e.get("part") or pathlib.Path(e.get("file", "")).stem
        by_part.setdefault(part.lower(), []).append(e.get("label") or part)
    occ, out = {}, {}
    for c in comps:
        if not c.get("part"):
            continue
        k = c["part"].lower()
        occ[k] = occ.get(k, 0) + 1
        n = c.get("occurrence") or occ[k]
        lst = by_part.get(k)
        if lst and n <= len(lst):
            out[c["id"]] = lst[n - 1]
    return out


# ------------------------------------------------------------------ manifest

def new_manifest(*, project, assembly, adapter, application, application_version="", file="", details=None,
                 reference="cad_kernel", reference_note=""):
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "assembly": assembly,
        "source": {"adapter": adapter, "application": application, "application_version": application_version,
                   "file": str(file), "exported": dt.datetime.now().isoformat(timespec="seconds"),
                   "details": details or {}},
        "units": {"length": "mm", "up_axis": "Z"},
        "bbox_mm": None,
        "hierarchy": [{"id": assembly, "parent": None, "kind": "assembly"}],
        "parts": {},
        "components": [],
        "geometry": {"assembly": None},
        "exploded": {},
        "validation": {"reference": reference, "note": reference_note},
        "_notes": [
            "transform: 4x4, column-vector convention, translation in mm, relative to the product root",
            "component id: stable id from the CAD source (SolidWorks Name2, FreeCAD object path, STEP node path)",
            "material: a proposal; per-part and per-component choices live in render/settings/scene.json and survive re-export",
        ],
    }


def part_entry(part_id, geometry, bbox_min, bbox_max, *, source_material="", source_color=None, source_path="", lib=None):
    """source_color: the part colour in the CAD source, sRGB, as [r, g, b] 0..1 or '#RRGGBB'."""
    if source_color and not isinstance(source_color, str):
        source_color = rgb_hex(source_color)
    e = {"part_id": part_id, "geometry": geometry, "bbox_mm": {"min": r4(bbox_min), "max": r4(bbox_max)},
         "source_material": source_material or "", "source_color": source_color, "source_path": str(source_path)}
    if lib is not None:
        e["material"] = propose_material(part_id, source_material, lib)
    return e


def component_entry(cid, part, transform, parent, parts, *, name=None, label=None, visible=True, suppressed=False,
                    source=None, occurrence=None):
    """occurrence: 1-based instance number of this part when the CAD source numbers instances
    (SolidWorks "<part>-3"); otherwise the order in the component list is used for matching."""
    e = {"id": cid, "name": name or cid.split("/")[-1], "parent": parent, "part": part,
         "transform": [r4(row) for row in transform], "visible": bool(visible), "suppressed": bool(suppressed),
         "source": source or {}}
    if label:
        e["label"] = label
    if occurrence:
        e["occurrence"] = int(occurrence)
    if part and part in parts:
        bb = parts[part]["bbox_mm"]
        lo, hi = world_bbox(transform, bb["min"], bb["max"])
        e["world_bbox_mm"] = [r4(lo), r4(hi)]
    return e


def finish(man):
    """Fill derived fields (overall bbox) and validate."""
    vis = [c for c in man["components"] if c.get("part") and c["visible"] and not c["suppressed"] and "world_bbox_mm" in c]
    if vis and not man.get("bbox_mm"):
        man["bbox_mm"] = union_bbox(c["world_bbox_mm"] for c in vis)
    problems = validate(man)
    if problems:
        raise ValueError("invalid product manifest:\n  " + "\n  ".join(problems))
    return man


def validate(man):
    """Structural checks of a schema-2.0 manifest. Returns a list of problems (empty = valid)."""
    p = []
    for k in ("schema_version", "assembly", "source", "units", "bbox_mm", "hierarchy", "parts", "components"):
        if k not in man or man[k] is None:
            p.append(f"missing {k}")
    if p:
        return p
    if man["units"] != {"length": "mm", "up_axis": "Z"}:
        p.append(f"units must be mm / Z-up, got {man['units']}")
    ids = [c["id"] for c in man["components"]]
    if len(ids) != len(set(ids)):
        p.append("component ids are not unique")
    nodes = {n["id"] for n in man["hierarchy"]}
    for c in man["components"]:
        if c.get("part") and c["part"] not in man["parts"]:
            p.append(f"component {c['id']} refers to unknown part {c['part']}")
        if c["parent"] not in nodes:
            p.append(f"component {c['id']} has unknown parent {c['parent']}")
        t = c.get("transform")
        if not (isinstance(t, list) and len(t) == 4 and all(len(r) == 4 for r in t)):
            p.append(f"component {c['id']} transform is not 4x4")
    for pid, part in man["parts"].items():
        g = part.get("geometry") or {}
        if not g.get("file") or g.get("format") not in set(FORMATS.values()):
            p.append(f"part {pid} geometry {g} (needs file and a known format)")
    if not any(c.get("part") for c in man["components"]):
        p.append("no component with geometry")
    return p


def upgrade(man):
    """Read an older manifest as schema 2.0 (in memory; the file is left as it is)."""
    if man.get("schema_version", "1.0").startswith("2."):
        return man
    man = json.loads(json.dumps(man))
    man["schema_version"] = SCHEMA_VERSION
    man["source"] = {"adapter": "solidworks", "application": "SOLIDWORKS", "application_version": "",
                     "file": man.pop("source_cad", ""), "exported": man.pop("exported", ""),
                     "details": {"step": man.get("step", {})}}
    step = man.pop("step", {}) or {}
    man["geometry"] = {"assembly": {"file": step["assembly"], "format": "step", "scale_to_m": None, "up_axis": "Z"}
                       if step.get("assembly") else None}
    for p in man.get("parts", {}).values():
        if p.get("step"):
            p["geometry"] = {"file": p.pop("step"), "format": "step", "scale_to_m": None, "up_axis": "Z"}
        p["source_material"] = p.pop("sw_material", "")
        p["source_path"] = p.pop("sw_path", "")
        app = p.pop("sw_appearance", None) or {}
        p["source_color"] = None if p.pop("sw_appearance_is_default", False) else rgb_hex(app.get("rgb"))
        if p.get("material", {}).get("source") == "solidworks_material":
            p["material"]["source"] = "cad_material"
    for c in man.get("components", []):
        c["source"] = {"sw_path": c.pop("sw_path", ""), "configuration": c.pop("configuration", "")}
    man.setdefault("validation", {"reference": "cad_kernel", "note": "bboxes measured by SolidWorks"})
    return man


def load(path):
    return upgrade(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


def save(man, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(man, indent=1), encoding="utf-8", newline="\n")
    return path


def rel(path, base):
    return str(pathlib.Path(path).resolve().relative_to(pathlib.Path(base).resolve())).replace("\\", "/")
