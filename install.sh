#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kpackage_tool="${KPACKAGE_TOOL:-kpackagetool6}"
kpackage_args=(--type Plasma/Wallpaper)
command -v "$kpackage_tool" >/dev/null || { printf 'Install kpackagetool6 (Plasma 6) first.\n' >&2; exit 1; }

"$project_root/scripts/build-packages.sh"
"$project_root/scripts/backup-wallpapers.sh"

for package_id in org.islandscape.plasma.beach org.islandscape.plasma.meadow; do
    package_dir="$project_root/build/packages/$package_id"
    if "$kpackage_tool" "${kpackage_args[@]}" --list | grep -Fxq "$package_id"; then
        "$kpackage_tool" "${kpackage_args[@]}" --upgrade "$package_dir"
    else
        "$kpackage_tool" "${kpackage_args[@]}" --install "$package_dir"
    fi
done

printf '\nInstalled both Islandscape wallpapers for this user.\n'
printf 'Choose Islandscape — Beach or Islandscape — Meadow in Desktop and Wallpaper settings.\n'
printf 'If they do not appear yet, log out and back in or restart plasmashell.\n'
