"""Paths and software locations for the Blender rendering pipeline.

Nothing here is hard-coded to one machine. Blender is found, in order, from:
  1. the BLENDER_EXE environment variable
  2. config/render.local.json  {"blender": "C:/.../blender.exe"}   (gitignored, per machine)
  3. ~/Tools/blender-*/blender[.exe] (newest), then Program Files/Blender Foundation/*/blender.exe
  4. `blender` on PATH
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "libraries" / "render"
BLENDER_SCRIPTS = ROOT / "scripts" / "blender"
LOCAL_CONFIG = ROOT / "config" / "render.local.json"
MIN_BLENDER = (5, 1)  # the STEP Importer extension needs Blender 5.1 or newer


def local_config():
    try:
        return json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def blender_exe():
    cands = [os.environ.get("BLENDER_EXE"), local_config().get("blender")]
    home = pathlib.Path.home()
    for exe in ("blender.exe", "blender"):
        cands += sorted(glob.glob(str(home / "Tools" / "blender-*" / exe)), reverse=True)
    cands += sorted(glob.glob(r"C:\Program Files\Blender Foundation\*\blender.exe"), reverse=True)
    cands.append(shutil.which("blender"))
    for c in cands:
        if c and pathlib.Path(c).is_file():
            return pathlib.Path(c)
    return None


def render_dir(folder):
    """Render workspace of an assembly or part folder (assemblies/<name> or projects/<name>)."""
    return pathlib.Path(folder) / "render"


LAYOUT = {
    "geometry": "export/geometry",
    "manifest": "export/product_manifest.json",
    "blender": "blender",
    "previews": "previews",
    "final": "final",
    "materials": "materials",
    "settings": "settings",
    "reports": "reports",
}


def path(folder, key):
    return render_dir(folder) / LAYOUT[key]


def blender():
    exe = blender_exe()
    if exe is None:
        sys.exit("Blender not found. Set BLENDER_EXE or config/render.local.json (see docs/rendering.md).")
    return exe


def run_blender(script, *args, timeout=None):
    """Run scripts/blender/<script> headless; echo its [render] lines and errors. Returns (code, output)."""
    cmd = [str(blender()), "-b", "-noaudio", "--python-exit-code", "1", "--python", str(BLENDER_SCRIPTS / script), "--", *map(str, args)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    keep = []
    for line in proc.stdout:
        if line.startswith("[render]") or "Error" in line or "Traceback" in line or line.startswith("  File") or keep and keep[-1].startswith("  File"):
            print(line.rstrip(), flush=True)
        keep.append(line)
    proc.wait(timeout=timeout)
    return proc.returncode, "".join(keep)
