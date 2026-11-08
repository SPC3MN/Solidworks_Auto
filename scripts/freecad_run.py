"""Find FreeCAD and run a script inside it headless (FreeCADCmd), from any Python.

FreeCAD is found, in order, from:
  1. the FREECAD_CMD environment variable (a file, or "flatpak" for the Flatpak build)
  2. config/render.local.json  {"freecad": ".../FreeCADCmd.exe"}   (gitignored, per machine)
  3. ~/Tools/FreeCAD*/bin, Program Files/FreeCAD*/bin, /Applications/FreeCAD.app
  4. freecadcmd / FreeCADCmd on PATH
  5. the Flatpak org.freecad.FreeCAD (Linux)

Arguments go to the script as one JSON value in an environment variable, because FreeCADCmd
treats extra command-line words as files to open. The Flatpak sandbox inherits neither the
host environment nor /tmp, so both are passed in explicitly (--env, --filesystem=/tmp).
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "config" / "render.local.json"
FLATPAK_ID = "org.freecad.FreeCAD"


def local_config():
    try:
        return json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def flatpak_installed():
    fp = shutil.which("flatpak")
    if not fp:
        return False
    return subprocess.run([fp, "info", FLATPAK_ID], capture_output=True).returncode == 0


def freecad_cmd():
    """Command prefix that runs FreeCADCmd, as a list, or None when FreeCAD is not found."""
    cands = [os.environ.get("FREECAD_CMD"), local_config().get("freecad")]
    home = pathlib.Path.home()
    for base in (home / "Tools", pathlib.Path(r"C:\Program Files"), pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"):
        for exe in ("FreeCADCmd.exe", "freecadcmd.exe", "FreeCADCmd", "freecadcmd"):
            cands += sorted(glob.glob(str(base / "FreeCAD*" / "bin" / exe)), reverse=True)
    cands += ["/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd", shutil.which("freecadcmd"), shutil.which("FreeCADCmd")]
    for c in cands:
        if c == "flatpak":
            return ["flatpak", "run", "--command=FreeCADCmd", FLATPAK_ID]
        if c and pathlib.Path(c).is_file():
            return [str(c)]
    if flatpak_installed():
        return ["flatpak", "run", "--command=FreeCADCmd", FLATPAK_ID]
    return None


def describe(cmd):
    return " ".join(cmd)


def run(script, env_name, args, timeout=3600):
    """Run `script` in FreeCADCmd with json(args) in $env_name. Returns (CompletedProcess, cmd)."""
    cmd = freecad_cmd()
    if cmd is None:
        raise FileNotFoundError("FreeCAD not found. Set FREECAD_CMD (a FreeCADCmd path, or 'flatpak') or "
                                "config/render.local.json {\"freecad\": \".../FreeCADCmd\"}.")
    value = json.dumps(args)
    env = dict(os.environ, **{env_name: value})
    full = list(cmd)
    if cmd[0] == "flatpak":
        full[2:2] = ["--filesystem=/tmp", f"--env={env_name}={value}"]
    proc = subprocess.run([*full, str(script)], env=env, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    return proc, cmd
