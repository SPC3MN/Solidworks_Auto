"""RCA audio cable with plug, local origin at the socket barrel tip. Built by scripts/cable_build.py from parameters/params.json."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import cable_build  # noqa: E402


def build(app, p):
    return cable_build.build(app, p)