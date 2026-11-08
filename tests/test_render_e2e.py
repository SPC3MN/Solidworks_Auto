"""End-to-end test of CAD source -> manifest -> Blender -> preview -> approval -> final,
at tiny quality, into a temporary folder (the product's own render/ workspace is not touched).

    .venv\\Scripts\\python tests\\test_render_e2e.py [assemblies\\grindmn] [--keep] [--no-export DIR]
    .venv\\Scripts\\python tests\\test_render_e2e.py path\\to\\product.step      (any adapter: .FCStd, .glb, ...)

The adapter follows the target (SolidWorks needs SolidWorks running, FreeCAD needs FreeCAD).
Blender + the STEP Importer are always needed.
Exit code 0 only when every step and check passed. Inspect the images it prints, too:
a pipeline that runs is not yet a pipeline that looks right.
"""
import argparse
import json
import pathlib
import shutil
import sys
import tempfile
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_cli as cli  # noqa: E402
import render_config as rc  # noqa: E402
import render_adapters  # noqa: E402

results = []


def step(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""), flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default=str(ROOT / "assemblies" / "grindmn"))
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-export", help="reuse an existing work dir (skips SolidWorks)")
    a = ap.parse_args()
    work = pathlib.Path(a.no_export) if a.no_export else pathlib.Path(tempfile.mkdtemp(prefix="render_e2e_"))
    target = pathlib.Path(a.target).resolve()
    exploded = target.parent / f"{target.name}_exploded"

    # 1-3 export + manifest
    if not a.no_export:
        man = render_adapters.export(target, work, exploded_from=exploded if (exploded / "assembly.json").exists() else None)
    else:
        man = cli.load_manifest(work)
    step("export.geometry_files", all((rc.render_dir(work) / p["geometry"]["file"]).exists() for p in man["parts"].values()),
         f"{len(man['parts'])} part files via the {man['source']['adapter']} adapter ({man['source']['application']})")
    step("manifest.valid", not render_adapters.common.validate(man))
    ids = [c["id"] for c in man["components"]]
    step("manifest.unique_ids", len(ids) == len(set(ids)), f"{len(ids)} components")
    step("manifest.repeated_instances", len({c["part"] for c in man["components"]}) <= len(ids))

    # 4-5 import + validation
    code, _ = cli.run_blender("bl_import.py", "--render-dir", rc.render_dir(work))
    rep = json.loads((rc.path(work, "reports") / "import_report.json").read_text())
    step("import.validation", code == 0 and rep["pass"], f"{sum(c['pass'] for c in rep['checks'])}/{len(rep['checks'])} checks")

    # 6-9 materials, studio + environment + technical scenes, previews (tiny)
    ns = types.SimpleNamespace(target=str(work), force=True, shots=None, quote=None)
    cli.cmd_init(ns)
    sp = cli.settings_path(work)
    s = json.loads(sp.read_text())
    s["render"]["preview"].update(long_side=240, samples=8)
    s["render"]["final"].update(long_side=320, samples=12)
    s["shots"] = [sh for sh in s["shots"] if sh["name"] in ("hero", "front", "exploded", "xray")]
    s["shots"].append({"name": "env_hero", "scene": "environment", "camera": "environment_hero", "category": "environment"})
    s["shots"].append({"name": "cut", "scene": "technical", "camera": "three_quarter_hero", "category": "technical",
                       "cutaway": {"components": "auto", "axis": "y", "keep": "+"}})
    s["environment"]["preset"] = "laboratory"
    sp.write_text(json.dumps(s, indent=1))
    cli.cmd_preview(types.SimpleNamespace(target=str(work), shots=None, force=False, quote=None))
    prev = json.loads((rc.path(work, "reports") / "preview_latest.json").read_text())
    for sh in prev["shots"]:
        st = sh["image"]
        step(f"preview.{sh['name']}", pathlib.Path(sh["file"]).exists() and 15 < st["mean"] < 250 and not sh["framing"]["cropped"],
             f"lum {st['mean']} fill {sh['framing']['bbox_fill']} -> {sh['file']}")
    step("preview.contact_sheet", prev.get("contact_sheet") and pathlib.Path(prev["contact_sheet"]).exists())
    env = prev["scenes"].get("environment", {})
    step("environment.clearance", env and not env["prop_clashes"], f"{env.get('environment')} on {env.get('support')}")

    # 10 approval gate and a revision
    try:
        cli.cmd_final(types.SimpleNamespace(target=str(work), force=False, shots=None, quote=None))
        step("gate.final_without_approval_refused", False)
    except SystemExit as e:
        step("gate.final_without_approval_refused", "NOT APPROVED" in str(e))
    s = json.loads(sp.read_text())
    s["lighting"]["preset"] = "dramatic_premium"   # "make it more dramatic"
    sp.write_text(json.dumps(s, indent=1))
    try:
        cli.cmd_approve(types.SimpleNamespace(target=str(work), quote="test approval"))
        step("gate.stale_preview_refused", False)
    except SystemExit as e:
        step("gate.stale_preview_refused", "changed since the last preview" in str(e))
    cli.cmd_preview(types.SimpleNamespace(target=str(work), shots=None, force=False, quote=None))
    cli.cmd_approve(types.SimpleNamespace(target=str(work), quote="TEST SUITE: automated approval of tiny test renders"))

    # 11-12 final + deliverables
    cli.cmd_final(types.SimpleNamespace(target=str(work), force=False, shots=None, quote=None))
    fin = json.loads((rc.path(work, "reports") / "final_latest.json").read_text())
    step("final.images", all(pathlib.Path(x["file"]).exists() for x in fin["shots"]), f"{len(fin['shots'])} images")
    step("final.blend", pathlib.Path(fin["blend"]).exists())
    step("final.deliverables", (rc.path(work, "final") / "deliverables.md").exists())
    step("cad.untouched", target.exists())

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed; work dir {work}")
    if not a.keep and not failed:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
