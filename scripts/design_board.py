"""The option board of one draft round: a single self-contained HTML page (sketches inline,
pictures embedded) that the owner reads to pick, merge or push back. Written by design_cli.py board.
"""
import base64
import datetime as dt
import html
import mimetypes
import pathlib

from sketch import num

E = html.escape
SIGN = {"<=": "≤", ">=": "≥", "<": "&lt;", ">": "&gt;", "==": "="}

CSS = """
:root{--bg:#fff;--card:#fff;--fg:#1b2230;--mut:#667085;--line:#d9dde5;--soft:#f3f5f8;--ok:#177a45;--bad:#c22a1c;--acc:#3f6fc4}
@media (prefers-color-scheme:dark){:root{--bg:#0e1014;--card:#14171c;--fg:#e7e9ee;--mut:#98a2b3;--line:#2b313b;--soft:#1b1f26;--ok:#4cc38a;--bad:#ff6b5e;--acc:#7ea6ee}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:28px;line-height:1.2;margin:4px 0 8px;text-wrap:balance}
h2{font-size:19px;margin:40px 0 12px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:0 0 4px}
h4{font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--mut);margin:18px 0 6px;font-weight:600}
p{margin:0 0 10px;max-width:72ch}
.eyebrow{color:var(--mut);font-size:13px;margin:0}
.mut{color:var(--mut)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:12.5px;white-space:nowrap}
td.req{min-width:240px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ok{color:var(--ok);font-weight:600}
.bad{color:var(--bad);font-weight:600}
.tag{display:inline-block;font-size:11.5px;font-weight:600;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut);vertical-align:middle;white-space:nowrap}
.tag.must{color:var(--fg);border-color:var(--fg)}
.tag.base{color:var(--acc);border-color:var(--acc)}
.delta{color:var(--mut);font-size:12px;margin-left:6px}
.alert{border:1px solid var(--bad);border-radius:8px;padding:10px 14px;margin:16px 0}
.alert ul{margin:4px 0 0;padding-left:20px}
.opt{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:18px;margin:18px 0}
.opt .sketch{margin:14px -6px 4px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);overflow-x:auto}
.opt .sketch svg{display:block;max-width:none}
dl.arch{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;margin:10px 0 0;font-size:14px}
dl.arch dt{color:var(--mut)}
dl.arch dd{margin:0}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:0 28px}
ul{margin:0 0 10px;padding-left:20px}
code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:1px 5px;border-radius:4px}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.shots figure{margin:0}
.shots img,.insp img{width:100%;height:auto;border-radius:6px;border:1px solid var(--line);display:block}
.shots figcaption{font-size:12px;color:var(--mut);margin-top:3px}
.insp{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.moves{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.moves div{border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:var(--soft)}
.moves b{display:block;margin-bottom:2px}
"""

ROWS = (("parts_total", "Parts, total"), ("parts_make", "Parts to make"), ("parts_buy", "Parts to buy"),
        ("fasteners", "Fasteners"), ("setups", "Setups / print jobs"), ("load_path_parts", "Parts in the load path"))


def data_uri(path):
    p = pathlib.Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def _mark(ok):
    return '<span class="ok">✓</span>' if ok else '<span class="bad">✗</span>'


def _check_cell(r):
    if r.get("error"):
        return f'{_mark(False)} <span class="mut">{E(r["error"])}</span>'
    return f'{_mark(r["ok"])} {num(r["lhs"])} {SIGN.get(r["op"], r["op"])} {num(r["rhs"])}'


def _ul(items):
    return "<ul>" + "".join(f"<li>{E(str(i))}</li>" for i in items) + "</ul>" if items else '<p class="mut">None.</p>'


def _brief(brief, opts, reqs):
    out = ['<h2 id="brief">Brief</h2>']
    confl = [c for c in brief.get("conflicts", []) if not c.get("resolution")]
    if confl:
        out.append('<div class="alert"><b class="bad">Unresolved conflicts in the brief</b>' + _ul(c.get("text", "") for c in confl) + "</div>")
    out.append('<div class="scroll"><table><tr><th>ID</th><th>Priority</th><th>Requirement</th><th>Source</th>'
               + "".join(f'<th>{E(o["id"])}</th>' for o in opts) + "</tr>")
    order = {"must": 0, "should": 1, "free": 2}
    for r in sorted(brief.get("requirements", []), key=lambda r: order[r["priority"]]):
        cells = ""
        for o in opts:
            res = next((x for x in reqs[o["id"]] if x["id"] == r["id"]), None)
            cells += f'<td class="n">{_check_cell(res) if res else "<span class=mut>your call</span>"}</td>'
        src = r["provenance"] + (f' · {r["source"]}' if r.get("source") else "")
        out.append(f'<tr><td>{E(r["id"])}</td><td><span class="tag {r["priority"]}">{r["priority"]}</span></td>'
                   f'<td class="req">{E(r["text"])}</td><td class="mut">{E(src)}</td>{cells}</tr>')
    out.append("</table></div>")
    if brief.get("bought_parts"):
        out.append("<h4>Bought parts</h4>" + _ul(
            f'{b.get("name", b.get("id"))}' + (f' ({b["part_number"]})' if b.get("part_number") else "")
            + (f' · library/{b["library"]}' if b.get("library") else "") + f' · {b.get("provenance", "estimated")}'
            for b in brief["bought_parts"]))
    open_q = [q for q in brief.get("open_questions", []) if not q.get("answer")]
    if open_q:
        out.append("<h4>Open questions</h4>" + _ul(q["question"] for q in open_q))
    notes = brief.get("notes", [])
    if notes:
        out.append("<h4>Your notes so far</h4>" + _ul(f'round {n.get("round", "?")}: {n["text"]}' for n in notes))
    return "".join(out)


def _inspiration(product, insp):
    pics, s = insp.get("pictures", []), insp.get("summary", {})
    if not pics and not any(s.get(k) for k in ("form", "mechanism", "materials")):
        return ""
    out = ['<h2 id="inspiration">What was taken from the inspiration</h2>']
    if s:
        out.append('<div class="cols">' + "".join(f"<div><h4>{t}</h4>{_ul(s.get(k, []))}</div>" for k, t in
                                                  (("form", "Form language"), ("mechanism", "Mechanism and function"), ("materials", "Materials and finish"))) + "</div>")
    out.append('<div class="insp">')
    for p in pics:
        f = product / p["file"]
        img = f'<img src="{data_uri(f)}" alt="{E(p.get("caption", p["file"]))}">' if f.exists() and f.stat().st_size < 3e6 else f'<p class="mut">{E(p["file"])}</p>'
        out.append(f'<div>{img}<p class="mut">{E(p.get("caption", ""))}</p>' + "".join(
            f"<h4>{t}</h4>{_ul(p.get(k, []))}" for k, t in (("form", "Form"), ("mechanism", "Mechanism"), ("materials", "Materials")) if p.get(k)) + "</div>")
    out.append("</div>")
    return "".join(out)


def _scorecard(opts, reqs):
    base = next((o for o in opts if o["id"] == "A"), None) if len(opts) > 1 else None
    out = [f'<h2 id="scorecard">{"Simplicity scorecard" if len(opts) > 1 else "Part count"}</h2><div class="scroll"><table><tr><th></th>'
           + "".join(f'<th class="n">{E(o["id"])} · {E(o["name"])}</th>' for o in opts) + "</tr>"]
    for key, label in ROWS:
        cells = ""
        for o in opts:
            v = o["scorecard"][key]
            d = v - base["scorecard"][key] if base and o is not base else 0
            cells += f'<td class="n">{v}' + (f'<span class="delta">{d:+d} vs A</span>' if d else "") + "</td>"
        out.append(f"<tr><td>{label}</td>{cells}</tr>")
    out.append("<tr><td>Processes</td>" + "".join(f'<td class="n">{E(", ".join(o["scorecard"]["processes"]) or "none")}</td>' for o in opts) + "</tr>")
    out.append("<tr><td>Envelope x × y × z (mm)</td>" + "".join(
        f'<td class="n">{" × ".join(num(o["derived"][k]) for k in ("bbox_x", "bbox_y", "bbox_z"))}</td>' for o in opts) + "</tr>")

    def tally(rs):
        bad = sum(not r["ok"] for r in rs)
        return f'<span class="{"bad" if bad else "ok"}">{len(rs) - bad} of {len(rs)}</span>' if rs else '<span class="mut">none</span>'
    out.append("<tr><td>Fit and stack-up checks passed</td>" + "".join(f'<td class="n">{tally(o["fit_results"])}</td>' for o in opts) + "</tr>")
    out.append("<tr><td>Checked musts met</td>" + "".join(
        f'<td class="n">{tally([r for r in reqs[o["id"]] if r["priority"] == "must"])}</td>' for o in opts) + "</tr>")
    out.append("</table></div>")
    return "".join(out)


def _massing(o):
    rep = o.get("massing")
    if not rep:
        return '<h4>3D massing</h4><p class="mut">Not built yet.</p>'
    if rep["option_hash"] != o["hash"]:
        return '<h4>3D massing</h4><p class="bad">Out of date: the option changed after the massing was built.</p>'
    out = [f'<h4>3D massing</h4><p>{_mark(rep["status"] == "pass")} '
           f'{"Built from the same parameters as the sketch" if rep["status"] == "pass" else "Massing checks failed"}: '
           f'envelope {" × ".join(num(v) for v in rep["bbox"])} mm, {len(rep["interference"])} interference(s).</p>']
    bad = [c for c in rep["checks"] if not c["ok"]]
    if bad:
        out.append(_ul(c["message"] for c in bad))
    shots = [(pathlib.Path(p), cap) for p, cap in rep.get("renders", []) if pathlib.Path(p).exists()]
    if shots:
        out.append('<div class="shots">' + "".join(
            f'<figure><img src="{data_uri(p)}" alt="{E(cap)} view of the massing model"><figcaption>{E(cap)}</figcaption></figure>' for p, cap in shots) + "</div>")
    return "".join(out)


def _option(o, svg, single):
    out = [f'<section class="opt" id="opt-{E(o["id"])}"><h3>{E(o["id"])} · {E(o["name"])} '
           + ('<span class="tag base">simplest baseline</span>' if o["id"] == "A" and not single else "")
           + (f'<span class="tag">merged from {E(", ".join(o["merged_from"]))}</span>' if o["merged_from"] else "") + "</h3>",
           f'<p>{E(o["summary"])}</p><dl class="arch">'
           + "".join(f'<dt>{k.replace("_", " ").capitalize()}</dt><dd>{E(str(o["architecture"][k]))}</dd>' for k in ("mechanism", "layout", "load_path", "process"))
           + f'</dl><div class="sketch">{svg}</div><div class="cols"><div><h4>Fit and stack-up</h4>']
    if o["fit_results"]:
        out.append('<div class="scroll"><table><tr><th>Check</th><th>Arithmetic</th><th class="n">Result</th><th class="n">Margin</th></tr>')
        for r in o["fit_results"]:
            out.append(f'<tr><td>{E(r["why"] or r["id"])}</td><td><code>{E(r["lhs_expr"])} {SIGN.get(r["op"], r["op"])} {E(r["rhs_expr"])}</code></td>'
                       f'<td class="n">{_check_cell(r)}</td><td class="n">{num(r["margin"])}</td></tr>')
        out.append("</table></div>")
    else:
        out.append('<p class="bad">No fit checks written for this option.</p>')
    out.append("</div><div>")
    if not single and o["id"] != "A":
        out.append("<h4>What it costs against A</h4>" + _ul(o["costs_vs_A"]))
    if o["from_inspiration"]:
        out.append("<h4>Taken from the inspiration</h4>" + _ul(o["from_inspiration"]))
    out.append("</div></div>" + _massing(o) + "</section>")
    return "".join(out)


def build(product, brief, rnd, opts, svgs, reqs, problems, insp):
    title = brief.get("title") or brief.get("product") or product.name
    single = len(opts) == 1
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>{E(title)} · round {rnd}</title><style>{CSS}</style></head><body><main>",
           f'<p class="eyebrow">Design draft · round {rnd} · {dt.date.today().isoformat()}</p><h1>{E(title)}</h1>',
           f'<p>{E(brief.get("purpose", ""))}</p>']
    if problems:
        out.append('<div class="alert"><b class="bad">This round is not ready to choose from</b>' + _ul(problems) + "</div>")
    out.append(_brief(brief, opts, reqs))
    if rnd == 1:
        out.append(_inspiration(product, insp))
    out.append(_scorecard(opts, reqs))
    out.append(f'<h2 id="options">{"The design" if single else "Options"}</h2>')
    out += [_option(o, svgs[o["id"]], single) for o in opts]
    out.append('<h2 id="moves">Your moves</h2><div class="moves">' + (
        "<div><b>Approve</b>Say so in words once the 3D massing looks right. Detailed modelling starts only then.</div>"
        "<div><b>Push back</b>Say what is wrong. Your notes become constraints and the design is redrawn.</div>"
        "<div><b>Ask for options</b>Say how many. The next round shows this design beside alternatives that differ in architecture.</div>"
        if single else
        "<div><b>Pick</b>Name one option. It gets a 3D massing model, and you approve that before detailed modelling.</div>"
        "<div><b>Merge</b>Name the pieces to combine across options. The hybrid is re-checked and redrawn as a new round.</div>"
        "<div><b>Push back</b>Say what is wrong. Your notes become constraints and a new round follows.</div>") + "</div>")
    out.append("</main></body></html>")
    return "\n".join(out)
