# /design file formats

Everything is JSON, UTF-8, mm. Keys starting with `_` are notes: they are ignored and never affect a hash.
The code that reads these files is `scripts/draft_lib.py`; a complete set is in
`products/example_pi_zero_case/`.

```
products/<name>/
  brief.json                      stage 0
  references/                     datasheets, sources.md, inspiration/<pictures>
  draft/inspiration.json          stage 1
  draft/round_N/<id>/params.json, option.json      you write these
  draft/round_N/<id>/sketch.svg, scorecard.json    written by `board`
  draft/round_N/<id>/massing/     written by `massing`: massing.step, report.json, renders/
  draft/round_N/board.html, round.json
  draft/log.json                  every pick, merge, push-back and approval, with the owner's words
  draft/approved/, approval.json  written by `approve`; earlier approvals move to draft/history/
  parts/<part id>/                stage 4: parameters/, design/, validation/, exports/, renders/
  assembly/assembly.json          stage 4
```

## brief.json

```json
{
  "product": "hand_grinder", "title": "Hand grinder", "purpose": "One sentence: what it is for.",
  "options": 1,
  "defaults": {"machined": "6061-T6", "printed": "PLA, FDM", "fits": "ISO 286"},
  "requirements": [
    {"id": "R1", "text": "Fits a 70 mm cup holder", "priority": "must", "provenance": "given",
     "source": "owner, 2026-11-09", "check": {"lhs": "bbox_x", "op": "<=", "rhs": 70}}
  ],
  "bought_parts": [{"id": "burr", "name": "48 mm conical burr set", "part_number": "", "library": null, "provenance": "estimated"}],
  "conflicts": [{"text": "450 pack + 120 cap is not the stated 670", "resolution": "owner: 570 overall (2026-11-09)"}],
  "open_questions": [{"question": "...", "answer": null}],
  "notes": []
}
```

- `options`: how many designs each round draws. 1 by default; set it to the number the owner asks for (3 when they
  say "options" without a number). It is not part of the approval, so it can change at any time.
- `priority`: `must` | `should` | `free`. `provenance`: `given` | `measured` | `chosen` | `estimated`.
- `check` is optional: `lhs`, `op` (`<=` `<` `>=` `>` `==`), `rhs`, each a number or an expression. It may use any
  parameter of the option being checked, plus `bbox_x`, `bbox_y`, `bbox_z`, `parts_total`, `parts_make`, `parts_buy`,
  `fasteners`, `setups`. A check that names a parameter an option lacks fails for that option, so prefer the derived names.
- A failed `must` blocks the round; a failed `should` is only shown.
- The approval binds `requirements`, `bought_parts` and `defaults`. `notes`, `open_questions` and `conflicts` can change freely.
- `decide --move pushback` appends the owner's words to `notes`; you then turn them into requirements.

## draft/inspiration.json

```json
{
  "pictures": [{"file": "references/inspiration/mill.jpg", "caption": "Peugeot pepper mill",
                "form": ["height : diameter 2.8", "waist at 40 % of the height"],
                "mechanism": ["grind set by a nut on the shaft top"],
                "materials": ["turned beech, satin lacquer"]}],
  "summary": {"form": ["..."], "mechanism": ["..."], "materials": ["..."]}
}
```

`file` is relative to the product folder. The board shows it in round 1.

## params.json (one per option)

```json
{
  "tube_od": {"value": 64, "src": "given", "note": "owner"},
  "wall": 2.0,
  "bore": "tube_od - 2*wall",
  "burr_od": {"value": 54, "src": "estimated", "note": "until the burr set is measured"}
}
```

A value is a number or an expression of other parameters (`+ - * / ** %`, `min max abs sqrt sin cos tan atan2
radians degrees floor ceil`, `pi`), in any order. A bare value has `src` `chosen`. The sketch prints a dimension
bold when its parameter is given or measured, and italic with `~` when estimated.

## option.json (one per design; the folder name is its id, `A` for a single design)

```json
{
  "name": "Slide-in sleeve",
  "summary": "One or two sentences the owner reads first.",
  "architecture": {"mechanism": "...", "layout": "...", "load_path": "board -> ledges -> floor -> desk", "process": "..."},
  "parts": [
    {"id": "sleeve", "name": "Sleeve", "source": "make", "process": "print", "material": "PLA", "setups": 1,
     "bodies": [
       {"type": "box", "size": ["inner_l + wall", "outer_w", "outer_h"], "at": ["-wall/2", 0, 0]},
       {"type": "box", "op": "cut", "size": ["inner_l + poke", "inner_w", "inner_h"], "at": ["poke/2", 0, "wall"]}]},
    {"id": "screw", "name": "M2.5 × 10", "source": "buy", "fastener": true,
     "bodies": [{"type": "cyl", "d": 2.5, "h": 10, "at": [0, 0, 0]}],
     "instances": [["hole_dx/2", "hole_dy/2", 0], ["-hole_dx/2", "hole_dy/2", 0]]}
  ],
  "load_path": [{"part": "board", "at": [0, "z_b"]}, {"part": "sleeve", "at": [0, "wall/2"]}, {"part": "sleeve", "at": [0, -4]}],
  "dims": [{"view": "section", "dir": "v", "a": 0, "b": "wall", "at": "inner_l/2 + 7", "param": "wall"}],
  "fit": [{"id": "roof", "lhs": "z_b + pcb_t + comp_h", "op": "<", "rhs": "outer_h - wall", "why": "Components clear the roof"}],
  "costs_vs_A": ["+1 printed part", "needs a screwdriver"],
  "from_inspiration": ["2 mm outside chamfers (mill.jpg)"],
  "allowed_interference": [["base", "screw", "thread engagement: M2.5 in a Ø2.1 tap hole"]],
  "merged_from": ["1:A", "1:C"],
  "section_y": 0
}
```

### Parts

| Key | Meaning |
|---|---|
| `id` | snake_case; becomes the folder `parts/<id>/` in stage 4 |
| `source` | `make`, `buy` or `library` (a part that exists in `library/` or `projects/`; name it in `library`) |
| `process`, `material`, `setups` | for made parts; `setups` is lathe or mill setups, or print jobs (default 1) |
| `fastener` | true for screws, nuts, clips, pins: counted on the scorecard |
| `qty` | defaults to the number of `instances` |
| `instances` | offsets `[x, y, z]`; the bodies are drawn once per instance (default one, at the origin) |

Count every part that has to exist, including standard hardware. Leaving parts out to make A look simple defeats the scorecard.

### Bodies

Axes: z up. The section is the plane y = `section_y`, seen from −y, so lay the product out with its main axis in
the x-z plane (turned parts about z, long products along x). List every `add` before the `cut`s: a cut applies to
the whole part. A cut may poke past the surface it opens (`+ poke`), and should, so no skin is left.

| `type` | Fields | `at` is |
|---|---|---|
| `box` | `size` [x, y, z], `r` (corner radius about z, optional) | the centre of the bottom face |
| `cyl` | `d`, `h`, `axis` (default `z`), `bore` (through, optional) | the centre of the start face; it extends toward +axis |
| `revolve` | `profile` [[radius, along-axis], …] closed, `axis` (default `z`) | the point on the axis where along-axis = 0 |
| `prism` | `profile` [[a, b], …] closed, `h`, `axis` (default `z`) | an offset; profile coordinates are (x, y) for axis z, (x, z) for y, (y, z) for x; extends toward +axis |

Reading the sketch: hatched = cut by the section plane; grey = bought; thin outline = behind the plane; dashed =
hidden or removed. A revolve whose axis is off the section plane is drawn as an outline, not cut.

### Dims

Overall length, width and height are drawn automatically (above and left of the views). Add the dimensions the
owner needs to judge the option: interfaces, wall thicknesses, the given sizes.

`view`: `section` (x, z), `right` (y, z) or `top` (x, y). `dir`: `h` or `v`. `a`, `b`: the two ends along that
direction. `at`: where the dimension line sits on the other axis (outside the outline reads best; below or to the
right, since the automatic ones are above and left). Optional: `param` (takes its provenance), `text` (replaces
the number), `dia` (adds Ø), `from` (where the extension lines start).

### Load path

A list of part ids, or `{"part": id, "at": [x, z]}` to place the node (do this when part centres coincide).
End it below the product to show where the load goes to ground.

### Fit checks

`lhs`, `op`, `rhs`, `why`, optional `id` and `tol` (for `==`). Both sides are evaluated and shown with the margin.
Write a check for every way the design could fail to go together: each stack along the main axis, each clearance
between a moving and a fixed part, each part passing through an opening during assembly, each thread engagement.
A check whose two sides are the same expression proves nothing; compare a part with what holds it.

## What `board` enforces

- every option loads (parameters resolve, bodies are valid, part ids are unique, architecture has all four keys);
- every option has fit checks, and all pass;
- every checked `must` passes for every option;
- the round has as many options as `brief.json` `options` asks for (a merge round, with `merged_from`, may hold one);
- with two or more options: there is an A, no option has fewer parts than A, and no two options have the same architecture text;
- the brief has no unresolved conflict.

## What `massing` checks

- the 3D envelope equals the sketch's on each axis (0.01 mm);
- every part is one valid solid;
- no two part instances overlap, except pairs in `allowed_interference`.
