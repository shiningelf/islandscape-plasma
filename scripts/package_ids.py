#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Print the package id of every theme of this project.

Both the public themes and the local only themes are listed, one id per line.
The scripts that install, restore or remove the wallpapers use this list
instead of repeating the ids.
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEME_DIRS = [ROOT / "src" / "themes", ROOT / "local-private" / "themes"]


def main() -> int:
    for base in THEME_DIRS:
        if not base.is_dir():
            continue
        for theme_dir in sorted(base.iterdir()):
            manifest = theme_dir / "theme.json"
            if not manifest.is_file():
                continue
            with open(manifest, "r", encoding="utf-8") as handle:
                print(json.load(handle)["packageId"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
