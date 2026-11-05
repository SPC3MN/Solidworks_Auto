# Findings from the FreeCAD prototype

Probed on FreeCAD 1.1.4 (macOS, headless `freecadcmd`) on 2026-11-05. Recorded
here so they don't have to be rediscovered, and so it's clear what the SolidWorks
version still has to prove for itself.

## Verified in FreeCAD

- A fully constrained sketch (a rounded rectangle: 4 lines + 4 tangent arcs, with
  width, depth and radius driven by spreadsheet aliases) reported
  `FullyConstrained == True`. After changing the spreadsheet width from 100 to 120
  and recomputing, the extrusion's bounding box was 120 wide and the shape was valid.
- Sketch distance constraints accept negative values and expressions through the
  API.
- Expressions support `max(a, b)`.
- Spreadsheet alias names cannot be unit names: `rad` was rejected, and the same
  will apply to `mm`, `deg`, `in`, etc. Parameter names need checking before use.
- Mesh export to STL and 3MF worked headless.
- Without the GUI, TechDraw could create pages, views and dimensions and write DXF.
  Its PDF export needs the GUI.

## Mapping to SolidWorks (to confirm on Windows)

| FreeCAD concept | Likely SolidWorks equivalent |
|---|---|
| Spreadsheet aliases + expressions | Global Variables / Equations, or a Design Table |
| Part-workbench booleans in an App::Part | Features in a `.SLDPRT`; multibody or separate parts |
| `freecadcmd` headless scripts | SolidWorks API over COM (e.g. Python `pywin32`, or a C#/VB.NET add-in) |
| TechDraw | SolidWorks Drawings (`.SLDDRW`), which export to PDF/DXF natively |
| freecad-mcp RPC add-on | still to be decided; see open questions |

## Other notes

- PrusaSlicer 2.9.7 has a command-line interface suitable for a slicing check.
  Don't assume a printer or filament profile; make it configurable, and flag
  results produced with default settings as unconfigured.
- The prototype had planned to draw renders and fallback PDF drawings with
  matplotlib from tessellated geometry. With SolidWorks this is probably
  unnecessary, since it can save images and drawings itself.
