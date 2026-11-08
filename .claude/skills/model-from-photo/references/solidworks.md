# Backend: SolidWorks 2025 (COM via pywin32)

Status: in use. Every contract item is implemented and verified. Full API notes:
[docs/solidworks_findings.md](../../../../docs/solidworks_findings.md). Read them before changing scripts.

## Setup and commands

- SolidWorks must be running. Python is `.venv\Scripts\python` (pywin32, late binding). Units in the API are metres.
- Part build: `scripts/swlib.py` (`Part.extrude / cut / shell / fillet / sweep / circular_pattern`, profiles
  `rect / circle / polygon / slot / path`). Geometry modules call `swlib.Part` from their `build()`.
- Pipeline: `.venv\Scripts\python scripts\pipeline.py projects\<name>` (native `.SLDPRT`, STEP re-opened in
  SolidWorks, STL checked in pure Python).
- Assembly: `.venv\Scripts\python scripts\assembly.py assemblies\<name>` (`.SLDASM`, interference detection with
  coincidence not counted, STEP, renders, wireframe).
- Also SolidWorks-only today: `board_build.py`, `cable_build.py`, `encoder_build.py`, `drawing.py`
  (dimensioned-drawing skill), `asm_capture.py` / `asm_simplify.py` / `frame_check.py` (80/20 simplification).
- Only extrusion depths and shell thickness are linked to global variables, so editing them in the GUI rebuilds
  the model. Other changes need a rerun of `model.py`.

## Sketch and feature rules

- **A sketch is rejected when its lines partly overlap existing model edges** (the feature returns None).
  Offset the profile 0.05 to 0.6 mm so its edges either match an edge exactly or stay clear of it. Example: a
  blade tab as wide as the blade body had to be made 2.6 instead of 3.0.
- **Blind cuts default to going against the plane normal**, the opposite of extrudes. `swlib.cut` handles it with
  `down`; module ops always cut toward +axis.
- Plane maps: Front Plane (z) is (x, y); Top Plane (y) maps (x, z) to sketch (x, −z); Right Plane (x) maps (y, z)
  to sketch (−z, y).
- **Select the new sketch explicitly before each feature call**, or a stale selection builds the wrong feature.
- **Fillets:** an EDGE pick on an inside corner failed; a FACE pick on the adjoining floor works. Picking 48 small
  circle edges rounded only 12; picking each top face rounded 46. `board_build` re-checks face areas and rounds
  the misses in a `_fix` feature.
- **Circular pattern:** axis from Top Plane × Right Plane (`InsertAxis2`), axis mark 1, features mark 4,
  `FeatureCircularPattern4(n, 2π, False, "NULL", True, True, False)`. Exact on 2128 holes.
- A self-crossing profile makes `FeatureCut4` return None with no other message.

## Running, failures and tidiness

| Failure | Cause and fix |
|---|---|
| Native file is 0 bytes | Rerun the pipeline. |
| STL or renders show a different part | Another process drove SolidWorks and stole focus. The pipeline activates by path and fails the export instead; rerun. Re-render a promoted part by opening it, activating it, checking `ActiveDoc` and calling `swlib.render`. |
| `could not insert <part>` in an assembly | A leftover document with the same file name is open (from a failed run). Close it and rerun. |
| "The object invoked has disconnected from its clients" | SolidWorks went away mid-batch; every later part fails too (`<unknown>.GetTitle`). Rerun from the first failed part once it answers. |
| A build takes over 5 minutes, or listing documents times out | SolidWorks is hung (seen after about 16 h of builds). Check `Get-Process SLDWORKS` (`Responding`), stop your own Python processes, and ask the user before force-quitting: unsaved work in other documents is lost. After a restart, wait until `RevisionNumber` answers. |

- `timeout` on a heavy part (the 63 MB STEP band) killed it during the STEP re-import and left two copies open.
- List open documents with `app.GetFirstDocument` and `doc.GetNext` (properties under late binding, no `()`),
  close your own with `app.CloseDoc(title)`. Never call `CloseAllDocuments`. Other sessions may be using
  SolidWorks at the same time (x8020 parts kept opening on grindmn); never close their documents.
- `SaveAs3` fails silently if another open document holds the target path; close it first.

## Simplify an existing assembly (vendor CAD too heavy to render)

1. Run `.venv\Scripts\python scripts\asm_capture.py <source.SLDASM> assemblies\<name> --interference`. It opens the source read-only.
2. Map every source part in `assemblies/x8020_map.json` to a `kind` and `type` (profile, bracket, fastener, plate or bearing; builders in
   `scripts/x8020_parts.py`) or to `keep`. Rebuild every catalog part so all assemblies share the same geometry.
3. Run `asm_simplify.py gen ...`, then `pipeline.py` on the new projects, then `frame_check.py --scratch <scratchpad>`.
4. Run `asm_simplify.py assemble assemblies\<name>`, then `assembly.py assemblies\<name>`. It checks the component count, the original
   bbox, no new interference against the original, and the face count before and after.
5. Never modify the source files.
