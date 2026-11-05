"""Model script for example_box: a parameter-linked solid block.

The pipeline calls build(app, params) and gets back the open SolidWorks document.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import sw_params  # noqa: E402


def build(app, params):
    model, _info = sw_params.build(app, params)
    return model
