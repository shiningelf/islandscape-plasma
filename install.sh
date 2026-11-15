#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
kpackage_tool="${KPACKAGE_TOOL:-kpackagetool6}"
kpackage_args=(--type Plasma/Wallpaper)
command -v "$kpackage_tool" >/dev/null || { printf 'Install kpackagetool6 (Plasma 6) first.\n' >&2; exit 1; }

"$project_root/scripts/build-packages.sh"
"$project_root/scripts/backup-wallpapers.sh"

shopt -s nullglob
installed=()
for package_root in "$project_root"/build/packages/*/ "$project_root"/build/private-packages/*/; do
    package_id="$(basename -- "$package_root")"
    if "$kpackage_tool" "${kpackage_args[@]}" --list | grep -Fxq "$package_id"; then
        "$kpackage_tool" "${kpackage_args[@]}" --upgrade "$package_root"
    else
        "$kpackage_tool" "${kpackage_args[@]}" --install "$package_root"
    fi
    installed+=("$package_id")
done

printf '\nInstalled the Islandscape wallpapers for this user:\n'
for package_id in "${installed[@]}"; do
    printf '  %s\n' "$package_id"
done
printf 'Choose one of them in Desktop and Wallpaper settings.\n'
printf 'If they do not appear yet, log out and back in or restart plasmashell.\n'
