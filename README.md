# Solidworks_Auto

An autonomous, agent-driven CAD environment: describe a product or enclosure in
natural language and have an AI agent (Claude Code) plan, model, validate, correct
and export it, using **SolidWorks on Windows** as the CAD kernel.

## Status

Early planning. This project replaces an earlier FreeCAD/macOS prototype
("Agentic-CAD"), which was stopped before any modelling code was written. What
carries over is the architecture and the lessons from probing that prototype:

- [docs/architecture.md](docs/architecture.md): the workflow, directory layout,
  build/validate/promote pipeline, validation checks and the autocorrection loop.
  None of this depends on which CAD program is used.
- [docs/freecad_prototype_findings.md](docs/freecad_prototype_findings.md): what
  was actually verified in the FreeCAD prototype, and which of those ideas map to
  SolidWorks.
- [docs/solidworks_open_questions.md](docs/solidworks_open_questions.md): things
  to investigate on the Windows machine before writing code.

Nothing in this repository has been tested against SolidWorks yet.
