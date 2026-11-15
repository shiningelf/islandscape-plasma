#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
#
# Builds the wallpaper packages.
#
#   build/packages/          public themes, taken from src/themes/
#   build/private-packages/  local only themes, taken from local-private/themes/
#
# A theme is any directory that holds a theme.json. Public and local themes
# use the same builder, so a theme that is developed locally produces exactly
# the same package shape as a theme that is published.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
public_root="$project_root/build/packages"
private_root="$project_root/build/private-packages"

rm -rf -- "$public_root" "$private_root"
mkdir -p -- "$public_root" "$private_root"

build_theme() {
    local source_dir="$1"
    local output_root="$2"
    local metadata_fallback="$3"

    local theme_id package_id package_root
    theme_id="$(basename -- "$source_dir")"
    package_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["packageId"])' \
        "$source_dir/theme.json")"
    package_root="$output_root/$package_id"

    mkdir -p -- "$package_root/contents/ui" "$package_root/contents/config" \
        "$package_root/contents/themes/$theme_id"
    python3 "$project_root/scripts/build_theme.py" \
        --source "$source_dir" --output "$package_root" --metadata "$metadata_fallback"
    cp -- "$project_root/LICENSE" "$package_root/LICENSE"
    cp -- "$project_root/upstream/Deskland/NOTICE" "$package_root/NOTICE"
    cp -- "$project_root/upstream/Deskland/TRADEMARKS.md" "$package_root/UPSTREAM-TRADEMARKS.md"
    cp -- "$project_root/upstream/Deskland/UPSTREAM-REVISION.txt" "$package_root/UPSTREAM-REVISION.txt"
    python3 -m json.tool "$package_root/metadata.json" >/dev/null
    printf 'Built %s\n' "$package_root"
}

printf 'Public themes:\n'
for source_dir in "$project_root"/src/themes/*/; do
    [ -f "$source_dir/theme.json" ] || continue
    build_theme "$source_dir" "$public_root" \
        "$project_root/packaging/metadata-$(basename -- "$source_dir").json"
done

private_themes_dir="$project_root/local-private/themes"
if [ -d "$private_themes_dir" ]; then
    printf 'Local only themes:\n'
    for source_dir in "$private_themes_dir"/*/; do
        [ -f "$source_dir/theme.json" ] || continue
        build_theme "$source_dir" "$private_root" ""
    done
else
    printf 'No local private themes present, skipping.\n'
fi

printf '\nPackages are in %s\n' "$public_root"
if [ -d "$private_themes_dir" ]; then
    printf 'Local only packages are in %s\n' "$private_root"
fi
