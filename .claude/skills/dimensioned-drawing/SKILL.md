---
name: dimensioned-drawing
description: Make a dimensioned 2D engineering drawing (SLDDRW + PDF + PNG) of a part in this repo, with third-angle Z-up views, a title block, and every dimension checked against the requirements. Use when the user asks for a drawing, a dimensioned drawing, a print, a 2D or a spec sheet of a part (e.g. "give me a drawing of the Pi 5", "dimension the HAT"), or after modelling a part when they want one.
---

# Dimensioned drawing of a part

`scripts/drawing.py` builds a drawing from `projects/<name>/drawing/drawing.json`. The part must already
be promoted (`design/<name>.SLDPRT`, with a passing pipeline report). Run Python as `.venv\Scripts\python`.

```
.venv\Scripts\python scripts\drawing.py projects\<name>
```

## What the script does for you

- **Views.** It saves Z-up named views (`Z_front`, `Z_top`, `Z_right`, `Z_isometric`) into the part,
  because the stock SolidWorks views assume Y is up. They are laid out in third angle:
  - the front elevation looks along +y, with x to the right and z up;
  - the top (plan) view sits above it;
  - the right view (looking along −x, y to the right) sits to the right of the front view;
  - the isometric view goes top right, at half scale if needed.
- **Scale and sheet.** The scale is the largest standard one that fits the views and room for
  dimensions on an A3 sheet (`"sheet": [420, 297]`): 10, 5, 4, 2 or 1 to 1, or 1:2, 1:4, 1:5 or 1:10.
  The sheet itself stays at 1:1. It draws the border and title block (title, project, source,
  scale, units, projection, date) and the notes.
- **Picking edges.** It selects each picked edge by mapping its model point (mm) through
  `View.ModelToViewTransform` to the sheet. It tries a model edge first, then a silhouette.
- **Checking values.** It reads back the value SolidWorks measured and compares it with `expect`
  (default tolerance 0.01 mm). A wrong pick shows up as a wrong number (an angle, a neighbouring
  edge) or as `no edge at pick`.
- **Output.** It writes `drawing/<name>.SLDDRW|.pdf|.png` and `drawing/history/<stamp>.json`, and closes everything it opened.

## Writing drawing.json

```json
{
  "title": "Raspberry Pi 5 - envelope",
  "source": "RPi mechanical drawing + photo (see requirements.md)",
  "dims": [
    {"label": "PCB length", "view": "top", "pick": [[0, 40, 1.6], [85, 38, 1.6]], "kind": "h", "side": "above", "expect": 85.0},
    {"label": "hole dia (4x)", "view": "top", "pick": [[4.85, 52.5, 1.6]], "expect": 2.7}
  ],
  "notes": ["All dimensions in mm", "Outline and holes: given", "Heights: estimated"]
}
```

- `pick` lists 1 or 2 points in model mm that lie **on** an edge.
  - Two parallel lines give their distance.
  - A circle and a line give the distance from the centre to the line.
  - Two circles give the distance between centres; use `kind` `h` or `v` to fix the direction.
  - One circle gives its diameter.
- `expect` comes from `requirements.md` (given, measured or estimated values). Never take it from a
  SolidWorks run: the check is only worth something if the number comes from somewhere else.
- `side` is `left`, `right`, `above` or `below` for linear dimensions. Diameters are placed automatically.

### What to dimension: general dimensions and holes only

This is the user's rule for parts they send as photos or part numbers. The drawing gives what is
needed to design fasteners and enclosures, and nothing more:

1. Overall size: length and width in the top view, overall height in the front view, overhangs included where they can be picked.
2. Mounting holes: pitch in x and y, the first hole's distance from an edge, and the diameter labelled "(4x)".
3. Board or plate thickness, which sets fastener and standoff lengths.

**Don't dimension ports and features**: RCA, USB-C, HDMI, jacks, headers, lens tubes, bores or chips.
Their envelope is already inside the overall size. Add one only if the user asks for it.
That usually comes to 5 to 8 dimensions.

### Pick rules (learned on standoff, rpi5, rpi_dac_hat, rpi_hq_camera)

- **Stay at least 1 to 2 mm (model) away from any other edge parallel to the one you want.**
  Otherwise the pick lands on the neighbour. Examples:
  - The camera's knurled ring sits 0.5 mm inside the board edge, so pick the board edge near a corner.
  - The camera's bottom edge sits 1 mm from its top edge, so that pick measured to the top edge.
  If several edges are close together, measure to a clearly separate one and change `expect` to match.
- **Pick where nothing covers the edge in that view.** For example, the Pi 5's right edge
  is only visible at y = 38, in the gap between the USB stacks. Check the layout for overhanging parts.
- **Circles seen edge-on can't be selected.** A barrel end seen from the side or from above selects
  the whole view instead. Dimension a cylinder in the view where it looks round (a diameter, or
  centre-to-centre spacing). Leave out lengths that can only be measured to an edge-on circle,
  and say so in `_comment`.
- **Pick each diameter at a different angle on its circle** (45°, 135°, 225°, ...). Each label
  leaves the view in the direction of its pick, so labels picked at the same angle collide.
- **Never use a side whose gap another view shares:** `top/below`, `front/above`, `front/right`
  and `right/left`. The script refuses to run if you do. Put front-view dimensions on the left or
  below, and top-view dimensions above, left or right.
- Within a side, the script stacks shorter dimensions nearer the part.

## Loop

1. Write `drawing.json`. Explain the pick choices in `_comment`.
2. Run the script. For each `FAIL`:
   - an angle, or a neighbour's value → move the pick away from nearby edges;
   - `no edge` → the edge is covered, or it is an edge-on circle;
   - a real mismatch → the model or the requirements are wrong. Report it; don't change `expect` to fit the model.

   Make at most 5 attempts per dimension.
3. Look at `drawing/<name>.png` for overlapping text, dimensions crossing views, or a missing view, and fix them.
   The PNG is low resolution; the PDF is the deliverable.
4. Send the PDF (and the PNG preview) with SendUserFile. Report the check count (for example 9/9),
   the scale, which values are estimates, and anything left undimensioned and why.
