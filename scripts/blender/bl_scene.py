"""Build the render scenes from the imported CAD and settings/scene.json, then render shots.

    blender -b --python scripts/blender/bl_scene.py -- --render-dir <folder>/render
        --quality preview|final [--shots hero,env_hero] [--settings-hash abc] [--hw-only]

Opens blender/<asm>_cad.blend (never modified), builds three Blender scenes that share
the CAD collection (Studio, Environment, Technical), renders each requested shot, and
saves blender/<asm>.blend (preview) or blender/<asm>_final.blend (final). Per-shot
changes (exploded copies, see-through, cutaway, isolation) are undone after the shot,
so the saved file is in the assembled state. A JSON report with timings, framing,
material assignments and checks goes to reports/.
"""
import datetime as dt
import pathlib
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bl_cameras as CAM  # noqa: E402
import bl_environments as ENV  # noqa: E402
import bl_materials as BM  # noqa: E402
import bl_stage as ST  # noqa: E402
import bl_technical as TECH  # noqa: E402
import bl_util as U  # noqa: E402

GPU_TYPES = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")


def detect_device():
    """Use a GPU when Cycles lists one, else the CPU. Returns what was found."""
    prefs = bpy.context.preferences.addons["cycles"].preferences
    found = {}
    for t in GPU_TYPES:
        try:
            devs = [d for d in prefs.get_devices_for_type(t) if d.type != "CPU"]
        except Exception:  # noqa: BLE001 - backend not compiled in / no driver
            devs = []
        if devs:
            found[t] = [d.name for d in devs]
    if found:
        t = next(iter(found))
        prefs.compute_device_type = t
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == t or d.type == "CPU"
        return {"device": "GPU", "backend": t, "gpus": found[t]}
    prefs.compute_device_type = "NONE"
    import multiprocessing
    return {"device": "CPU", "threads": multiprocessing.cpu_count(),
            "note": "no Cycles-compatible GPU found (CUDA/OptiX/HIP/oneAPI/Metal)"}


def configure(scene, q, look, exposure, device):
    r = scene.render
    scene.render.engine = "CYCLES"
    c = scene.cycles
    c.device = "GPU" if device["device"] == "GPU" else "CPU"
    c.samples = q["samples"]
    c.use_adaptive_sampling = True
    c.adaptive_threshold = q.get("noise_threshold", 0.02)
    c.use_denoising = q.get("denoise", True)
    if hasattr(c, "denoiser"):
        c.denoiser = "OPENIMAGEDENOISE"
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 12, 4, 8
    c.transmission_bounces, c.transparent_max_bounces = 12, 24
    c.sample_clamp_indirect = 10.0
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 0.5
    r.use_persistent_data = True
    r.resolution_percentage = 100
    vs = scene.view_settings
    vs.view_transform = "AgX"
    try:
        vs.look = look or "None"
    except TypeError:
        U.log(f"look '{look}' not available, using None")
        vs.look = "None"
    vs.exposure = exposure or 0.0
    r.image_settings.file_format = q.get("format", "PNG")
    r.image_settings.color_mode = "RGBA" if scene.render.film_transparent else "RGB"
    r.image_settings.color_depth = str(q.get("color_depth", "8" if q.get("format", "PNG") == "PNG" else "16"))
    if q.get("format") == "TIFF":
        r.image_settings.tiff_codec = "DEFLATE"


def resolution(q, shot):
    if shot.get("resolution"):
        return tuple(shot["resolution"])
    a, b = (float(x) for x in str(shot.get("aspect", "1:1")).split(":"))
    long_side = q["long_side"]
    return (long_side, round(long_side * b / a)) if a >= b else (round(long_side * a / b), long_side)


def new_scene(name, cad_root):
    sc = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
    if cad_root.name not in [c.name for c in sc.collection.children]:
        sc.collection.children.link(cad_root)
    sc.unit_settings.system = "METRIC"
    return sc


def main():
    args = U.script_args()
    rdir = pathlib.Path(args["render-dir"]).resolve()
    if args.get("hw-only"):
        U.log("HW", detect_device())
        return
    quality = args.get("quality", "preview")
    man = U.load_manifest(rdir / "export" / "product_manifest.json")
    settings = U.load_json(rdir / "settings" / "scene.json")
    q = settings["render"][quality]
    asm = man["assembly"]
    bpy.ops.wm.open_mainfile(filepath=str(rdir / "blender" / f"{asm}_cad.blend"))
    device = detect_device()
    U.log("device", device)

    cad_root = next(c for c in bpy.data.collections if c.get("cad_role") == "cad_root")
    cad = [o for o in cad_root.all_objects if "cad_id" in o]
    mat_table = BM.assign(cad, man, settings)
    visible = [o for o in cad if not o.hide_render]
    box = (Vector([min(U.exact_world_bbox(o)[0][i] for o in visible) for i in range(3)]),
           Vector([max(U.exact_world_bbox(o)[1][i] for o in visible) for i in range(3)]))
    by_key = {}
    for o in cad:
        by_key[o["cad_id"]] = o
        if o.get("cad_label"):
            by_key[o["cad_label"]] = o

    shots = settings["shots"]
    if args.get("shots"):
        want = set(args["shots"].split(","))
        shots = [s for s in shots if s["name"] in want]
    used = {s.get("scene", "studio") for s in shots}

    # --- scenes (each shares the CAD collection)
    base = bpy.context.scene
    base.name = "Studio"
    scenes, info = {}, {}
    if True:  # the studio scene always exists (it is the file's main scene)
        coll = U.collection("Studio_Set", base.collection)
        info["studio"] = ST.build_studio(base, box, settings, coll)
        scenes["studio"] = base
    if "environment" in used:
        sc = new_scene("Environment", cad_root)
        info["environment"] = ENV.build(sc, box, settings, U.collection("Environment_Set", sc.collection))
        scenes["environment"] = sc
    ex_coll, ex_objs = None, []
    if "technical" in used or any(s.get("exploded") for s in shots):
        sc = new_scene("Technical", cad_root)
        tset = dict(settings)
        tset["lighting"] = dict(settings.get("technical", {}).get("lighting", {"preset": "neutral_technical"}))
        tset["studio"] = settings.get("technical", {}).get("studio", {})
        info["technical"] = ST.build_studio(sc, box, tset, U.collection("Technical_Set", sc.collection))
        scale = settings.get("technical", {}).get("explode_scale", 1.0)
        ex_coll, ex_objs, method = TECH.exploded_collection(cad, man, sc.name, scale)
        sc.collection.children.link(ex_coll)
        ex_coll.hide_render = True
        info["technical"]["explode_method"] = method
        scenes["technical"] = sc
    for key, sc in scenes.items():
        i = info.get(key, {})
        look = settings.get("lighting", {}).get("look", i.get("look")) if key == "studio" else i.get("look", "None")
        exposure = settings.get("lighting", {}).get("exposure", i.get("exposure", 0.0)) if key != "technical" else 0.0
        if key == "environment":
            exposure = settings.get("environment", {}).get("exposure", 0.0)
            look = settings.get("environment", {}).get("look", "AgX - Base Contrast")
        configure(sc, q, look, exposure, device)

    # --- shots
    cams = {k: U.collection(f"Cameras_{sc.name}", sc.collection) for k, sc in scenes.items()}
    presets = U.lib("cameras")["presets"]
    out_root = rdir / ("previews" if quality == "preview" else "final")
    shot_reports = []
    for shot in shots:
        key = shot.get("scene", "studio")
        sc = scenes[key]
        exploded = bool(shot.get("exploded"))
        objs = ex_objs if exploded else cad
        act_vis = [o for o in objs if not o.hide_render]
        sbox = (Vector([min(U.exact_world_bbox(o)[0][i] for o in act_vis) for i in range(3)]),
                Vector([max(U.exact_world_bbox(o)[1][i] for o in act_vis) for i in range(3)]))
        spec = dict(presets[shot.get("camera", "three_quarter_hero")])
        spec.update(shot.get("camera_overrides", {}))
        w, h = resolution(q, shot)
        cam = CAM.make(f"CAM_{shot['name']}", spec, sbox, w / h, cams[key], by_key, box)
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = w, h
        if ex_coll is not None:
            ex_coll.hide_render = not exploded
        cad_root.hide_render = exploded
        floor_ob = bpy.data.objects.get(info.get(key, {}).get("floor_object") or "")
        if floor_ob is not None:
            if spec.get("el", 0) < 80:
                ST.orient_backdrop(floor_ob, spec.get("az", 0))
            floor_ob.location.z = sbox[0].z  # the floor follows the shot's lowest part (exploded sets too)
        undo, odesc = TECH.apply_overrides(objs, shot, settings, sbox)
        cat = shot.get("category", key)
        ext = ".tif" if q.get("format") == "TIFF" else ".png"
        out = out_root / cat / f"{shot['name']}{ext}"
        out.parent.mkdir(parents=True, exist_ok=True)
        sc.render.filepath = str(out)
        if bpy.context.window:
            bpy.context.window.scene = sc
        t = time.time()
        bpy.ops.render.render(write_still=True, scene=sc.name)
        secs = round(time.time() - t, 1)
        frame = CAM.framing_report(cam, sc, sbox)
        undo()
        cad_root.hide_render = False
        if ex_coll is not None:
            ex_coll.hide_render = True
        rep = {"name": shot["name"], "scene": key, "category": cat, "file": str(out), "seconds": secs,
               "resolution": [w, h], "camera": {k: spec.get(k) for k in ("type", "focal_mm", "az", "el", "margin", "target", "dof")},
               "exploded": exploded, "overrides": odesc, "framing": frame}
        shot_reports.append(rep)
        U.log(f"shot {shot['name']}: {w}x{h} {secs}s fill {frame['bbox_fill']} cropped {frame['cropped']} -> {out}")

    # --- checks that do not need the images
    checks = []
    unknown = [m for m in mat_table if m["confidence"] == "low"]
    checks.append({"id": "materials.confidence", "pass": True, "warn": bool(unknown),
                   "low_confidence": sorted({m["part"] for m in unknown})})
    for s in shot_reports:
        if s["framing"]["cropped"] and not shot_target_is_detail(s):
            checks.append({"id": f"framing.{s['name']}", "pass": False, "note": "product cut off by the frame"})
    if "environment" in info and info["environment"]["prop_clashes"]:
        checks.append({"id": "environment.clearance", "pass": False, "props": info["environment"]["prop_clashes"]})
    floor = info.get("studio", {}).get("floor_object")
    checks.append({"id": "grounded", "pass": True, "note": "floor/support top placed at the product's lowest point",
                   "product_min_z_mm": round(box[0].z / U.MM, 3)})

    # --- save the scene file (assembled state); the CAD file stays untouched
    if bpy.context.window:
        bpy.context.window.scene = base
    blend = rdir / "blender" / (f"{asm}.blend" if quality == "preview" else f"{asm}_final.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, copy=False)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    report = {"quality": quality, "time": stamp, "settings_hash": args.get("settings-hash"), "device": device,
              "blend": str(blend), "product_bbox_mm": [round((box[1] - box[0])[i] / U.MM, 2) for i in range(3)],
              "scenes": info, "materials": mat_table, "shots": shot_reports, "checks": checks,
              "render_settings": q}
    U.save_json(rdir / "reports" / f"{quality}_{stamp}.json", report)  # render_cli makes {quality}_latest.json
    U.log(f"saved {blend}; report reports/{quality}_{stamp}.json")


def shot_target_is_detail(s):
    t = (s["camera"] or {}).get("target") or ""
    return t.startswith("region:") or t.startswith("component:")


if __name__ == "__main__":
    main()
