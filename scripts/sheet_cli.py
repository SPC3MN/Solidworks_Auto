"""Hand-folded sheet parts: definition -> flat pattern (DXF) + folded model (STEP) + validation.

    python3 scripts/sheet_cli.py template tray projects/<name> --length 120 --width 80 --height 30 [--flange 10] [--dims inside]
    python3 scripts/sheet_cli.py check    projects/<name>            # host-only checks, no FreeCAD
    python3 scripts/sheet_cli.py build    projects/<name>            # everything
    python3 scripts/sheet_cli.py coupons  <out dir> --slot-lengths 4,8,12 --bridges 1,1.5,2 [--slot-width 0.5]
    python3 scripts/sheet_cli.py record   <out dir>/coupons.json --id 05 --result held --angle 90 --leg-a 30.4 --leg-b 30.5

`build` reads <folder>/sheet.json (scripts/sheet_lib.py) and writes, in that folder:
  flat/<name>[_UNTESTED].dxf   layers CUT_THROUGH, FOLD_PERFORATION, FOLD_DIRECTION, REFERENCE (mm), read back and compared
  flat/<name>.svg              the flat pattern to look at
  folded/<name>.step           rigid panels turned about their folds; <name>.FCStd in the spec's tree
  renders/                     folded views, and one view after each folding step
  report.json, validation/history/<stamp>_<verdict>.json

The report gives three separate verdicts: geometrically valid, manufacturable (against the named
manufacturing profile) and experimentally validated (every fold's recipe matches a coupon that
held, in the material profile). A fold with no such coupon marks every output UNTESTED; it does
not stop the build. `build` exits 1 only when the geometric or the manufacturable verdict fails.

A part of a product (products/<name>/parts/<part>) is built only from its approved draft.
"""
import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import draft_lib as D  # noqa: E402
import dxf_io  # noqa: E402
import fold_patterns as FP  # noqa: E402
import sheet_draw  # noqa: E402
import sheet_lib as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def save(p, data):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def load(folder):
    try:
        return S.load_sheet(folder)
    except D.DraftError as e:
        sys.exit(f"{folder}: {e}")


def show(checks):
    for c in checks:
        if not c["ok"]:
            print(f'{"UNTESTED" if c["level"] == "experimental" else "FAIL":8} {c["id"]:30} {c["message"]}')
    v = S.verdicts(checks)
    for lv in S.LEVELS:
        n = [c for c in checks if c["level"] == lv]
        print(f'{S.LEVEL_NAMES[lv]:26} {"yes" if v[lv] else "NO":4} ({sum(c["ok"] for c in n)} of {len(n)} checks)')
    return v


# ---------------------------------------------------------------- commands

def cmd_template(a):
    out = pathlib.Path(a.folder)
    if (out / "sheet.json").exists() and not a.force:
        sys.exit(f"{out / 'sheet.json'} exists (use --force to overwrite)")
    raw = S.tray(a.length, a.width, a.height, flange=a.flange, dims=a.dims, name=out.name,
                 flange_walls=tuple(a.flange_walls.split(",")))
    raw = {"_comment": "A hand-folded sheet part (scripts/sheet_lib.py). Written by sheet_cli.py template tray; edit freely. "
                       "Panels, folds and recipes are independent: change a fold's recipe without touching the panels.", **raw}
    save(out / "sheet.json", raw)
    try:
        S.resolve(raw, name=out.name)
    except D.DraftError as e:
        sys.exit(f"the template does not resolve: {e}")
    print(out / "sheet.json")


def cmd_check(a):
    v = show(S.checks(load(a.folder)))
    print("(host checks only: flat overlap, folded interference and the folding sequence need build)")
    sys.exit(0 if v["geometric"] and v["manufacturable"] else 1)


def _job(sheet, out_dir, text):
    cuts, relief = [], []
    for f in sheet["folds"]:
        c, r = S.fold_entities(sheet, f)
        cuts += c
        relief += r
    zones = [[f["s"], f["e"], f["e2"], f["s2"]] for f in sheet["folds"] if sheet["recipes"][f["recipe"]]["allowance"] > 0]
    return {
        "name": sheet["name"], "t": sheet["t"], "out_dir": str(out_dir),
        "panels": [{"id": pid, "flat": p["flat"], "cuts": p["flat_features"]} for pid, p in sheet["panels"].items()],
        "zones": zones, "reliefs": relief, "perforations": cuts,
        "folds": [{"id": f["id"], "m0": f["m0"], "m1": f["m1"], "d": f["d"], "hinge_z": f["hinge_z"],
                   "label": f'{f["parent"]} to {f["child"]}, {f["direction"]} {f["angle"]:g} deg, step {f["sequence"]}, recipe {f["recipe"]}'}
                  for f in sheet["folds"]],
        "chain": {pid: [f["id"] for f in S.chain(sheet, pid)] for pid in sheet["panels"]},
        "connected": [[f["parent"], f["child"]] for f in sheet["folds"]],
        "states": S.states(sheet),
        "params": [[k, f'{v["value"]:g}  ({v["src"]})'] for k, v in sheet["params"].items()],
        "material": [[sheet["material"], ""]] + [[k, v] for k, v in sheet["mat"].items() if k != "tested"]
                    + [["tested recipes", len(sheet["mat"].get("tested", []))]],
        "manufacturing": [[sheet["manufacturing"], ""]] + list(sheet["man"].items()),
        "validation_text": text,
        "export_text": "Written by sheet_cli.py build: flat/*.dxf, flat/*.svg, folded/*.step, report.json",
        "fcstd": str(out_dir.parent / f'{sheet["name"]}.FCStd'), "step": str(out_dir / f'{sheet["name"]}.step'),
    }


def _dxf_layers(sheet, loops, untested):
    cut, perf, ref, direction = [], [], [], []
    for face in loops:
        for lp in [face["outer"]] + face["holes"]:
            if lp["kind"] == "poly":
                pts = lp["pts"]
                lp = {"kind": "poly", "closed": True, "pts": pts,
                      "bulges": [dxf_io.bulge(pts[k], pts[(k + 1) % len(pts)], m) if m else 0 for k, m in enumerate(lp["mids"])]}
            cut.append(lp)
    for f in sheet["folds"]:
        perf += S.fold_entities(sheet, f)[0]
        ref.append({"kind": "line", "a": f["m0"], "b": f["m1"]})
        # an arrow on the moving panel: it points away from the fold for "up" (toward the viewer), at it for "down"
        mid = [(f["m0"][0] + f["m1"][0]) / 2, (f["m0"][1] + f["m1"][1]) / 2]
        p = lambda u, v: [mid[0] + f["n"][0] * u + f["d"][0] * v, mid[1] + f["n"][1] * u + f["d"][1] * v]  # noqa: E731
        tip, tail = (6.0, 2.0) if f["direction"] == "up" else (2.0, 6.0)
        back = tip - 1.5 if tip > tail else tip + 1.5
        direction += [{"kind": "line", "a": p(tail, 0), "b": p(tip, 0)}, {"kind": "line", "a": p(tip, 0), "b": p(back, 0.8)},
                      {"kind": "line", "a": p(tip, 0), "b": p(back, -0.8)}]
    x0, y0, _, _ = S.flat_extent(sheet)
    if untested:
        ref += dxf_io.text("UNTESTED", x0, y0 - 9, 5)
    return {"CUT_THROUGH": cut, "FOLD_PERFORATION": perf, "FOLD_DIRECTION": direction, "REFERENCE": ref}


def cmd_build(a):
    import freecad_run
    import render_config as rc
    folder = pathlib.Path(a.folder).resolve()
    if folder.parent.name == "parts" and (folder.parents[1] / "brief.json").exists():
        ok, msg = D.gate(folder.parents[1], folder.name)
        if not ok:
            sys.exit(msg)
    sheet = load(folder)
    name, checks = sheet["name"], S.checks(sheet)
    add = lambda cid, ok, msg: S._check(checks, cid, "geometric", ok, msg)  # noqa: E731

    work = folder / "folded"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    host = "\n".join(f'{"ok  " if c["ok"] else "FAIL"} [{c["level"]}] {c["message"]}' for c in checks)
    job_file, res = work / "job.json", pathlib.Path(tempfile.mkdtemp(prefix="fcsheet_")) / "sheet.json"
    (folder / f"{name}.FCStd").unlink(missing_ok=True)      # or FreeCAD leaves a backup copy beside it
    save(job_file, {**_job(sheet, work, "Host checks at build time (report.json has the full verdicts):\n" + host), "out_json": str(res)})
    proc, cmd = freecad_run.run(ROOT / "scripts" / "fc" / "fc_sheet.py", "FC_JOB", {"job_file": str(job_file)})
    err = res.with_name(res.name + ".error")
    if err.exists() or not res.exists():
        sys.exit(f"FreeCAD failed ({freecad_run.describe(cmd)}):\n" + (err.read_text() if err.exists() else proc.stdout[-3000:] + proc.stderr[-3000:]))
    r = D.load_json(res)
    job_file.unlink()

    # the kernel's findings
    add("flat.overlap", not r["flat_overlaps"], "panels do not overlap in the flat pattern" if not r["flat_overlaps"] else
        "panels overlap in the flat pattern: " + ", ".join(" / ".join(o["pair"]) for o in r["flat_overlaps"]))
    add("flat.one_piece", r["flat_pieces"] == 1, f'the flat pattern is {r["flat_pieces"]} piece(s)')
    lo, hi = S.folded_bbox(sheet)
    same = all(abs(x - y) <= 0.01 for x, y in zip(lo + hi, r["bbox_min"] + r["bbox_max"]))
    add("folded.bbox", same, "the kernel's folded envelope equals the arithmetic's" if same else
        f'folded envelope differs: kernel {r["bbox_min"]}..{r["bbox_max"]}, arithmetic {lo}..{hi}')
    final = r["states"][-1]["interference"]
    add("folded.interference", not final, "no folded panels collide" if not final else
        "folded panels collide: " + ", ".join(f'{" / ".join(i["pair"])} ({i["volume_mm3"]:g} mm³)' for i in final))
    for g in sorted({s["sequence"] for s in r["states"]}):
        bad = [(s["label"], i) for s in r["states"] if s["sequence"] == g for i in s["interference"]]
        add(f"sequence.{g}", not bad, f"folding step {g} can be carried out" if not bad else
            f'folding step {g} collides at {bad[0][0]}: {" / ".join(bad[0][1]["pair"])}')

    # flat pattern files, and the DXF read back
    untested = S.untested(sheet)
    flat = folder / "flat"
    shutil.rmtree(flat, ignore_errors=True)
    flat.mkdir()
    dxf = flat / f'{name}{"_UNTESTED" if untested else ""}.dxf'
    layers = _dxf_layers(sheet, r["loops"], untested)
    dxf_io.write(dxf, layers)
    back = dxf_io.read(dxf)
    ext, want = dxf_io.extent({"c": back.get("CUT_THROUGH", [])}), S.flat_extent(sheet)
    ok = dxf_io.counts(back) == dxf_io.counts(layers) and ext is not None and all(abs(x - y) <= 1e-3 for x, y in zip(ext, want))
    add("flat.dxf_readback", ok, f"the DXF reads back with the same entities per layer and the blank's extent ({dxf_io.counts(back)})")
    (flat / f"{name}.svg").write_text(sheet_draw.flat_svg(sheet), encoding="utf-8", newline="\n")

    renders = []
    if rc.blender_exe():
        shutil.rmtree(folder / "renders", ignore_errors=True)
        for stl, cap in r["stls"]:
            first = cap == "folded"
            sub = folder / "renders" / ("" if first else pathlib.Path(stl).stem)
            views = "isometric,front,right,top" if first else "isometric"
            if rc.run_blender("bl_check_views.py", "--stl", stl, "--out", sub, "--size", 700, "--views", views, timeout=900)[0] == 0:
                renders += [[str(sub / f"{v}.png"), cap if not first else v] for v in views.split(",")]
    else:
        print("no renders: Blender not found (config/render.local.json)")
    for f in work.glob("*.stl"):
        f.unlink()

    v = show(checks)
    x0, y0, x1, y1 = want
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    report = {
        "schema_version": "1.0", "sheet": name, "timestamp": stamp, "freecad_version": r["freecad_version"],
        "material": sheet["material"], "manufacturing": sheet["manufacturing"], "manufacturing_status": sheet["man"].get("status", ""),
        "verdicts": {S.LEVEL_NAMES[lv]: v[lv] for lv in S.LEVELS}, "untested": untested,
        "blank_mm": [round(x1 - x0, 3), round(y1 - y0, 3), sheet["t"]], "flat_area_mm2": r["flat_area"],
        "folded_envelope_mm": [round(h - l, 3) for l, h in zip(r["bbox_min"], r["bbox_max"])], "volume_mm3": r["volume"],
        "folds": [{"id": f["id"], "parent": f["parent"], "child": f["child"], "angle": f["angle"], "direction": f["direction"],
                   "sequence": f["sequence"], "recipe": f["recipe"], "length": round(f["length"], 3),
                   **FP.summary(f["length"], sheet["recipes"][f["recipe"]])} for f in sheet["folds"]],
        "bom": [{"name": f'{sheet["mat"]["alloy"]}-{sheet["mat"]["temper"]} sheet, {sheet["t"]:g} mm', "qty": 1,
                 "blank_mm": [round(x1 - x0, 1), round(y1 - y0, 1)]}] + sheet["hardware"],
        "checks": checks, "files": {"dxf": str(dxf), "svg": str(flat / f"{name}.svg"), "step": str(work / f"{name}.step"),
                                    "fcstd": str(folder / f"{name}.FCStd")}, "renders": renders}
    verdict = "fail" if not (v["geometric"] and v["manufacturable"]) else "untested" if untested else "pass"
    save(folder / "report.json", report)
    save(folder / "validation" / "history" / f"{stamp}_{verdict}.json", report)
    print(f'blank {x1 - x0:g} × {y1 - y0:g} × {sheet["t"]:g}; folded {" × ".join(f"{x:g}" for x in report["folded_envelope_mm"])}; {len(sheet["folds"])} folds')
    print(f"dxf: {dxf}\nstep: {work / (name + '.step')}")
    if untested:
        print("UNTESTED: at least one fold has no passing coupon; the outputs are marked.")
    sys.exit(0 if verdict != "fail" else 1)


def cmd_coupons(a):
    out = pathlib.Path(a.folder)
    mat, man = S.profile("materials", a.material), S.profile("manufacturing", a.manufacturing)
    w, length = (float(x) for x in a.strip.lower().split("x"))
    lens, bridges = [float(x) for x in a.slot_lengths.split(",")], [float(x) for x in a.bridges.split(",")]
    if len(lens) * len(bridges) > 99:
        sys.exit("at most 99 coupons per sheet")
    gap, layers, table, n = 6.0, {"CUT_THROUGH": [], "FOLD_PERFORATION": [], "ENGRAVING": [], "REFERENCE": []}, [], 0
    for row, br in enumerate(bridges):
        for col, sl in enumerate(lens):
            n += 1
            cid = f"{n:02d}"
            x, y = col * (w + gap), row * (length + gap)
            rec = {**FP.DEFAULTS["slots"], "method": "slots", "slot_length": sl, "slot_width": a.slot_width, "bridge": br,
                   "end_clearance": a.end_clearance}
            s = FP.summary(w, rec)
            layers["CUT_THROUGH"].append({"kind": "poly", "closed": True, "pts": [[x, y], [x + w, y], [x + w, y + length], [x, y + length]]})
            for sc, slen in FP.generate(w, rec):
                c = [x + sc, y + length / 2]
                if a.slot_width <= 0:
                    layers["FOLD_PERFORATION"].append({"kind": "line", "a": [c[0] - slen / 2, c[1]], "b": [c[0] + slen / 2, c[1]]})
                else:
                    h = max((slen - a.slot_width) / 2, 0)
                    layers["FOLD_PERFORATION"].append({"kind": "stadium", "a": [c[0] - h, c[1]], "b": [c[0] + h, c[1]], "w": a.slot_width})
            layers["ENGRAVING"] += dxf_io.text(cid, x + 3, y + 3, 5)
            flags = [m for ok, m in ((s["slots"] >= 1, "no slot fits"), (br >= man["min_bridge"], "bridge under the profile's minimum"),
                                     (s["end_uncut"] >= man["min_end_clearance"], "end clearance under the profile's minimum")) if not ok]
            table.append({"id": cid, "recipe": {k: rec[k] for k in ("method", "slot_length", "slot_width", "bridge", "end_clearance")},
                          "fold_length": w, "flat_length": length, **s, "flags": flags})
    out.mkdir(parents=True, exist_ok=True)
    dxf_io.write(out / "coupons.dxf", layers)
    back = dxf_io.read(out / "coupons.dxf")
    if dxf_io.counts(back) != dxf_io.counts(layers):
        sys.exit("the coupon DXF did not read back as written")
    save(out / "coupons.json", {
        "_comment": "Cut coupons.dxf, fold each strip by hand to the target angle with the engraved end (leg A) held flat, then record "
                    "each result with sheet_cli.py record. Leg lengths are measured on the outside, from the strip's end to the far face of the other leg.",
        "material": a.material, "manufacturing": a.manufacturing, "thickness": mat["thickness"], "strip": [w, length], "coupons": table})
    lines = ["# Fold coupons", "", f"Material {a.material} ({mat['thickness']:g} mm). Strips {w:g} × {length:g}, one fold across the middle. "
             "The engraved number is at the end of leg A.", "", "| ID | Slot length | Slot width | Bridge | Slots | Line left as bridges | Flags |",
             "|---|---|---|---|---|---|---|"]
    lines += [f'| {c["id"]} | {c["recipe"]["slot_length"]:g} | {c["recipe"]["slot_width"]:g} | {c["recipe"]["bridge"]:g} | {c["slots"]} | '
              f'{c["bridge_share"] * 100:.0f} % | {"; ".join(c["flags"]) or "none"} |' for c in table]
    lines += ["", "| ID | Held or cracked | Angle reached | Leg A | Leg B | Notes |", "|---|---|---|---|---|---|"] + [f'| {c["id"]} | | | | | |' for c in table]
    (out / "coupons.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f'{n} coupons: {out / "coupons.dxf"}\ntable to fill in: {out / "coupons.md"}')


def cmd_record(a):
    path = pathlib.Path(a.coupons)
    data = D.load_json(path)
    c = next((c for c in data["coupons"] if c["id"] == a.id), None)
    if c is None:
        sys.exit(f"{path} has no coupon {a.id}")
    lib = S.LIB / "materials.json"
    mats = D.load_json(lib)
    entry = {"coupon": f"{path.parent.name}:{a.id}", "date": dt.date.today().isoformat(), "recipe": c["recipe"], "angle": a.angle,
             "result": a.result, "grain": a.grain, "notes": a.notes or ""}
    if a.leg_a is not None and a.leg_b is not None:
        # rigid model: the two outside legs add up to the flat length plus twice the hinge height
        entry.update(legs=[a.leg_a, a.leg_b], hinge_measured=round((a.leg_a + a.leg_b - c["flat_length"]) / (2 * data["thickness"]), 3))
    mats[data["material"]].setdefault("tested", []).append(entry)
    if a.result == "held":
        mats[data["material"]]["status"] = "has tested fold recipes: see 'tested'"
    save(lib, mats)
    print(f'recorded {entry["coupon"]} as {a.result} in {lib}' + (f' (hinge at {entry["hinge_measured"]:g} of the thickness)' if "legs" in entry else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("template")
    p.add_argument("kind", choices=("tray",))
    p.add_argument("folder")
    for name in ("length", "width", "height"):
        p.add_argument(f"--{name}", type=float, required=True)
    p.add_argument("--flange", type=float, default=0.0)
    p.add_argument("--flange-walls", default="front,right,rear,left")
    p.add_argument("--dims", choices=("outside", "inside"), default="outside")
    p.add_argument("--force", action="store_true")
    for name in ("check", "build"):
        sub.add_parser(name).add_argument("folder")
    p = sub.add_parser("coupons")
    p.add_argument("folder")
    p.add_argument("--material", default="5052-H32_1.0")
    p.add_argument("--manufacturing", default="generic_untested")
    p.add_argument("--slot-lengths", required=True)
    p.add_argument("--bridges", required=True)
    p.add_argument("--slot-width", type=float, default=0.5)
    p.add_argument("--end-clearance", type=float, default=2.0)
    p.add_argument("--strip", default="40x60", help="fold length x flat length, mm")
    p = sub.add_parser("record")
    p.add_argument("coupons")
    p.add_argument("--id", required=True)
    p.add_argument("--result", required=True, choices=("held", "cracked", "partial"))
    p.add_argument("--angle", type=float, required=True, help="angle reached, degrees")
    p.add_argument("--leg-a", type=float)
    p.add_argument("--leg-b", type=float)
    p.add_argument("--grain", choices=("along", "across", "unknown"), default="unknown", help="rolling direction relative to the fold line")
    p.add_argument("--notes")
    a = ap.parse_args(argv)
    {"template": cmd_template, "check": cmd_check, "build": cmd_build, "coupons": cmd_coupons, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
