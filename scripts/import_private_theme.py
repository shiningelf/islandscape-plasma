#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Import a local only theme from the workspace prototype directory.

The manifest of every local theme lives next to the theme and names the
prototype files it is built from:

    {
        "prototypeDir": "prototype",
        "page": "beach-turquoise.html",
        "entry": "maldives.html",
        "scripts": ["maldives-reef.js", ...],
        "assets": ["maldives-coconut-palm-v2.png", ...]
    }

The page is adapted for the Linux port, the scripts and the images are copied
verbatim. Nothing is written into the public source tree, and the manifest
keeps the file names of a private theme out of the public scripts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def load_adapter():
    """Load adapt-theme-page.py, whose file name is not a module name."""
    spec = importlib.util.spec_from_file_location(
        "adapt_theme_page", HERE / "adapt-theme-page.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load adapt-theme-page.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["adapt_theme_page"] = module
    spec.loader.exec_module(module)
    return module


def check_javascript(page: pathlib.Path) -> None:
    """Parse the inline scripts of the page, so a broken edit cannot ship."""
    node = shutil.which("node")
    if not node:
        print("  node not found, skipping the JavaScript syntax check")
        return
    text = page.read_text(encoding="utf-8")
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S)
    with tempfile.TemporaryDirectory() as directory:
        for index, block in enumerate(blocks):
            script = pathlib.Path(directory) / f"block{index}.js"
            script.write_text(block, encoding="utf-8")
            result = subprocess.run(
                [node, "--check", str(script)], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise SystemExit(
                    f"JavaScript syntax error in {page}:\n{result.stderr.strip()}"
                )
    print(f"  JavaScript syntax check passed ({len(blocks)} inline blocks)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="source.json of a local theme")
    parser.add_argument("--workspace", default=str(ROOT.parent),
                        help="workspace that holds the prototype directory")
    args = parser.parse_args()

    manifest_path = pathlib.Path(args.manifest).resolve()
    theme_dir = manifest_path.parent
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    workspace = pathlib.Path(args.workspace).resolve()
    prototype_dir = workspace / manifest.get("prototypeDir", "prototype")
    if not prototype_dir.is_dir():
        print(f"prototype directory not found: {prototype_dir}", file=sys.stderr)
        return 1

    with open(theme_dir / "theme.json", "r", encoding="utf-8") as handle:
        theme = json.load(handle)

    adapter = load_adapter()
    sys.path.insert(0, str(HERE))
    import theme_params as tp  # noqa: E402

    params = tp.resolve_params(theme, tp.load_library())

    # --- the page ------------------------------------------------------
    source_page = prototype_dir / manifest["page"]
    if not source_page.is_file():
        print(f"prototype page not found: {source_page}", file=sys.stderr)
        return 1
    text = source_page.read_text(encoding="utf-8")
    try:
        adapted = adapter.adapt(text, params)
    except adapter.AdaptationError as error:
        print(f"adaptation failed: {error}", file=sys.stderr)
        return 1
    entry = theme_dir / manifest["entry"]
    entry.write_text(adapted, encoding="utf-8")
    print(f"  page {source_page.name} -> {entry}")
    check_javascript(entry)

    # --- scripts and assets --------------------------------------------
    for name in manifest.get("scripts", []):
        source = prototype_dir / name
        if not source.is_file():
            print(f"prototype script not found: {source}", file=sys.stderr)
            return 1
        shutil.copy2(source, theme_dir / name)
        print(f"  script {name}")

    assets = manifest.get("assets", [])
    if assets:
        asset_dir = theme_dir / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        for name in assets:
            source = prototype_dir / "assets" / name
            if not source.is_file():
                print(f"prototype asset not found: {source}", file=sys.stderr)
                return 1
            shutil.copy2(source, asset_dir / name)
            print(f"  asset assets/{name}")

    print(f"  imported {theme['id']} into {theme_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
