#!/usr/bin/env bash
set -euo pipefail

state_home="${XDG_STATE_HOME:-$HOME/.local/state}"
state_dir="$state_home/islandscape-plasma"
state_file="$state_dir/wallpapers.tsv"
busctl_cmd="${BUSCTL_CMD:-busctl}"
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
owned_ids="$(python3 "$project_root/scripts/package_ids.py" | tr '\n' ' ')"

if [[ -e "$state_file" ]]; then
    printf 'Keeping existing wallpaper backup: %s\n' "$state_file"
    exit 0
fi
mkdir -p -- "$state_dir"
tmp_file="$state_file.tmp.$$"
script='print(JSON.stringify(desktops().map(d => ({screen:d.screen, plugin:d.wallpaperPlugin}))))'
if ! state_json="$("$busctl_cmd" --user --json=short call org.kde.plasmashell /PlasmaShell \
    org.kde.PlasmaShell evaluateScript s "$script")"; then
    printf 'Could not query Plasma wallpaper state. Run this inside your Plasma session.\n' >&2
    exit 1
fi
if ! ISLANDSCAPE_WALLPAPER_JSON="$state_json" ISLANDSCAPE_OWNED_IDS="$owned_ids" python3 - >"$tmp_file" <<'PY'
import json
import os
import sys

wrapper = json.loads(os.environ["ISLANDSCAPE_WALLPAPER_JSON"])
desktops = json.loads(wrapper["data"][0])
owned = set(os.environ.get("ISLANDSCAPE_OWNED_IDS", "").split())
by_screen = {}
active_owned = set()
for desktop in desktops:
    screen = str(desktop.get("screen", ""))
    plugin = str(desktop.get("plugin", ""))
    if not screen.isdigit() or not plugin:
        continue
    if plugin in owned:
        active_owned.add(screen)
    else:
        by_screen.setdefault(screen, plugin)

if active_owned:
    sys.exit("An Islandscape wallpaper is already active but no previous state is saved. Select the original wallpaper first, or restore it manually.")
for screen, plugin in sorted(by_screen.items(), key=lambda item: int(item[0])):
    print(f"{screen}\t{plugin}")
if not by_screen:
    sys.exit("Plasma reported no desktop wallpapers")
PY
then
    rm -f -- "$tmp_file"
    exit 1
fi
chmod 600 "$tmp_file"
mv -- "$tmp_file" "$state_file"
printf 'Saved wallpaper plugin IDs to %s\n' "$state_file"
