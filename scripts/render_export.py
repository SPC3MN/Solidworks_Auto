"""Export a CAD product for rendering (kept for older commands; render_cli.py export is the same).

    .venv\\Scripts\\python scripts\\render_export.py assemblies\\grindmn [--exploded-from assemblies\\grindmn_exploded]
    .venv\\Scripts\\python scripts\\render_export.py path\\to\\product.FCStd
    .venv\\Scripts\\python scripts\\render_export.py path\\to\\product.step --out some\\folder

The adapter is picked from the file type (scripts/render_adapters/__init__.py).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import render_adapters  # noqa: E402


def run(target, out_folder=None, exploded_from=None, explode_axis="z", ap242=False, **options):
    return render_adapters.export(target, out_folder, exploded_from=exploded_from, explode_axis=explode_axis,
                                  ap242=ap242, **options)


if __name__ == "__main__":
    import render_cli
    render_cli.main(["export", *sys.argv[1:]])
