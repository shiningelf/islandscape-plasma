#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build one Islandscape Plasma wallpaper package from a theme directory.

A theme directory holds

    theme.json      the parameter specification and the package identity
    metadata.json   optional, overrides packaging/metadata-<id>.json
    <entry>.html    the theme page and any file it loads relative to itself

Everything else in the directory is copied into the package next to the theme
page, so a theme that ships its own scripts and images stays self contained.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import theme_params as tp  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENDOR_PROTOTYPE = ROOT / "vendor" / "Deskland" / "prototype"


def read_json(path: pathlib.Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(source: pathlib.Path, target: pathlib.Path) -> None:
    if not source.is_file():
        raise SystemExit(f"missing theme file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="theme directory")
    parser.add_argument("--output", required=True, help="package directory")
    parser.add_argument("--metadata", default="", help="fallback metadata.json")
    args = parser.parse_args()

    source = pathlib.Path(args.source).resolve()
    output = pathlib.Path(args.output).resolve()
    theme = read_json(source / "theme.json")

    library = tp.load_library()
    params = tp.resolve_params(theme, library)
    theme_id = theme["id"]
    package_id = theme["packageId"]
    if output.name != package_id:
        raise SystemExit(f"package directory {output.name} does not match {package_id}")

    # --- metadata -------------------------------------------------------
    metadata_source = source / "metadata.json"
    if not metadata_source.is_file() and args.metadata:
        candidate = pathlib.Path(args.metadata)
        if candidate.is_file():
            metadata_source = candidate
    if not metadata_source.is_file():
        raise SystemExit(f"no metadata.json for theme {theme_id}")
    write_text(output / "metadata.json", metadata_source.read_text(encoding="utf-8"))

    # --- wallpaper host -------------------------------------------------
    template = (ROOT / "src" / "linux" / "main.qml.in").read_text(encoding="utf-8")
    rendered = template.replace("@THEME_ID@", theme_id)
    rendered = rendered.replace("@THEME_FILE@", theme["entry"])
    rendered = rendered.replace(
        "@THEME_PARAMS_JSON@", tp.qml_literal(tp.resolve_params(theme, library))
    )
    rendered = rendered.replace(
        "@THEME_PARAM_SPEC_JSON@", tp.qml_literal(tp.page_spec(params))
    )
    rendered = rendered.replace(
        "@THEME_CONFIG_VALUES@", tp.config_binding(params)
    )
    for placeholder in ("@THEME_ID@", "@THEME_FILE@", "@THEME_PARAMS_JSON@",
                        "@THEME_PARAM_SPEC_JSON@", "@THEME_CONFIG_VALUES@"):
        if placeholder in rendered:
            raise SystemExit(f"unresolved placeholder {placeholder}")
    write_text(output / "contents" / "ui" / "main.qml", rendered)

    # --- configuration --------------------------------------------------
    write_text(output / "contents" / "ui" / "config.qml", tp.render_config_qml(params))
    write_text(output / "contents" / "config" / "main.xml", tp.render_config_xml(params))

    # --- theme payload --------------------------------------------------
    theme_out = output / "contents" / "themes" / theme_id
    theme_out.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir()):
        if item.name in ("theme.json", "metadata.json", "source.json"):
            continue
        if item.is_dir():
            shutil.copytree(item, theme_out / item.name, dirs_exist_ok=True)
        elif item.is_file():
            copy_file(item, theme_out / item.name)
    for relative in theme.get("vendorFiles", []):
        copy_file(VENDOR_PROTOTYPE / relative, theme_out / relative)

    entry = theme_out / theme["entry"]
    if not entry.is_file():
        raise SystemExit(f"theme entry {theme['entry']} is missing from {theme_out}")

    print(f"  theme {theme_id}: {len(params)} parameters, entry {theme['entry']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
