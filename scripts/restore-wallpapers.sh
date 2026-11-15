#!/usr/bin/env bash
set -euo pipefail

state_home="${XDG_STATE_HOME:-$HOME/.local/state}"
state_file="$state_home/islandscape-plasma/wallpapers.tsv"
busctl_cmd="${BUSCTL_CMD:-busctl}"
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
owned_ids=()
while IFS= read -r package_id; do
    [ -n "$package_id" ] && owned_ids+=("$package_id")
done < <(python3 "$project_root/scripts/package_ids.py")

active_file="$(mktemp)"
trap 'rm -f -- "$active_file"' EXIT
script='print(JSON.stringify(desktops().map(d => ({screen:d.screen, plugin:d.wallpaperPlugin}))))'
if ! state_json="$("$busctl_cmd" --user --json=short call org.kde.plasmashell /PlasmaShell \
    org.kde.PlasmaShell evaluateScript s "$script")"; then
    printf 'Could not query Plasma wallpaper state. Run this inside your Plasma session.\n' >&2
    exit 1
fi
if ! ISLANDSCAPE_WALLPAPER_JSON="$state_json" python3 - >"$active_file" <<'PY'
import json
import os

wrapper = json.loads(os.environ["ISLANDSCAPE_WALLPAPER_JSON"])
for desktop in json.loads(wrapper["data"][0]):
    screen = str(desktop.get("screen", ""))
    plugin = str(desktop.get("plugin", ""))
    if screen.isdigit() and plugin:
        print(f"{screen}\t{plugin}")
PY
then
    printf 'Could not parse the current Plasma wallpaper state.\n' >&2
    exit 1
fi

declare -A previous=()
if [[ -r "$state_file" ]]; then
    while IFS=$'\t' read -r screen plugin; do
        [[ "$screen" =~ ^[0-9]+$ && -n "$plugin" ]] && previous["$screen"]="$plugin"
    done <"$state_file"
fi

restored=0
while IFS=$'\t' read -r screen current; do
    is_owned=0
    for plugin_id in "${owned_ids[@]}"; do
        [[ "$current" == "$plugin_id" ]] && is_owned=1
    done
    (( is_owned )) || continue
    if [[ -z "${previous[$screen]:-}" ]]; then
        printf 'No saved wallpaper for screen %s; keeping the package installed. Select a different wallpaper manually, then retry; the previous choice cannot be inferred without a backup.\n' "$screen" >&2
        exit 1
    fi
    "$busctl_cmd" --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell setWallpaper \
        "sa{sv}u" "${previous[$screen]}" 0 "$screen" >/dev/null
    printf 'Restored screen %s to %s\n' "$screen" "${previous[$screen]}"
    restored=1
done <"$active_file"

if (( ! restored )); then
    printf 'No Islandscape wallpaper is active; no wallpaper changes needed.\n'
fi
