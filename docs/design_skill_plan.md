# Plan: the `/design` skill

Planned with the owner on 2026-11-09 (audit of the repo, then five rounds of questions). Decisions marked
**(owner)** were chosen by the owner; the rest follow from them and can be changed.

**Status (2026-11-09): build steps 1 (the drafting phase) and 2 (the kernel) are built** (sections 9 and 10). It was proven on
`products/example_pi_zero_case`, a test product whose brief and approval were written by the skill's author; a
product of the owner's has not been through it yet. Section 9 lists where the build differs from this plan.

## 1. Goal

One orchestrator skill, `/design`, in this repo's `.claude/skills/`. It takes whatever the owner has (text,
numbers, datasheets, part numbers, inspiration pictures), runs a drafting phase that ends in several distinct
options, and only after a recorded approval builds validated CAD. Later outputs are chosen stage by stage.

| Decision | Choice |
|---|---|
| Design scope **(owner)** | machined mechanical products, 3D-printed parts and enclosures, styled consumer products. Frames and fixtures (80/20) are not a target. |
| Backend **(owner)** | FreeCAD only. SolidWorks tools are frozen on a legacy branch. |
| Packaging **(owner)** | one orchestrator skill in this repo |
| Deliverables **(owner)** | chosen by the owner at each stage: validated CAD + STEP/STL, photoreal renders, manufacturing drawings, design record |
| User **(owner)** | the owner only: terse questions, engineering vocabulary, the owner's defaults assumed (simplicity first, 6061, PLA/FDM, ISO fits) |
| Main rule (standing) | the simplest design that works |

## 2. Stages and gates

```
0 Intake ─► 1 Distil ─► 2 Options (sketch boards) ─► 3 Massing ─► GATE ─► 4 Detail ─► 5 Stage menu
                              ▲        │ pick / merge / push back      │ hard approval
                              └────────┘                               ▼
                                                        any change to the brief reopens the gate
```

### Stage 0: Intake **(owner: free brief, then gap questions)**

- The owner gives anything in any form. The skill sorts every statement into `brief.json`:
  - **priority**: `must` (hard constraint), `should` (preference), `free` (the skill decides);
  - **provenance**: `given`, `measured`, `chosen`, `estimated` (the existing convention).
- Conflict check by hand arithmetic before any question (stack-ups, envelopes, parts against what holds them),
  as done on grindmn and airmn.
- **One** AskUserQuestion round, only on gaps and conflicts that change the design, recommended option first.
- Bought parts named in the brief go to the bought-parts path (section 6).

### Stage 1: Distil inspiration **(owner: form language, mechanism and function, materials and finish)**

For each picture, written to `draft/inspiration.md` and shown on the first board:

- **Form language** as measurable rules: proportions (height : diameter), edge treatment (radii, chamfers in
  mm), symmetry, visual weight.
- **Mechanism and function**: how it adjusts, closes, carries load, comes apart. These seed option
  architectures.
- **Materials and finish**: fed to the BOM and to the render material table.
- Signature details are not extracted **(owner)**. Pictures inform the design; they are not copied.

### Stage 2: The design, or options **(owner: simplest baseline + distinct concepts; parametric sketches; board page)**

- **One design per round is the default; several options are drawn only when the owner asks (owner, 2026-11-09,
  after step 1 was built: "If a very specific design is given there is no need for several options").**
  `brief.json` `"options"` holds the number. A single design goes straight to massing, and the owner sees the
  sketch and the massing together.
- With several: **A is always the fewest-parts design that meets every `must`.** The others must differ
  from A and from each other in architecture (mechanism, layout, load path or process), not only in sizes or
  styling. Each states what it costs against A.
- Each option is a parameter file, `draft/round_N/<A|B|C>/params.json`. `scripts/sketch.py` (standard library
  only) draws a dimensioned, to-scale SVG sheet from it: section through the main axis, outline views, the
  load path.
- Each option carries **(owner)**:
  - a **simplicity scorecard**: parts (make / buy), setups or print jobs, fasteners, load path, cost against A;
  - a **fit and stack-up check**: hand arithmetic that the parts fit, with every failure listed.
  - Mass, cost and strength estimates are not part of drafting; do them only when the owner asks.
- **Board**: one static HTML page per round, `draft/round_N/board.html`: options side by side with sketches,
  scorecard, fit check and what each took from the inspiration. Rounds are kept and feed the design record.
- **Owner's moves (owner)**: *pick* one, *merge* across options (the skill re-checks the hybrid and redraws
  it), or *push back with notes* (notes become constraints in `brief.json`; a new round follows). Direct
  number editing is not a supported move; dimension changes go through notes.

### Stage 3: Massing **(owner: sketch first, 3D for the shortlist; stop after massing)**

- The picked or merged option (two at most if the owner cannot choose) gets a rough 3D model built from the
  same parameter file: envelopes and interfaces only, placeholders for detail.
- Clay renders (isometric, front, right, section) go on the board next to the sketch.

### Gate: draft approval **(owner: hard gate, like render approval)**

- `design_cli.py approve <product> --quote "<owner's words>"` writes `draft/approval.json` with the hash of
  `brief.json` and the chosen option's `params.json`.
- Detail modelling refuses to run without a valid approval. Only an explicit yes counts.
- A later change to the brief or the parameters invalidates the approval for the parts it touches; the old
  approval moves to `draft/history/`.

### Stage 4: Detail

- Runs without stopping to a validated assembly: every part, the assembly, the exploded assembly, autocorrect
  (5 attempts per issue). It stops early only for a conflict that needs the owner's decision.
- The approved parameters are the only source of driving values, so the model cannot drift from the sketch.

### Stage 5: Stage menu **(owner: deliverables decided in stages)**

After stage 4 the skill reports (CAD renders, check results, open items) and offers: photoreal renders
(`product-render`, unchanged, with its own approval gate), manufacturing drawings, design record, or revise
(back to stage 2 with notes).

## 3. Validation **(owner: requirement checks, hand volume where possible)**

- Every part is checked against the approved brief: envelope, interface dimensions, hole sizes and positions.
- Prismatic and turned parts keep the exact hand-volume check. Freeform parts (loft, blend) are checked by
  envelope and by section dimensions at stated stations instead.
- **New check to build: interfaces and holes (owner).** Find cylindrical faces in the built solid, group by
  axis, compare diameter and position with the brief, and require mating parts' patterns to agree.
- Wall and printability, clearance windows and machinability checks stay unbuilt until asked for.

## 4. Geometry kernel

Styled products need more than extrude, cut, shell, round sweep and pattern. With FreeCAD as the only backend,
`fclib` can use OpenCASCADE directly. Add, in this order, each with a probe part and a recorded finding:
revolve, sketches on tilted planes, loft between sections, edge fillets and chamfers chosen by geometry, helix.

## 5. Repo layout **(owner: product folders + parts library)**

```
products/<name>/
  brief.json  brief.md          # stage 0
  references/                   # datasheets, inspiration pictures, sources.md
  draft/inspiration.md
  draft/round_N/board.html, <A|B|C>/params.json, sketch.svg, scorecard.json
  draft/massing/                # stage 3
  draft/approval.json, history/
  parts/<part>/                 # today's projects/<name>/ contents
  assembly/  assembly_exploded/
  render/  drawings/  record.md
library/<part>/                 # reusable bought parts: bearings, boards, fasteners, 80/20
```

- Repo renamed (working name `Auto_Model`); README and CLAUDE.md rewritten Linux-first.
- Existing projects migrated by script: grindmn and airmn become products and the worked examples; boards,
  bearings, PSUs, cables and 80/20 parts move to `library/`.
- Housekeeping found in the audit: decide whether `validation/history/` passes are tracked (about 150 are
  untracked now), move large binaries out of git or to LFS, add tests beyond rendering.

## 6. Existing skills **(owner: fold in as the bought-parts path)**

- `model-from-photo` becomes `references/bought-parts.md` of `/design`: replicate a real object from a part
  number, datasheet or photo, at envelope detail by default, and store it in `library/`.
- Its geometry rules and lessons move to `references/geometry.md`; FreeCAD notes stay in `references/freecad.md`.
- `product-render` stays a separate skill, called from the stage menu.
- `dimensioned-drawing` is SolidWorks-only; drawings need a FreeCAD TechDraw port before the menu can offer them.

## 7. Build order **(owner: drafting phase first)**

1. **Drafting on today's kernel.** `brief.json` schema, `scripts/sketch.py`, the board page, `design_cli.py`
   (`init`, `round`, `approve`, `status`), the massing step, the `/design` SKILL.md. New work goes straight
   into `products/<name>/`. Prove it end to end on one new product.
2. **Kernel.** Revolve, tilted planes, loft, fillets and chamfers; freeform validation by sections.
3. **Interface and hole check.**
4. **Migration and cleanup.** Move existing projects, retire SolidWorks to a legacy branch, rename the repo,
   rewrite README and CLAUDE.md.
5. **TechDraw drawings**, then the design-record generator.

## 8. Still open

- Which product of the owner's goes through the drafting phase first (the example only tested the tools).
- The repo's final name.
- Whether validation history is tracked in git.

## 9. Step 1 as built

Files: `scripts/draft_lib.py` (parameters, bodies, views, scorecard, checks, gate), `scripts/sketch.py`,
`scripts/design_board.py`, `scripts/design_cli.py`, `scripts/fc/fc_massing.py`, `.claude/skills/design/`,
`tests/test_design_unit.py` (20 tests). `pipeline.py` calls the gate; `assembly.py` finds a product's parts.

Differences from the sections above:

| Plan | As built | Why |
|---|---|---|
| Each option is `params.json` plus sketch code | `params.json` plus a declarative `option.json`: parts as lists of bodies (box, cyl, revolve, prism; add or cut) whose sizes are expressions of the parameters | one description feeds the sketch, the massing and the approval hash, so they cannot disagree |
| Fit check "by hand arithmetic" | each check is `lhs op rhs` in `option.json`, evaluated by `board` and shown with its numbers and margin | a wrong stack fails the round instead of being trusted |
| `draft/inspiration.md` | `draft/inspiration.json` | the board renders it |
| `draft/massing/` | `draft/round_N/<id>/massing/` | it belongs to one option of one round; the round's board shows it |
| "invalidates the approval for the parts it touches" | the approval stores one hash per part; a changed brief closes the gate for every part, a changed option only for the parts whose resolved bodies changed | |
| not planned | the gate also refuses a part whose own `params.json` differs from the approved draft on a shared value, and a part that is not in the approved draft | "the model cannot drift from the sketch" needed enforcing |
| not planned | `board` refuses a round where an option has fewer parts than A or two options have the same architecture text | the option rules needed enforcing |
| three options every round | one design unless `brief.json` `options` says more; `round` makes that many folders and `board` refuses fewer | owner's change, 2026-11-09 |
| not planned | `assembly.py` looks for parts in `products/<name>/parts`, then `library/`, then `projects/` | stage 4 needs it in the product layout |

Limits found while building:

- The section is always the plane y = `section_y`. A revolve whose axis is off that plane is drawn as an outline.
- The sketch applies every cut of a part to all of its adds, so adds must be listed first.
- Massing parts are single-colour clay renders on the check-view background; there is no per-part colour.
- The board embeds the massing renders, about 2 MB per massed option.

## 10. Step 2 as built (the kernel)

`scripts/fc/fclib.py` gained `plane().rotated()`, `Part.revolve`, `Part.loft` (ruled or smooth), `Part.helix`,
`Part.chamfer` and the `edges()` selector for fillets and chamfers. `scripts/handcalc.py` holds the closed-form
volumes. `pipeline.py` checks `spec.json` `"sections"` (extent and area of a cross-section at a station) and lets a
freeform part leave `volume` out. Six probe parts pass the pipeline (`projects/example_revolve`, `_tilted`,
`_loft`, `_vase`, `_edges`, `_spring`), `tests/test_kernel.py` compares 30 builds with hand values, and the
findings are in `docs/freecad_findings.md`.

Not done in this step:

- The draft's body types are unchanged (box, cyl, revolve, prism): a lofted form is still drafted as its nearest
  revolve or prism.
- Sweeps of a non-round profile, variable-radius fillets and threads. `shell` works on a smooth loft but not on a
  ruled one with kinks; lofted bodies are hollowed with a second loft as a cut.
- The existing projects were not rewritten to use the new ops.
