#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
#
# Imports the local only themes from the workspace prototype directory into
# local-private/themes/. The imported files never leave that directory and are
# never part of a public package.
#
# Usage: scripts/import-private-themes.sh [workspace]
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
workspace="${1:-$(dirname -- "$project_root")}"

private_themes="$project_root/local-private/themes"
if [ ! -d "$private_themes" ]; then
    printf 'No local private themes directory at %s\n' "$private_themes" >&2
    exit 1
fi

status=0
for manifest in "$private_themes"/*/source.json; do
    [ -f "$manifest" ] || continue
    printf 'Importing %s\n' "$(basename -- "$(dirname -- "$manifest")")"
    python3 "$project_root/scripts/import_private_theme.py" \
        --manifest "$manifest" --workspace "$workspace" || status=1
done

exit "$status"
