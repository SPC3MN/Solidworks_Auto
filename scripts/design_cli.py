"""The drafting phase of the /design skill: brief -> option rounds -> massing -> approval. One entry point.

    python3 scripts/design_cli.py init     <name> --title "Hand grinder"
    python3 scripts/design_cli.py round    products/<name> [--options A,B,C] [--from A | --from A=AC]
    python3 scripts/design_cli.py board    products/<name> [--round N]
    python3 scripts/design_cli.py decide   products/<name> --move pick|merge|pushback --options A[,C] --notes "<the owner's words>"
    python3 scripts/design_cli.py massing  products/<name> [--option A] [--round N]
    python3 scripts/design_cli.py approve  products/<name> --quote "<the owner's approval, verbatim>"
    python3 scripts/design_cli.py status   products/<name>
    python3 scripts/design_cli.py gate     products/<name> [--part <id>]
    python3 scripts/design_cli.py params   products/<name> --part <id>      # approved values -> parts/<id>/parameters/params.json

A round holds one design unless the owner asked for options (brief.json "options": N): then it holds
N, A is the simplest, and the others must differ from it in architecture.

`board` checks every option of a round (parameters, bodies, fit checks, the brief's machine-checked
requirements and, with several options, A being the simplest and the architectures differing), draws
the sketches at one common scale and writes round_N/board.html. It exits 1 while anything is wrong,
and the board says what.

The approval gate: `approve` needs a current board without problems and a passing massing of the
same option, and records the owner's words with the hashes of the brief and of every part. Detail
modelling (pipeline.py on products/<name>/parts/<part>) refuses to run unless `gate` passes. Run
`approve` only after the owner has explicitly approved the massing in chat.
"""
import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import design_board  # noqa: E402
import draft_lib as D  # noqa: E402
import sketch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The owner's standing defaults (assumed without asking; a brief can override them).
DEFAULTS = {"goal": "the simplest design that works", "machined": "6061-T6", "printed": "PLA, FDM",
            "fits": "ISO 286", "general_tolerance": "ISO 2768-mK", "units": "mm"}


# ---------------------------------------------------------------- helpers

def product_dir(arg):
    p = pathlib.Path(arg)
    if not (p / "brief.json").exists() and (ROOT / "products" / arg / "brief.json").exists():
        p = ROOT / "products" / arg
    if not (p / "brief.json").exists():
        sys.exit(f"{arg}: no brief.json (run design_cli.py init <name> first)")
    return p.resolve()


def save(p, data):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def rounds(product):
    return sorted(int(p.name[6:]) for p in (product / "draft").glob("round_*") if p.name[6:].isdigit())


def round_dir(product, n=None):
    have = rounds(product)
    if not have:
        sys.exit("no rounds yet: design_cli.py round <product>")
    n = n or have[-1]
    if n not in have:
        sys.exit(f"round {n} does not exist (rounds: {have})")
    return n, product / "draft" / f"round_{n}"


def option_dirs(rdir):
    return sorted(p for p in rdir.iterdir() if p.is_dir() and (p / "option.json").exists())


def read_log(product):
    p = product / "draft" / "log.json"
    return D.load_json(p) if p.exists() else []


def add_log(product, **entry):
    save(product / "draft" / "log.json", read_log(product) + [{"time": now(), **entry}])


def load_opts(rdir):
    try:
        return [D.load_option(f) for f in option_dirs(rdir)]
    except D.DraftError as e:
        sys.exit(f"cannot draw the board: {e}")


def options_asked(brief):
    """How many options the owner asked for. One design is the default."""
    n = brief.get("options", 1)
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 6:
        sys.exit('brief.json "options" must be a whole number from 1 to 6')
    return n


def shortlisted(product):
    """(round, option id) to mass and approve: the owner's pick in the latest round, or that
    round's only design. None while a choice, a merge or a push-back is still open."""
    have = rounds(product)
    if not have:
        return None
    for e in reversed(read_log(product)):
        if e["round"] == have[-1] and e["move"] == "pick":
            return have[-1], e["options"][0]
        if e["round"] == have[-1] and e["move"] in ("merge", "pushback"):
            return None
    ids = option_dirs(product / "draft" / f"round_{have[-1]}")
    return (have[-1], ids[0].name) if len(ids) == 1 else None


# ---------------------------------------------------------------- commands

def cmd_init(a):
    name = a.product
    if not name.replace("_", "").isalnum() or name != name.lower():
        sys.exit("the product name must be snake_case")
    product = ROOT / "products" / name
    if (product / "brief.json").exists():
        sys.exit(f"{product} already exists")
    (product / "references" / "inspiration").mkdir(parents=True)
    save(product / "brief.json", {
        "schema_version": "1.0", "product": name, "title": a.title or name.replace("_", " ").capitalize(), "purpose": "",
        "options": 1,
        "_comment": "Stage 0 of /design. options: how many designs to draw per round; 1 unless the owner asks for options. requirements: {id, text, priority must|should|free, provenance given|measured|chosen|estimated, "
                    "source, check {lhs, op, rhs} (optional, over option parameters and bbox_x/y/z, parts_total, parts_make, parts_buy, "
                    "fasteners, setups)}. Keys starting with _ are notes. See .claude/skills/design/references/schemas.md.",
        "defaults": DEFAULTS, "requirements": [], "bought_parts": [], "conflicts": [], "open_questions": [], "notes": []})
    save(product / "draft" / "inspiration.json", {
        "_comment": "Stage 1 of /design. pictures: {file (relative to the product folder), caption, form [], mechanism [], materials []}; "
                    "summary: the rules carried into the options.",
        "pictures": [], "summary": {"form": [], "mechanism": [], "materials": []}})
    print(f"created {product}\nnext: fill brief.json from what the owner gave, then design_cli.py round {product.relative_to(ROOT)}")


def cmd_round(a):
    product = product_dir(a.product)
    have = rounds(product)
    n = (have[-1] if have else 0) + 1
    rdir = product / "draft" / f"round_{n}"
    copied = []
    for item in a.frm.split(",") if a.frm else []:
        old, _, new = item.partition("=")
        src = product / "draft" / f"round_{n - 1}" / old
        if not (src / "option.json").exists():
            sys.exit(f"--from {old}: round {n - 1} has no option {old}")
        (rdir / (new or old)).mkdir(parents=True)
        for f in ("option.json", "params.json"):
            shutil.copy2(src / f, rdir / (new or old) / f)
        copied.append(f"{old} as {new}" if new else old)
    asked = options_asked(D.load_json(product / "brief.json"))
    # a merge round (--from A=AC) holds only the hybrid; any other round holds as many designs as the owner asked for
    for oid in a.options.split(",") if a.options else ([] if "=" in (a.frm or "") else list("ABCDEF"[:asked])):
        (rdir / oid).mkdir(parents=True, exist_ok=True)
    print(f"round {n}: {rdir}")
    print("write option.json and params.json in:", ", ".join(sorted(p.name for p in rdir.iterdir())),
          f"(copied from round {n - 1}: {', '.join(copied)})" if copied else "")


def round_problems(brief, opts, reqs):
    out = [f"brief: unresolved conflict: {c.get('text', '')}" for c in brief.get("conflicts", []) if not c.get("resolution")]
    for o in opts:
        if not o["fit_results"]:
            out.append(f"{o['id']}: no fit checks. Every option needs the arithmetic that its parts fit.")
        out += [f"{o['id']}: fit check fails: {r['why'] or r['id']} ({r['lhs_expr']} = {r['lhs']:g} {r['op']} {r['rhs_expr']} = {r['rhs']:g})"
                for r in o["fit_results"] if not r["ok"]]
        out += [f"{o['id']}: must {r['id']} is not met: {r['why']}" + (f" ({r['error']})" if r.get("error") else f" ({r['lhs']:g} {r['op']} {r['rhs']:g})")
                for r in reqs[o["id"]] if r["priority"] == "must" and not r["ok"]]
    asked = brief.get("options", 1)
    if len(opts) < asked and not any(o["merged_from"] for o in opts):
        out.append(f"the owner asked for {asked} options and this round has {len(opts)}")
    if len(opts) > 1:
        base = next((o for o in opts if o["id"] == "A"), None)
        if base is None:
            out.append("a round of several options needs an option A: the simplest design that meets every must")
        for o in opts:
            if base and o is not base and o["scorecard"]["parts_total"] < base["scorecard"]["parts_total"]:
                out.append(f"{o['id']} has fewer parts ({o['scorecard']['parts_total']}) than A ({base['scorecard']['parts_total']}): "
                           "A must be the simplest option")
        norm = lambda o: tuple(" ".join(str(o["architecture"][k]).lower().split()) for k in D.ARCH_KEYS)  # noqa: E731
        for i, o in enumerate(opts):
            for p in opts[i + 1:]:
                if norm(o) == norm(p):
                    out.append(f"{o['id']} and {p['id']} have the same architecture: options must differ in mechanism, layout, load path or process")
    return out


def cmd_board(a):
    product = product_dir(a.product)
    n, rdir = round_dir(product, a.round)
    try:
        brief = D.load_brief(product)
    except D.DraftError as e:
        sys.exit(str(e))
    opts = load_opts(rdir)
    if not opts:
        sys.exit(f"{rdir}: no options (each needs option.json and params.json)")
    reqs = {o["id"]: D.requirement_results(brief, o) for o in opts}
    problems = round_problems(brief, opts, reqs)
    try:
        scale = min(sketch.fit_scale(o) for o in opts)
        svgs = {o["id"]: sketch.write(o, scale, uid=f"r{n}{o['id']}") for o in opts}
    except D.DraftError as e:
        sys.exit(f"cannot draw the board: {e}")
    for o in opts:
        rep = o["folder"] / "massing" / "report.json"
        o["massing"] = D.load_json(rep) if rep.exists() else None
        save(o["folder"] / "scorecard.json", {
            "option": o["id"], "round": n, "hash": o["hash"], "scorecard": o["scorecard"], "envelope_mm": o["derived"],
            "fit": o["fit_results"], "requirements": reqs[o["id"]],
            "problems": [p for p in problems if p.startswith(f"{o['id']}:") or p.startswith(f"{o['id']} ")]})
    insp_path = product / "draft" / "inspiration.json"
    insp = D.load_json(insp_path) if insp_path.exists() else {}
    board = rdir / "board.html"
    board.write_text(design_board.build(product, brief, n, opts, svgs, reqs, problems, insp), encoding="utf-8", newline="\n")
    save(rdir / "round.json", {"round": n, "time": now(), "brief_hash": D.brief_hash(brief), "scale_px_per_mm": round(scale, 4),
                               "options": {o["id"]: o["hash"] for o in opts}, "problems": problems})
    for o in opts:
        sc = o["scorecard"]
        print(f"{o['id']}  {o['name']}: {sc['parts_total']} parts ({sc['parts_make']} make, {sc['parts_buy']} buy), "
              f"{sc['fasteners']} fasteners, {sc['setups']} setups, fits {sum(r['ok'] for r in o['fit_results'])}/{len(o['fit_results'])}")
    print(f"board: {board}")
    if problems:
        print("\nNOT READY:\n  " + "\n  ".join(problems))
        sys.exit(1)


def cmd_decide(a):
    product = product_dir(a.product)
    n, rdir = round_dir(product, a.round)
    have = [p.name for p in option_dirs(rdir)]
    ids = a.options.split(",") if a.options else []
    for oid in ids:
        if oid not in have:
            sys.exit(f"round {n} has no option {oid} (options: {have})")
    if a.move == "pick" and len(ids) != 1:
        sys.exit("pick names exactly one option")
    if a.move == "merge" and len(ids) < 2:
        sys.exit("merge names the options it combines (--options A,C) and --notes says which pieces")
    if a.move != "pick" and not a.notes:
        sys.exit("--notes with the owner's words is required")
    add_log(product, round=n, move=a.move, options=ids, notes=a.notes or "")
    if a.move == "pushback":
        brief = D.load_json(product / "brief.json")
        brief.setdefault("notes", []).append({"round": n, "time": now(), "text": a.notes, "options": ids})
        save(product / "brief.json", brief)
        print(f"notes added to brief.json. Turn each into a requirement (or a conflict to settle), then: design_cli.py round {a.product}")
    elif a.move == "merge":
        print(f"next: design_cli.py round {a.product} --from {ids[0]}={''.join(ids)}  (start from the option that gives most), write the hybrid there "
              f"with \"merged_from\": {json.dumps([f'{n}:{i}' for i in ids])}, and re-check its fits before showing it")
    else:
        print(f"next: design_cli.py massing {a.product}")


def cmd_massing(a):
    import freecad_run
    import render_config as rc
    product = product_dir(a.product)
    pick = shortlisted(product)
    if a.option:
        n, rdir = round_dir(product, a.round)
        oid = a.option
    elif pick:
        (n, oid), rdir = pick, product / "draft" / f"round_{pick[0]}"
    else:
        sys.exit("the owner has not chosen between this round's options: record the pick with design_cli.py decide --move pick, or pass --option")
    try:
        o = D.load_option(rdir / oid)
    except D.DraftError as e:
        sys.exit(str(e))
    out = rdir / oid / "massing"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    res = pathlib.Path(tempfile.mkdtemp(prefix="fcmass_")) / "massing.json"
    job = {"name": f"{product.name}_{oid}", "out_dir": str(out), "out_json": str(res), "section_y": o["section_y"],
           "parts": [{"id": p["id"], "bodies": p["bodies"], "instances": p["instances"]} for p in o["parts"]]}
    proc, cmd = freecad_run.run(ROOT / "scripts" / "fc" / "fc_massing.py", "FC_JOB", job)
    err = res.with_name(res.name + ".error")
    if err.exists() or not res.exists():
        sys.exit(f"massing failed ({freecad_run.describe(cmd)}):\n" + (err.read_text() if err.exists() else proc.stdout[-3000:] + proc.stderr[-3000:]))
    r = D.load_json(res)

    checks = []
    for ax, got, want in zip("xyz", r["bbox"], (o["derived"][k] for k in ("bbox_x", "bbox_y", "bbox_z"))):
        ok = abs(got - want) <= 0.01
        checks.append({"id": f"bbox.{ax}", "ok": ok, "message": f"3D envelope {ax} is {got:g}, the sketch says {want:g}"})
    for pid, p in r["parts"].items():
        ok = p["valid"] and p["solids"] == 1 and p["volume"] > 0
        checks.append({"id": f"solid.{pid}", "ok": ok, "message": f"part {pid} is {p['solids']} separate solids (a part is one piece)"
                       if p["solids"] != 1 else f"part {pid} is not a valid solid"})
    allowed = [sorted(x[:2]) for x in o["allowed_interference"]]
    for itf in r["interference"]:
        ok = itf["pair"] in allowed
        checks.append({"id": "interference." + "/".join(itf["pair"]), "ok": ok,
                       "message": f"{itf['pair'][0]} and {itf['pair'][1]} overlap by {itf['volume_mm3']:g} mm³"})

    renders = []
    if rc.blender_exe():
        for stl, sub, views, tag in ((r["stl"], "", "isometric,front,right,top", ""), (r["section_stl"], "section", "isometric,front", "section, ")):
            if stl and rc.run_blender("bl_check_views.py", "--stl", stl, "--out", out / "renders" / sub, "--size", 600, "--views", views, timeout=900)[0] == 0:
                renders += [[str(out / "renders" / sub / f"{v}.png"), tag + v] for v in views.split(",")]
    else:
        print("no clay renders: Blender not found (config/render.local.json)")
    for f in out.glob("*.stl"):
        f.unlink()  # only needed for the renders; the STEP is the massing model
    status = "pass" if all(c["ok"] for c in checks) else "fail"
    save(out / "report.json", {"option": oid, "round": n, "option_hash": o["hash"], "time": now(), "status": status,
                               "freecad_version": r["freecad_version"], "bbox": r["bbox"], "parts": r["parts"],
                               "interference": r["interference"], "checks": checks, "step": r["step"], "renders": renders})
    for c in checks:
        if not c["ok"]:
            print("FAIL ", c["message"])
    print(f"massing {status.upper()}: {out / 'massing.step'}  ({len(renders)} renders)")
    cmd_board(argparse.Namespace(product=str(product), round=n))
    if status != "pass":
        sys.exit(1)


def cmd_approve(a):
    product = product_dir(a.product)
    if not a.quote:
        sys.exit("--quote with the owner's approval, verbatim, is required")
    pick = shortlisted(product)
    if a.option:
        n, rdir = round_dir(product, a.round)
        oid = a.option
    elif pick:
        (n, oid), rdir = pick, product / "draft" / f"round_{pick[0]}"
    else:
        sys.exit("the owner has not chosen between this round's options: design_cli.py decide --move pick first")
    folder = rdir / oid
    try:
        o, brief = D.load_option(folder), D.load_brief(product)
    except D.DraftError as e:
        sys.exit(str(e))
    info = D.load_json(rdir / "round.json") if (rdir / "round.json").exists() else {}
    if info.get("options", {}).get(oid) != o["hash"] or info.get("brief_hash") != D.brief_hash(brief):
        sys.exit("the board is out of date (the option or the brief changed): run board, show it, and ask again")
    mine = [p for p in info.get("problems", []) if p.startswith((f"{oid}:", f"{oid} ", "brief:"))]
    if mine:
        sys.exit("cannot approve an option with open problems:\n  " + "\n  ".join(mine))
    rep = folder / "massing" / "report.json"
    if not rep.exists():
        sys.exit("no 3D massing of this option: design_cli.py massing, show the owner the renders, then ask")
    rep = D.load_json(rep)
    if rep["option_hash"] != o["hash"] or rep["status"] != "pass":
        sys.exit("the massing is out of date or failed its checks: rebuild it, show it, and ask again")

    draft = product / "draft"
    old = D.load_json(draft / "approval.json") if (draft / "approval.json").exists() else None
    if old:
        hist = draft / "history" / old["approved_at"].replace(":", "")
        hist.mkdir(parents=True)
        shutil.move(str(draft / "approval.json"), hist / "approval.json")
        if (draft / "approved").exists():
            shutil.move(str(draft / "approved"), hist / "approved")
    shutil.rmtree(draft / "approved", ignore_errors=True)
    shutil.copytree(folder, draft / "approved", ignore=shutil.ignore_patterns("renders", "*.stl"))
    save(draft / "approved" / "option.json", {**D.load_json(folder / "option.json"), "id": oid})
    changed = sorted(k for k in set(o["part_hashes"]) | set(old["parts"] if old else {})
                     if (old["parts"] if old else {}).get(k) != o["part_hashes"].get(k))
    save(draft / "approval.json", {"approved_at": now(), "quote": a.quote, "round": n, "option": oid, "option_hash": o["hash"],
                                   "brief_hash": D.brief_hash(brief), "parts": o["part_hashes"],
                                   "changed_since_last_approval": changed if old else None})
    add_log(product, round=n, move="approve", options=[oid], notes=a.quote)
    print(f"approved option {oid} of round {n} ({o['hash']}). Parts: {', '.join(o['part_hashes'])}")
    if old:
        print("parts to rebuild (changed or new since the last approval):", ", ".join(changed) or "none")


def cmd_status(a):
    product = product_dir(a.product)
    brief = D.load_brief(product)
    reqs = brief.get("requirements", [])
    print(f"{brief.get('title', product.name)}: " + ", ".join(f"{sum(r['priority'] == p for r in reqs)} {p}" for p in D.PRIORITIES)
          + f"; {sum(not c.get('resolution') for c in brief.get('conflicts', []))} open conflicts"
          + f"; {sum(not q.get('answer') for q in brief.get('open_questions', []))} open questions"
          + f"; {options_asked(brief)} design(s) per round")
    for n in rounds(product):
        rdir = product / "draft" / f"round_{n}"
        info = D.load_json(rdir / "round.json") if (rdir / "round.json").exists() else {}
        ids = [p.name for p in option_dirs(rdir)]
        state = "no board" if not info else f"{len(info['problems'])} problems" if info["problems"] else "ready"
        print(f"round {n}: options {', '.join(ids) or 'none'} ({state})")
    for e in read_log(product):
        print(f"  {e['time']}  round {e['round']}  {e['move']} {','.join(e['options'])}" + (f"  \"{e['notes']}\"" if e["notes"] else ""))
    pick = shortlisted(product)
    if pick:
        rep = product / "draft" / f"round_{pick[0]}" / pick[1] / "massing" / "report.json"
        print(f"to mass and approve: {pick[1]} of round {pick[0]}; massing:", D.load_json(rep)["status"] if rep.exists() else "not built")
    print("gate:", D.gate(product)[1])


def cmd_params(a):
    """Start a part's params.json from the approved draft, so detail modelling uses the approved values."""
    product = product_dir(a.product)
    ok, msg = D.gate(product)
    if not ok:
        sys.exit(msg)
    opt = D.load_option(product / "draft" / "approved")
    if a.part not in opt["part_hashes"]:
        sys.exit(f"part '{a.part}' is not in the approved draft ({', '.join(opt['part_hashes'])})")
    out = product / "parts" / a.part / "parameters" / "params.json"
    have = D.load_json(out) if out.exists() else {}
    extra = {k: v for k, v in have.items() if k not in opt["names"] and not k.startswith("_")}
    save(out, {"_comment": f"Values shared with the approved draft (option {opt['id']}, {opt['hash']}) are written by design_cli.py params; "
                           "the gate refuses the part if one differs. Add detail-only parameters below them.",
               **{k: round(v, 6) for k, v in opt["names"].items()}, **extra})
    print(out)


def cmd_gate(a):
    ok, msg = D.gate(product_dir(a.product), a.part)
    print(msg)
    sys.exit(0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("product")
    p.add_argument("--title")
    for name in ("round", "board", "decide", "massing", "approve", "status", "gate", "params"):
        p = sub.add_parser(name)
        p.add_argument("product")
        if name in ("board", "decide", "massing", "approve"):
            p.add_argument("--round", type=int)
        if name == "round":
            p.add_argument("--options", help="empty option folders to create (default: A, or as many as brief.json options says)")
            p.add_argument("--from", dest="frm", help="options to copy from the previous round as a starting point: A, or A=AC to rename (a merge)")
        if name == "decide":
            p.add_argument("--move", required=True, choices=("pick", "merge", "pushback"))
            p.add_argument("--options")
            p.add_argument("--notes")
        if name in ("massing", "approve"):
            p.add_argument("--option")
        if name == "approve":
            p.add_argument("--quote")
        if name in ("gate", "params"):
            p.add_argument("--part", required=name == "params")
    a = ap.parse_args(argv)
    {"init": cmd_init, "round": cmd_round, "board": cmd_board, "decide": cmd_decide, "massing": cmd_massing,
     "approve": cmd_approve, "status": cmd_status, "gate": cmd_gate, "params": cmd_params}[a.cmd](a)


if __name__ == "__main__":
    main()
