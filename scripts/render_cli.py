"""Photorealistic rendering of a SolidWorks product with Blender Cycles: one entry point.

    .venv\\Scripts\\python scripts\\render_cli.py hw
    .venv\\Scripts\\python scripts\\render_cli.py export   assemblies\\grindmn [--exploded-from assemblies\\grindmn_exploded]
    .venv\\Scripts\\python scripts\\render_cli.py import   assemblies\\grindmn
    .venv\\Scripts\\python scripts\\render_cli.py init     assemblies\\grindmn [--force]
    .venv\\Scripts\\python scripts\\render_cli.py preview  assemblies\\grindmn [--shots hero,env_hero]
    .venv\\Scripts\\python scripts\\render_cli.py approve  assemblies\\grindmn --quote "<the user's approval, verbatim>"
    .venv\\Scripts\\python scripts\\render_cli.py final    assemblies\\grindmn
    .venv\\Scripts\\python scripts\\render_cli.py status   assemblies\\grindmn

The approval gate: `final` renders only when settings/approval.json holds the hash of the
current settings/scene.json AND that exact scene was previewed. Any edit to scene.json
after approval invalidates it, so the user always approves what is rendered. Run
`approve` only after the user has explicitly approved the previews in chat.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import render_config as rc  # noqa: E402

CATEGORIES = ("studio", "environment", "details", "exploded", "technical")


# ---------------------------------------------------------------- helpers

def blender():
    exe = rc.blender_exe()
    if exe is None:
        sys.exit("Blender not found. Set BLENDER_EXE or config/render.local.json (see docs/rendering.md).")
    return exe


def run_blender(script, *args, timeout=None):
    cmd = [str(blender()), "-b", "-noaudio", "--python-exit-code", "1", "--python", str(rc.BLENDER_SCRIPTS / script), "--", *map(str, args)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    keep = []
    for line in proc.stdout:
        if line.startswith("[render]") or "Error" in line or "Traceback" in line or line.startswith("  File") or keep and keep[-1].startswith("  File"):
            print(line.rstrip(), flush=True)
        keep.append(line)
    proc.wait(timeout=timeout)
    return proc.returncode, "".join(keep)


def folder_of(target):
    f = pathlib.Path(target).resolve()
    return f.parent if f.is_file() else f


def settings_path(folder):
    return rc.path(folder, "settings") / "scene.json"


def settings_hash(folder):
    data = json.loads(settings_path(folder).read_text(encoding="utf-8"))

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    # the libraries are part of what the user approves: a preset edit changes the hash too
    libs = {n: strip(json.loads((rc.LIB / f"{n}.json").read_text(encoding="utf-8")))
            for n in ("materials", "lighting", "cameras")}
    return hashlib.sha256(json.dumps([strip(data), libs], sort_keys=True).encode()).hexdigest()[:16]


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def save(p, data):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- commands

def cmd_hw(_a):
    import os
    import platform
    print(f"OS: {platform.platform()}  CPU: {platform.processor()}  logical cores: {os.cpu_count()}")
    exe = blender()
    out = subprocess.run([str(exe), "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    print(f"Blender: {out} ({exe})")
    run_blender("bl_scene.py", "--render-dir", ".", "--hw-only")


def cmd_export(a):
    import render_export
    render_export.run(a.target, None, a.exploded_from, a.explode_axis, a.ap242)


def cmd_import(a):
    folder = folder_of(a.target)
    args = ["--render-dir", rc.render_dir(folder)]
    if a.tol_linear:
        args += ["--tol-linear", a.tol_linear]
    if a.tol_angular:
        args += ["--tol-angular", a.tol_angular]
    code, _ = run_blender("bl_import.py", *args)
    if code:
        sys.exit("import failed validation: see render/reports/import_report.json")


def default_settings(man):
    n = len([c for c in man["components"] if c.get("part")])
    shots = [
        {"name": "hero", "scene": "studio", "camera": "three_quarter_hero", "category": "studio"},
        {"name": "low_angle", "scene": "studio", "camera": "low_angle_hero", "category": "studio"},
        {"name": "front", "scene": "studio", "camera": "front_ortho", "category": "studio"},
        {"name": "side", "scene": "studio", "camera": "side_ortho", "category": "studio"},
        {"name": "top", "scene": "studio", "camera": "top_ortho", "category": "studio"},
        {"name": "detail", "scene": "studio", "camera": "detail_closeup", "category": "details"},
    ]  # environment shots are opt-in: add {"name": "env_hero", "scene": "environment", "camera": "environment_hero"}
    sz = man["bbox_mm"]["size"]
    if sz[2] > 1.4 * max(sz[0], sz[1]):  # tall product: portrait hero shots fill the frame better
        for s in shots:
            if s["name"] in ("hero", "low_angle"):
                s["aspect"] = "4:5"
    if n > 1:
        shots += [
            {"name": "exploded", "scene": "technical", "camera": "exploded_hero", "category": "exploded", "exploded": True},
            {"name": "xray", "scene": "technical", "camera": "three_quarter_hero", "category": "technical", "xray": "auto"},
        ]
    low = sorted({p for p, v in man["parts"].items() if v["material"].get("confidence") == "low"})
    return {
        "schema_version": "1.0",
        "_comment": "Scene state for render_cli.py. Edit this to change the look; previews and the approval follow it. Keys starting with _ are notes and do not affect the approval hash.",
        "lighting": {"preset": "soft_commercial", "intensity": 1.0, "softness": 1.0, "fill_ratio": 1.0,
                     "warmth_kelvin": 0, "rotate": 0, "exposure": 0.0},
        "studio": {"background": {}, "floor": {}},
        "environment": {"preset": "workshop", "intensity": 1.0, "exposure": 0.0},
        "technical": {"lighting": {"preset": "neutral_technical"}, "explode_scale": 1.0},
        "materials": {"_review": low, "_how": "parts: {part_id: {material, finish, color, roughness}}; components: {sw_id or label: {...}} wins over parts",
                      "parts": {}, "components": {}},
        "shots": shots,
        "render": {
            "preview": {"long_side": 800, "samples": 48, "noise_threshold": 0.03, "denoise": True, "format": "PNG"},
            "final": {"long_side": 2400, "samples": 256, "noise_threshold": 0.01, "denoise": True, "format": "PNG", "color_depth": "16"},
        },
    }


def cmd_init(a):
    folder = folder_of(a.target)
    man = load(rc.path(folder, "manifest"))
    p = settings_path(folder)
    if p.exists() and not a.force:
        print(f"{p} exists: kept (it holds the user's choices). Use --force to reset.")
        return
    save(p, default_settings(man))
    print(f"wrote {p}")


def image_stats(png):
    from PIL import Image, ImageStat
    im = Image.open(png).convert("RGB")
    im.thumbnail((400, 400))
    g = im.convert("L")
    hist = g.histogram()
    n = sum(hist)
    return {"mean": round(ImageStat.Stat(g).mean[0], 1), "clipped_pct": round(100 * sum(hist[250:]) / n, 2),
            "crushed_pct": round(100 * sum(hist[:6]) / n, 2)}


def contact_sheet(shots, out, title):
    from PIL import Image, ImageDraw, ImageFont
    imgs = [(s, Image.open(s["file"]).convert("RGB")) for s in shots if pathlib.Path(s["file"]).exists()]
    if not imgs:
        return None
    cell, pad, lab = 420, 12, 46
    cols = min(3, len(imgs))
    rows = -(-len(imgs) // cols)
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (cell + lab + pad) + pad + 40), (30, 31, 34))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("segoeui.ttf", 16)
        small = ImageFont.truetype("segoeui.ttf", 13)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((pad, 10), title, fill=(235, 235, 235), font=font)
    for i, (s, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        im.thumbnail((cell, cell))
        x, y = pad + c * (cell + pad), 40 + pad + r * (cell + lab + pad)
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        cam = s["camera"]
        lens = "ortho" if cam.get("type") == "ORTHO" else f"{cam.get('focal_mm')} mm"
        d.text((x, y + cell + 4), f"{s['name']}  ({s['scene']}{', exploded' if s['exploded'] else ''})", fill=(235, 235, 235), font=font)
        d.text((x, y + cell + 24), f"{lens}  az {cam.get('az')}  el {cam.get('el')}  {s['resolution'][0]}x{s['resolution'][1]}  {s['seconds']} s",
               fill=(170, 170, 170), font=small)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def ensure_import(folder):
    man_p = rc.path(folder, "manifest")
    man = load(man_p)
    cad = rc.path(folder, "blender") / f"{man['assembly']}_cad.blend"
    rep = rc.path(folder, "reports") / "import_report.json"
    if not cad.exists() or not rep.exists() or cad.stat().st_mtime < man_p.stat().st_mtime or not load(rep)["pass"]:
        print("CAD import missing or older than the manifest: importing")
        code, _ = run_blender("bl_import.py", "--render-dir", rc.render_dir(folder))
        if code:
            sys.exit("import failed validation: see render/reports/import_report.json")
    return man


def newest_report(folder, quality):
    reps = sorted(p for p in rc.path(folder, "reports").glob(f"{quality}_2*.json"))
    if not reps:
        sys.exit(f"no {quality} report written")
    return load(reps[-1])


def summarize(folder, rep, quality):
    print(f"\n== {quality} summary ==")
    print(f"device: {rep['device']}")
    sc = rep["scenes"]
    if "studio" in sc:
        print(f"studio: lighting {sc['studio']['lighting']}, background {sc['studio']['background']}, floor {sc['studio']['floor'].get('type')}")
    if "environment" in sc:
        print(f"environment: {sc['environment']['environment']} on {sc['environment']['support']}; clashes {sc['environment']['prop_clashes'] or 'none'}")
    if "technical" in sc:
        print(f"technical: lighting {sc['technical']['lighting']}, explode offsets from {sc['technical'].get('explode_method')}")
    print("materials (part -> material [source, confidence]):")
    seen = {}
    for m in rep["materials"]:
        seen.setdefault(m["part"], m)
    for part, m in sorted(seen.items()):
        fin = f" / {m['finish']}" if m.get("finish") else ""
        print(f"  {part:28} {m['material']}{fin}  [{m['source']}, {m['confidence']}]")
    print("shots:")
    for s in rep["shots"]:
        st = s.get("image", {})
        print(f"  {s['name']:10} {s['scene']:11} {s['camera'].get('type')} {s['camera'].get('focal_mm') or ''} az {s['camera'].get('az')} el {s['camera'].get('el')}"
              f"  fill {s['framing']['bbox_fill']}{' CROPPED' if s['framing']['cropped'] else ''}  {s['seconds']} s  "
              f"lum {st.get('mean')} clip {st.get('clipped_pct')}% crush {st.get('crushed_pct')}%")
    for c in rep["checks"]:
        if not c["pass"] or c.get("warn"):
            print("  CHECK", "FAIL" if not c["pass"] else "WARN", c)


def estimate_final(folder, prev):
    st = load(settings_path(folder))
    pq, fq = st["render"]["preview"], st["render"]["final"]
    total = 0.0
    for s in prev["shots"]:
        px = (fq["long_side"] / pq["long_side"]) ** 2
        total += s["seconds"] * px * (fq["samples"] / pq["samples"]) * 0.6
    return total


def only_shots_removed(folder, prev):
    """True when the current settings equal the last previewed ones except for shots that were
    deleted: the remaining previews are then still exactly what would render."""
    snap = rc.path(folder, "settings") / "history" / f"{prev.get('time')}_preview.json"
    if not snap.exists():
        return False
    old, cur = load(snap), load(settings_path(folder))
    old_shots, cur_shots = old.pop("shots", []), cur.pop("shots", [])
    strip = lambda d: json.dumps({k: v for k, v in d.items() if not k.startswith("_")}, sort_keys=True)
    return strip(old) == strip(cur) and all(s in old_shots for s in cur_shots) and len(cur_shots) < len(old_shots)


def cmd_preview(a):
    folder = folder_of(a.target)
    ensure_import(folder)
    if not settings_path(folder).exists():
        cmd_init(a)
    h = settings_hash(folder)
    rp0 = rc.path(folder, "reports") / "preview_latest.json"
    if not a.shots and rp0.exists():
        prev = load(rp0)
        if prev.get("settings_hash") != h and only_shots_removed(folder, prev):
            keep = {s["name"] for s in load(settings_path(folder))["shots"]}
            prev["shots"] = [s for s in prev["shots"] if s["name"] in keep]
            prev["settings_hash"], prev["partial"] = h, False
            for sc in list(prev.get("scenes", {})):
                if sc != "studio" and not any(x["scene"] == sc for x in prev["shots"]):
                    prev["scenes"].pop(sc)
            prev["note"] = "shots removed only: existing previews carried over, nothing re-rendered"
            sheet = contact_sheet(prev["shots"], rc.path(folder, "previews") / "contact_sheet.png",
                                  f"{load(rc.path(folder, 'manifest'))['assembly']} previews  ({prev['time']}, settings {h})")
            prev["contact_sheet"] = str(sheet) if sheet else None
            prev["final_estimate_s"] = round(estimate_final(folder, prev))
            save(rp0, prev)
            shutil.copy2(settings_path(folder), rc.path(folder, "settings") / "history" / f"{prev['time']}_preview.json")
            summarize(folder, prev, "preview")
            print("\n" + prev["note"])
            print(f"contact sheet: {sheet}")
            print(f"settings hash {h}")
            return
    args = ["--render-dir", rc.render_dir(folder), "--quality", "preview", "--settings-hash", h]
    if a.shots:
        args += ["--shots", a.shots]
    code, _ = run_blender("bl_scene.py", *args)
    if code:
        sys.exit("preview render failed (see output above)")
    rp = rc.path(folder, "reports") / "preview_latest.json"
    prev = load(rp) if rp.exists() else None
    rep = newest_report(folder, "preview")
    for s in rep["shots"]:
        s["image"] = image_stats(s["file"])
    # a partial preview of the same settings joins the shots already previewed with them
    if a.shots and prev and prev.get("settings_hash") == h:
        done = {s["name"] for s in rep["shots"]}
        order = [s["name"] for s in load(settings_path(folder))["shots"]]
        rep["shots"] = sorted(rep["shots"] + [s for s in prev["shots"] if s["name"] not in done],
                              key=lambda s: order.index(s["name"]) if s["name"] in order else 99)
        if s["image"]["clipped_pct"] > 8 and s["scene"] != "studio":
            rep["checks"].append({"id": f"exposure.{s['name']}", "pass": True, "warn": True, "note": "large clipped area"})
    sheet = contact_sheet(rep["shots"], rc.path(folder, "previews") / "contact_sheet.png",
                          f"{load(rc.path(folder, 'manifest'))['assembly']} previews  ({rep['time']}, settings {h})")
    rep["contact_sheet"] = str(sheet) if sheet else None
    want = {s["name"] for s in load(settings_path(folder))["shots"]}
    rep["partial"] = not want <= {s["name"] for s in rep["shots"]}
    rep["final_estimate_s"] = round(estimate_final(folder, rep))
    save(rp, rep)
    save(rc.path(folder, "reports") / f"preview_{rep['time']}.json", rep)
    hist = rc.path(folder, "settings") / "history" / f"{rep['time']}_preview.json"
    hist.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(settings_path(folder), hist)
    summarize(folder, rep, "preview")
    st = load(settings_path(folder))
    fq = st["render"]["final"]
    print(f"\ncontact sheet: {sheet}")
    print(f"proposed final: {len(st['shots'])} shots, long side {fq['long_side']} px, {fq['samples']} samples, {fq['format']}"
          f" -> about {rep['final_estimate_s'] / 60:.0f} min on {rep['device']['device']}")
    print(f"settings hash {h}: approve with  render_cli.py approve {a.target} --quote \"...\"  after the user says so.")


def cmd_approve(a):
    folder = folder_of(a.target)
    if not a.quote or len(a.quote.strip()) < 2:
        sys.exit("--quote with the user's approval, verbatim, is required")
    h = settings_hash(folder)
    rp = rc.path(folder, "reports") / "preview_latest.json"
    if not rp.exists():
        sys.exit("no preview yet: run preview first")
    rep = load(rp)
    if rep.get("settings_hash") != h:
        sys.exit(f"scene.json changed since the last preview ({rep.get('settings_hash')} -> {h}): preview again, then ask the user")
    if rep.get("partial"):
        names = {s["name"] for s in rep["shots"]}
        missing = [s["name"] for s in load(settings_path(folder))["shots"] if s["name"] not in names]
        if missing:
            sys.exit(f"no preview of the current settings for {missing}: preview them before approval")
    save(rc.path(folder, "settings") / "approval.json",
         {"settings_hash": h, "approved_at": dt.datetime.now().isoformat(timespec="seconds"), "quote": a.quote,
          "preview_report": str(rp), "shots": [s["name"] for s in rep["shots"]]})
    print(f"approved settings {h}")


def cmd_final(a):
    folder = folder_of(a.target)
    ap = rc.path(folder, "settings") / "approval.json"
    h = settings_hash(folder)
    if not ap.exists():
        sys.exit("NOT APPROVED: show the previews to the user and get explicit approval first (render_cli.py approve).")
    appr = load(ap)
    if appr["settings_hash"] != h:
        sys.exit(f"NOT APPROVED: scene.json changed after approval ({appr['settings_hash']} -> {h}). Preview and ask again.")
    man = ensure_import(folder)
    code, _ = run_blender("bl_scene.py", "--render-dir", rc.render_dir(folder), "--quality", "final", "--settings-hash", h)
    if code:
        sys.exit("final render failed (see output above)")
    rep = newest_report(folder, "final")
    for s in rep["shots"]:
        s["image"] = image_stats(s["file"])
    sheet = contact_sheet(rep["shots"], rc.path(folder, "final") / "contact_sheet.png",
                          f"{man['assembly']} final renders ({rep['time']})")
    shutil.copy2(settings_path(folder), rc.path(folder, "settings") / f"final_{rep['time']}.json")
    save(rc.path(folder, "reports") / "final_latest.json", rep)
    lines = [f"# {man['assembly']}: final renders", "",
             f"- Rendered {rep['time']} on {rep['device']['device']} with Blender Cycles; settings {h}, approved {appr['approved_at']} (\"{appr['quote']}\").",
             f"- Scene file: `{pathlib.Path(rep['blend']).relative_to(folder)}` (CAD import: `blender/{man['assembly']}_cad.blend`).",
             f"- Settings: `render/settings/final_{rep['time']}.json`; source CAD `{man['source_cad']}` (unchanged).",
             f"- Materials are rendering presets (Principled BSDF), not measured physical data.", "",
             "| Shot | Scene | File | Size | Time |", "|---|---|---|---|---|"]
    for s in rep["shots"]:
        lines.append(f"| {s['name']} | {s['scene']} | `{pathlib.Path(s['file']).relative_to(folder)}` | {s['resolution'][0]}x{s['resolution'][1]} | {s['seconds']} s |")
    (rc.path(folder, "final") / "deliverables.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    summarize(folder, rep, "final")
    print(f"\ndeliverables: {rc.path(folder, 'final') / 'deliverables.md'}\ncontact sheet: {sheet}")


def cmd_status(a):
    folder = folder_of(a.target)
    mp = rc.path(folder, "manifest")
    print("manifest:", mp if mp.exists() else "missing (run export)")
    ip = rc.path(folder, "reports") / "import_report.json"
    if ip.exists():
        print("import:", "PASS" if load(ip)["pass"] else "FAIL")
    if settings_path(folder).exists():
        h = settings_hash(folder)
        print("settings hash:", h)
        pp = rc.path(folder, "reports") / "preview_latest.json"
        if pp.exists():
            ph = load(pp).get("settings_hash")
            print("last preview:", load(pp)["time"], "matches settings" if ph == h else f"STALE ({ph})")
        ap = rc.path(folder, "settings") / "approval.json"
        if ap.exists():
            ah = load(ap)["settings_hash"]
            print("approval:", load(ap)["approved_at"], "valid" if ah == h else f"INVALID (approved {ah})")
        else:
            print("approval: none")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hw")
    p = sub.add_parser("export")
    p.add_argument("target")
    p.add_argument("--exploded-from")
    p.add_argument("--explode-axis", default="z", choices="xyz")
    p.add_argument("--ap242", action="store_true")
    p = sub.add_parser("import")
    p.add_argument("target")
    p.add_argument("--tol-linear")
    p.add_argument("--tol-angular")
    for name in ("init", "preview", "approve", "final", "status"):
        p = sub.add_parser(name)
        p.add_argument("target")
        p.add_argument("--force", action="store_true")
        p.add_argument("--shots")
        p.add_argument("--quote")
    a = ap.parse_args()
    {"hw": cmd_hw, "export": cmd_export, "import": cmd_import, "init": cmd_init, "preview": cmd_preview,
     "approve": cmd_approve, "final": cmd_final, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
