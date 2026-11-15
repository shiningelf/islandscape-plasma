# Upstream source and licenses

Islandscape for Plasma is based on the free themes in
[BLEZZ0102/Deskland](https://github.com/BLEZZ0102/Deskland), upstream revision
`9818b577402ff476e1b59da07970c56472713126`.

The upstream repository's `LICENSE`, `NOTICE`, and `TRADEMARKS.md` are included
in [`vendor/Deskland/`](vendor/Deskland/). The upstream project code and theme
assets are GPL version 3. This project applies GPL-3.0-only to the combined
distribution. Qt, KDE Frameworks, QtWebEngine and Chromium are system
dependencies and are not bundled here.

## Source separation

- `vendor/Deskland/prototype/` contains the unmodified upstream Beach and
  Meadow pages, support JavaScript and the images those themes use.
- `src/themes/beach/flat.html` and `beach-palms.js` are the Linux-adapted
  Beach copies. They contain the QtWebEngine message adapter, physical-pixel
  render scaling and the documented palm-clearance adjustment.
- `src/themes/meadow/meadow.html` is the Linux-adapted Meadow page. It contains
  the QtWebEngine message adapter and the same physical-pixel scale policy.
- `src/linux/main.qml.in` is the Plasma host. It reads per-screen desktop icon
  geometry, follows page DPR changes, holds geometry during drags, and uses
  Plasma's maximized/fullscreen window monitor to pause the affected output.
  Its parameter table is generated from the theme description, so the host,
  the configuration UI and the theme page always agree about the valid values.
- `src/linux/param-library.json` holds the numeric rules of the parameter sets
  that several themes share, currently the coastal one.
- `packaging/` gives Beach and Meadow separate IDs so both are selectable in
  Plasma's wallpaper chooser.

The upstream checkout in the parent workspace was not modified while creating
this project. Upstream attribution and the trademark notice travel with the
packages. Islandscape is an independent port and does not imply Deskland author
endorsement.
