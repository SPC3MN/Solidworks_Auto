"""grindmn screw_m4x6: geometry lives in projects/grindmn/grindmn_parts.py (shared by all grindmn parts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "grindmn"))
import grindmn_parts  # noqa: E402


def build(app, params):
    return grindmn_parts.build(app, "screw_m4x6", params)
