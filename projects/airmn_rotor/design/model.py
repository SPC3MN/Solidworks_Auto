"""airmn rotor: geometry lives in projects/airmn/airmn_parts.py (shared by all airmn parts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "airmn"))
import airmn_parts  # noqa: E402


def build(app, params):
    return airmn_parts.build(app, "rotor", params)
