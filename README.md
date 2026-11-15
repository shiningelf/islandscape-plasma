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

They appear as separate entries in Plasma's wallpaper chooser.

## Parameters

Every theme describes its parameters in one file, `theme.json`:

```json
{
  "id": "beach",
  "params": {
    "library": "coastal",
    "groups": [{"name": "Shoreline", "keys": ["sigma", "warp"]}],
    "labels": {"sigma": {"label": "Distance from icons", "unit": "px"}},
    "defaults": {"sigma": 100}
  }
}
```

* `src/linux/param-library.json` holds the shared numeric rules. The
  `coastal` library covers the parameters that every coastal theme shares
  (`sigma`, `warp`, `shoal`, `shallow`, `palms`, `kayaks`, `birds`); the
  `meadow` library covers the meadow parameters. A theme adds its own
  parameters under `params.extra` when a theme needs parameters beyond its
  shared library.
* The labels, hints, units, grouping and defaults belong to the theme, so a
  theme can be translated without touching the shared rules.
* One specification produces four things: the configuration UI
  (`contents/ui/config.qml`), the KConfig schema (`contents/config/main.xml`),
  the parameter table compiled into the wallpaper host (`contents/ui/main.qml`)
  and the constraint table the theme page receives. No range, step or default
  is written down twice.

The settings are stored per theme in Plasma's own wallpaper configuration, so
switching a theme never mixes the settings of another one. The configuration
dialog is the standard Plasma one, next to the wallpaper preview.

## Host and theme protocol

The wallpaper host and the theme page talk through `window.postMessage`:

| Message | Direction | Payload |
|---|---|---|
| `params` | host → page | range, step and default of every parameter |
| `settings` | host → page | the current values |
| `reset` | host → page | the values to restore |
| `icons` | host → page | the icon rectangles of this output, in physical pixels |
| `pause` | host → page | true while a maximized or fullscreen window covers the output |
| `ready` | page → host | the page installed its listener |

The page converts the physical pixels of the icon rectangles with
`window.devicePixelRatio`, the same way the Windows host did, and the host
takes its own scale from the page so that a Plasma scale change cannot drift
away from the wallpaper.

## Install on Arch-based Plasma 6

Runtime requirements are KDE Plasma 6, QtWebEngine for Qt 6, `kpackagetool6`,
Python 3, and a running Plasma user session. The scripts install into the
current user's KPackage directory; do not run them with `sudo`.

```sh
./install.sh
```

The installer builds both included wallpaper packages, records the current wallpaper
plugin ID for each screen, and installs them. Open **System Settings →
Wallpaper** (or the desktop wallpaper picker) and choose the theme you want.
If the entries do not appear yet, log out and back in, or restart the Plasma
shell:

```sh
systemctl --user restart plasma-plasmashell.service
```

If you install packages manually instead, run `scripts/backup-wallpapers.sh`
before selecting an Islandscape wallpaper so uninstall can restore the
previous wallpaper plugin on each display.

## Uninstall and restore

With the wallpaper state recorded by `install.sh`, run:

```sh
./uninstall.sh
```

The script switches displays that currently use Islandscape back to their
saved wallpaper plugin, then removes the packages. Plasma retains each
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

The generated wallpaper packages are written to `build/packages/`. No C++
compilation is needed.

## Source layout

```text
vendor/Deskland/       Unmodified upstream files used by these themes
src/linux/             Plasma QML host, icon bridge, scale and pause handling
src/linux/param-library.json  Shared parameter rules of the coastal themes
src/themes/            Linux-adapted Beach and Meadow HTML entry points
packaging/             Plasma KPackage metadata for both wallpaper entries
scripts/               Build, install, backup, restore and uninstall helpers
```

See [`UPSTREAM.md`](UPSTREAM.md) for source revision, license and the exact
Linux adaptation list. The bundled upstream license and trademark notice are
in `vendor/Deskland/`; the project is distributed under GPL-3.0-only.
