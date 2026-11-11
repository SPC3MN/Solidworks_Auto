# Hand-folded sheet parts (the `fold` process)

An aluminium part cut flat and folded by hand along weakened lines. Tools: `scripts/sheet_cli.py`
(`sheet_lib.py`, `fold_patterns.py`, `dxf_io.py`, `fc/fc_sheet.py`). Plan and limits: `docs/folded_enclosure_plan.md`.
Worked example: `projects/example_folded_tray`.

**No fold geometry is safe until a coupon of it has been cut and bent.** A fold whose recipe has no passing coupon
in the material profile marks every output UNTESTED. Never tell the owner a fold will hold; say what was tested.

## Three layers, kept apart

| Layer | In `sheet.json` | Knows |
|---|---|---|
| Panels | `panels`: id, `outline` (counter-clockwise polygon, mm, own frame, seen from the face that is up in the flat pattern), `features` (`circle` d/at, `rect` size/at, `slot` length/width/angle/at, `polygon` points) | shape only |
| Folds | `folds`: id, `parent` + `parent_edge`, `child` + `child_edge`, `angle`, `direction` (`up` = toward the viewer of the flat pattern, so that face becomes the inside), `sequence`, `recipe` (a name), optional `offset` along the parent's edge | where and how far, never how it is made |
| Recipes | `recipes`: name → `method` (`slots` in this release), `slot_length`, `slot_width` (0 = a slit of one kerf), `bridge`, `end_clearance`, `hinge`, `allowance`, `relief_d` | the manufacturing method |

Edge i of a panel runs from outline point i to point i + 1. A child's whole edge lies on its parent's edge, centred
unless `offset` is given. Panels form one tree from a root panel. `material` and `manufacturing` name profiles in
`libraries/sheet/`; `params` are expressions as in a draft's `params.json`, with `t` (the sheet thickness) defined.

To change how a fold is made, change its recipe. The panels and folds stay as they are.

`hinge` is where the rigid hinge sits through the thickness (0.5: bridges bend at mid-thickness). `allowance` is the
flat length a fold takes up. Both are estimates until a coupon is measured; `record` reports the measured hinge.

## Commands

```
python3 scripts/sheet_cli.py template tray <folder> --length L --width W --height H [--flange F] [--dims inside]
python3 scripts/sheet_cli.py check   <folder>     # host checks only
python3 scripts/sheet_cli.py build   <folder>     # DXF, SVG, STEP, FCStd, renders, report
python3 scripts/sheet_cli.py coupons <folder> --slot-lengths 4,8,12 --bridges 1,1.5,2
python3 scripts/sheet_cli.py record  <folder>/coupons.json --id 05 --result held --angle 90 --leg-a 30.4 --leg-b 30.5
```

`build` writes `flat/<name>[_UNTESTED].dxf` (layers `CUT_THROUGH`, `FOLD_PERFORATION`, `FOLD_DIRECTION`, `REFERENCE`),
`flat/<name>.svg`, `folded/<name>.step`, `<name>.FCStd`, `renders/` (the folded part, and one view after each folding
step) and `report.json`. Look at the SVG and the renders before reporting.

## The three verdicts

Report them separately, always, in these words:

- **geometrically valid**: one tree; features inside their panels; the flat pattern does not overlap itself and is
  one piece; folded panels do not collide; every folding step can be carried out; the DXF reads back as written.
- **manufacturable**: slot width, bridge, uncut ends, material round holes, hole size, panel depth to grip, each
  against the manufacturing profile. With `generic_untested` this only means "passes placeholder limits": say so.
- **experimentally validated**: every fold's recipe matches a coupon that held, in this material, at this angle.

## Coupons

`coupons` writes a sheet of numbered strips, one fold each, sweeping slot length and bridge. The owner cuts them,
folds each by hand with the numbered end held flat, and fills in `coupons.md`. Enter each line with `record`: it
goes into the material profile, and a recipe within 10 % of a coupon that held then counts as tested.

## In a /design draft

A part with `"sheet": "<file in the option folder>"` and no `bodies` is a folded part: its folded panels become
its bodies (the sketch, fit checks and massing work as for any part), the board shows its flat pattern, each fold
counts as one setup, and `at` places it. The option's parameters override the sheet's of the same name, so name
the driving sizes the same in both (`L`, `W`, `H` in the tray template).

After approval: `design_cli.py params <product> --part <id>` writes `parts/<id>/sheet.json` with the approved
values, then `sheet_cli.py build products/<name>/parts/<id>`. The gate refuses the build when a shared parameter,
a panel or a fold differs from the approved draft. A recipe may be changed at this stage.

## Limits of this release

- One fold method: straight slots in one row. Grooves, staggered and curved patterns are not built.
- A draft can only show folds in 90° steps; `build` handles any angle.
- Panels joined by a fold are not checked against each other for collision (a rigid mid-thickness hinge always
  overlaps its neighbour by a sliver). Everything else is.
- Features must lie inside a panel; a notch in an edge is drawn as part of the outline.
- No exploded view, no PDF drawing, no CAM.
