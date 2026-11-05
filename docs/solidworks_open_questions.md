# Open questions for the SolidWorks / Windows build

To investigate on the target machine before writing code. None of these have been
researched yet.

1. **Version and licence**: which SolidWorks version and edition is installed,
   and does the licence allow API automation?
2. **Integration route**: is there a maintained SolidWorks MCP server, or should
   one be built? Options include a Python MCP server driving SolidWorks over COM
   (`pywin32`), or a C# add-in that exposes a local endpoint. Check what exists
   before building anything.
3. **Persistent session**: attach to a running SolidWorks instance rather than
   starting a new one for each call, and work out how to handle modal dialogs that
   block automation.
4. **Parameter binding**: decide between Global Variables/Equations and Design
   Tables for keeping `params.json` in sync with the model.
5. **Exports**: confirm STEP, STL and 3MF export settings (units, tessellation
   tolerance) through the API, plus PDF/DXF export of drawings.
6. **Geometry queries for validation**: what the API offers for faces, normals,
   ray casting, minimum distance and interference detection (SolidWorks has its
   own Interference Detection), versus doing these checks on an exported STEP
   with an independent kernel such as build123d/OCP. An independent check has the
   advantage of also exercising export integrity.
7. **Toolchain on Windows**: Python and uv, git, Claude Code, PrusaSlicer
   (`prusa-slicer-console.exe` for the command line).
