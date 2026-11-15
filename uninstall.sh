#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kpackage_tool="${KPACKAGE_TOOL:-kpackagetool6}"
kpackage_args=(--type Plasma/Wallpaper)
command -v "$kpackage_tool" >/dev/null || { printf 'kpackagetool6 is required to uninstall.\n' >&2; exit 1; }

# Restore the saved per-screen wallpaper before removing a package that might
# still be selected. The helper refuses to orphan an active wallpaper if its
# pre-install backup is missing.
"$project_root/scripts/restore-wallpapers.sh"

while IFS= read -r package_id; do
    [ -n "$package_id" ] || continue
    if "$kpackage_tool" "${kpackage_args[@]}" --list | grep -Fxq "$package_id"; then
        "$kpackage_tool" "${kpackage_args[@]}" --remove "$package_id"
    fi
done < <(python3 "$project_root/scripts/package_ids.py")

state_home="${XDG_STATE_HOME:-$HOME/.local/state}"
rm -f -- "$state_home/islandscape-plasma/wallpapers.tsv"
printf 'Islandscape wallpapers removed. Plasma wallpaper settings and upstream source files were left untouched.\n'
