#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_root="$project_root/build/packages"
rm -rf -- "$build_root"
mkdir -p -- "$build_root"

build_one() {
    local theme_id="$1"
    local entry_file="$2"
    local package_id="$3"
    local package_root="$build_root/$package_id"

    mkdir -p -- "$package_root/contents/ui" "$package_root/contents/themes/$theme_id/assets"
    cp -- "$project_root/packaging/metadata-$theme_id.json" "$package_root/metadata.json"
    cp -- "$project_root/LICENSE" "$package_root/LICENSE"
    THEME_ID="$theme_id" THEME_FILE="$entry_file" OUTPUT="$package_root/contents/ui/main.qml" \
        python3 - "$project_root/src/linux/main.qml.in" <<'PY'
import os
import pathlib
import sys

template = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
rendered = template.replace("@THEME_ID@", os.environ["THEME_ID"])
rendered = rendered.replace("@THEME_FILE@", os.environ["THEME_FILE"])
pathlib.Path(os.environ["OUTPUT"]).write_text(rendered, encoding="utf-8")
PY
    cp -a -- "$project_root/src/themes/$theme_id/." "$package_root/contents/themes/$theme_id/"
    cp -- "$project_root/vendor/Deskland/NOTICE" "$package_root/NOTICE"
    cp -- "$project_root/vendor/Deskland/TRADEMARKS.md" "$package_root/UPSTREAM-TRADEMARKS.md"
    cp -- "$project_root/vendor/Deskland/UPSTREAM-REVISION.txt" "$package_root/UPSTREAM-REVISION.txt"
    cp -- "$project_root/vendor/Deskland/prototype/share.js" "$package_root/contents/themes/$theme_id/share.js"
    if [[ "$theme_id" == beach ]]; then
        for asset in beach-coconut-palm-v2.png beach-coconut-palm-curved.png \
                     beach-coconut-palm-airy.png beach-coconut-palm-windswept.png \
                     beach-coconut-palm-arch.png; do
            cp -- "$project_root/vendor/Deskland/prototype/assets/$asset" \
                "$package_root/contents/themes/beach/assets/$asset"
        done
    else
        cp -- "$project_root/vendor/Deskland/prototype/meadow-boy.js" \
            "$package_root/contents/themes/meadow/meadow-boy.js"
        cp -- "$project_root/vendor/Deskland/prototype/meadow-cat.js" \
            "$package_root/contents/themes/meadow/meadow-cat.js"
        for asset in meadow-kite-boy-level-face.png meadow-kite-boy-diagonal-run.png meadow-black-kitten.png; do
            cp -- "$project_root/vendor/Deskland/prototype/assets/$asset" \
                "$package_root/contents/themes/meadow/assets/$asset"
        done
    fi
    python3 -m json.tool "$package_root/metadata.json" >/dev/null
    printf 'Built %s\n' "$package_root"
}

build_one beach flat.html org.islandscape.plasma.beach
build_one meadow meadow.html org.islandscape.plasma.meadow
