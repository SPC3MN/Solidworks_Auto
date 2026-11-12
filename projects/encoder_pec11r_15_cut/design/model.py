"""Rotary encoder, built from parameters/params.json by scripts/encoder_build.py."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import encoder_build  # noqa: E402


def build(app, params):
    return encoder_build.build(app, params)
