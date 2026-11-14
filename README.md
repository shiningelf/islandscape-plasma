# Islandscape for KDE Plasma

Islandscape is a user-installed KDE Plasma wallpaper port based on the free
Beach and Meadow themes from [Deskland Preview](https://github.com/BLEZZ0102/Deskland).
The original theme renderers remain HTML/WebGL2; the Linux layer is a QML
wallpaper plugin that supplies real desktop icon rectangles, tracks display
scale, and pauses a display when a maximized or fullscreen window covers it.

The product name and plugin IDs are distinct from Deskland. This is an
independent community port and is not an official Deskland release.

## Included wallpapers

- **Islandscape — Beach**: waves, shoreline, kayaks, birds and palms.
- **Islandscape — Meadow**: grass, drifting clouds, shadows, a kite-flying boy
  and a cat.

They appear as separate entries in Plasma's wallpaper chooser. The original
author's settings window has not been ported yet; each theme currently uses
its source defaults.

## Install on Arch-based Plasma 6

Runtime requirements are KDE Plasma 6, QtWebEngine for Qt 6, `kpackagetool6`,
Python 3, and a running Plasma user session. The scripts install into the
current user's KPackage directory; do not run them with `sudo`.

```sh
./install.sh
```

The installer builds both wallpaper packages, records the current wallpaper
plugin ID for each screen, and installs them. Open **System Settings →
Wallpaper** (or the desktop wallpaper picker) and choose Beach or Meadow. If
the entries do not appear yet, log out and back in, or restart the Plasma shell:

```sh
systemctl --user restart plasma-plasmashell.service
```

If you install packages manually instead, run `scripts/backup-wallpapers.sh`
before selecting either Islandscape wallpaper so uninstall can restore the
previous wallpaper plugin on each display.

## Uninstall and restore

With the wallpaper state recorded by `install.sh`, run:

```sh
./uninstall.sh
```

The script switches displays that currently use Islandscape back to their
saved wallpaper plugin, then removes both packages. Plasma retains each
wallpaper plugin's own settings in its desktop configuration, so selecting
the saved plugin restores its configured image or wallpaper settings.

If the original wallpaper was changed after installation, open Plasma's
wallpaper chooser and select the desired wallpaper before uninstalling. The
uninstaller only restores screens that still use an Islandscape wallpaper.
If no backup exists, it refuses to remove a package that is still active,
avoiding a broken wallpaper. Switch to another wallpaper first, or run the
backup helper before selecting Islandscape.

## Build packages without installing

```sh
./scripts/build-packages.sh
```

The generated KPackage directories are written to `build/packages/`. No C++
compilation is needed.

## Source layout

```text
vendor/Deskland/       Unmodified upstream files used by these themes
src/linux/             Plasma QML host, icon bridge, scale and pause handling
src/themes/            Linux-adapted Beach and Meadow HTML entry points
packaging/             Plasma KPackage metadata for both wallpaper entries
scripts/               Build, install, backup, restore and uninstall helpers
```

See [`UPSTREAM.md`](UPSTREAM.md) for source revision, license and the exact
Linux adaptation list. The bundled upstream license and trademark notice are
in `vendor/Deskland/`; the project is distributed under GPL-3.0-only.
