#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check that the local only themes stay out of the public source and packages.

The local only themes live in local-private/, which is git ignored and is
never part of a public package. This script verifies that:

  * local-private/ is ignored by git and nothing in it is tracked,
  * no file of a local only theme exists in the public source tree,
  * no public package contains a file of a local only theme,
  * the local only package contains everything the theme page loads.

The theme page, its scripts and its description files are compared by name and
by content. The images are compared by name only: the palm drawings of the
Maldives theme are the same pictures the Beach theme already ships under a
different name, so their content is public even though the file names are not.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRIVATE_DIR = ROOT / "local-private"
PUBLIC_SOURCE_DIRS = ["src", "vendor", "packaging", "scripts"]
PUBLIC_PACKAGES = ROOT / "build" / "packages"
PRIVATE_PACKAGES = ROOT / "build" / "private-packages"

failures = []
notes = []


def fail(message: str) -> None:
    failures.append(message)


def git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip()


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def theme_inventory(theme_dir: pathlib.Path) -> tuple[set[str], set[str]]:
    """Return the distinctive file names and the unique content digests."""
    names: set[str] = set()
    unique_digests: set[str] = set()

    manifest_path = theme_dir / "source.json"
    manifest = {}
    if manifest_path.is_file():
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)

    # theme.json, metadata.json and source.json exist for every theme, they
    # are compared by content, not by name.
    for name in [manifest.get("page", ""), manifest.get("entry", "")]:
        if name:
            names.add(name)
    for name in manifest.get("scripts", []):
        names.add(name)
    for name in manifest.get("assets", []):
        names.add(name)

    # Everything but the images is unique content: the page, the scripts and
    # the description files. The images are artwork that another theme may
    # already ship under a different name.
    for path in sorted(theme_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
            continue
        unique_digests.add(digest(path))

    return names, unique_digests


def main() -> int:
    if not PRIVATE_DIR.is_dir():
        notes.append("no local private themes present")
    else:
        # --- git ---------------------------------------------------------
        code, _ = git("check-ignore", "-q", str(PRIVATE_DIR))
        if code != 0:
            fail("local-private/ is not ignored by git")
        else:
            notes.append("local-private/ is ignored by git")

        code, output = git("ls-files", "local-private")
        if output:
            fail(f"files of local-private/ are tracked by git: {output.splitlines()}")
        else:
            notes.append("no file of local-private/ is tracked by git")

        themes = sorted(p for p in PRIVATE_DIR.glob("themes/*") if p.is_dir())
        if not themes:
            notes.append("local-private/themes/ holds no theme")

        for theme_dir in themes:
            theme_id = theme_dir.name
            names, unique_digests = theme_inventory(theme_dir)

            # --- public source tree -------------------------------------
            for directory in PUBLIC_SOURCE_DIRS:
                base = ROOT / directory
                if not base.is_dir():
                    continue
                for path in base.rglob("*"):
                    if not path.is_file():
                        continue
                    if path.name in names:
                        fail(
                            f"file name of the local theme {theme_id} in the public tree: {path}"
                        )
                    if digest(path) in unique_digests:
                        fail(
                            f"content of the local theme {theme_id} in the public tree: {path}"
                        )

            # --- public packages ----------------------------------------
            if PUBLIC_PACKAGES.is_dir():
                for path in PUBLIC_PACKAGES.rglob("*"):
                    if not path.is_file():
                        continue
                    if path.name in names:
                        fail(
                            f"file name of the local theme {theme_id} in a public package: {path}"
                        )
                    if digest(path) in unique_digests:
                        fail(
                            f"content of the local theme {theme_id} in a public package: {path}"
                        )

            # --- local package -------------------------------------------
            with open(theme_dir / "theme.json", "r", encoding="utf-8") as handle:
                theme = json.load(handle)
            package = PRIVATE_PACKAGES / theme["packageId"]
            if not package.is_dir():
                fail(f"the local package of {theme_id} was not built: {package}")
                continue
            payload = package / "contents" / "themes" / theme_id
            if not (payload / theme["entry"]).is_file():
                fail(f"the local package of {theme_id} misses {theme['entry']}")
            manifest_path = theme_dir / "source.json"
            if manifest_path.is_file():
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
                for script in manifest.get("scripts", []):
                    if not (payload / script).is_file():
                        fail(f"the local package of {theme_id} misses {script}")
                for asset in manifest.get("assets", []):
                    if not (payload / "assets" / asset).is_file():
                        fail(f"the local package of {theme_id} misses assets/{asset}")
            notes.append(
                f"local theme {theme_id}: {len(names)} private file names, "
                f"{len(unique_digests)} private contents, package {package.name} complete"
            )

    for note in notes:
        print(f"  ok   {note}")
    for failure in failures:
        print(f"  FAIL {failure}")
    if failures:
        print(f"\n{len(failures)} problem(s) found.")
        return 1
    print("\nThe public source tree and the public packages contain no local only theme.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
