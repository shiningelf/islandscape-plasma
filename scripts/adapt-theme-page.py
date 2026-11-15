#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Adapt an upstream Deskland prototype page for the Linux Plasma port.

The upstream prototype pages are single file applications that expect a
Windows WebView2 host. The Plasma port keeps the rendering code untouched and
only rewrites the edges of the page:

  * the host bridge becomes dual: WebView2 for Windows, window.postMessage
    for the QtWebEngine based Plasma wallpaper plugin,
  * the simulated Windows desktop chrome (task bar, clock, layout panel and
    the fake icon desktop) is removed, because Plasma draws the real one,
  * the settings handler validates every parameter against one range table
    instead of clamping a hand picked subset,
  * the render scale follows the same large display rule as the other themes.

Every step is anchored: if an expected block is not found exactly once the
script fails instead of producing a half converted page.

    adapt-theme-page.py --source prototype/beach-turquoise.html \\
                        --output local-private/themes/maldives/maldives.html \\
                        --params local-private/themes/maldives/theme.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import theme_params as tp  # noqa: E402


class AdaptationError(Exception):
    pass


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def remove_between(text: str, start: str, end: str, label: str) -> str:
    """Remove the region that starts at ``start`` and ends right before ``end``."""
    if text.count(start) != 1:
        raise AdaptationError(f"{label}: start marker found {text.count(start)} times: {start!r}")
    if text.count(end) != 1:
        raise AdaptationError(f"{label}: end marker found {text.count(end)} times: {end!r}")
    begin = text.index(start)
    finish = text.index(end)
    if finish < begin:
        raise AdaptationError(f"{label}: markers are out of order")
    return text[:begin] + text[finish:]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AdaptationError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def insert_before(text: str, marker: str, addition: str, label: str) -> str:
    if text.count(marker) != 1:
        raise AdaptationError(f"{label}: marker found {text.count(marker)} times: {marker!r}")
    return text.replace(marker, addition + marker, 1)


# --------------------------------------------------------------------------
# the Linux specific code blocks
# --------------------------------------------------------------------------

HOST_BRIDGE = """  const host = window.chrome && window.chrome.webview;
  if (host) {
    host.addEventListener('message', ev => handle(JSON.parse(ev.data)));
    host.postMessage('ready');
  } else {
    // Linux adapter: QtWebEngine has no WebView2 host object. The Plasma
    // wallpaper plugin posts the same messages through window.postMessage.
    addEventListener('message', ev => handle(typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data));
    console.log('ISLANDSCAPE_QML_HOST_READY');
  }"""

PARAMETER_HELPERS = """// ---------------------------------------------------------------------------
// Parameters
//
// The host sends the range table of every parameter together with the values.
// The page validates against that table, so a value can never be out of range
// even if it comes from somewhere else. Without a table the page falls back to
// its own SLIDERS definitions.
// ---------------------------------------------------------------------------
function islandscapeParamSpec() {
  const spec = window.__ISLANDSCAPE_PARAMS__;
  return spec && typeof spec === 'object' ? spec : null;
}
function islandscapeKnownParam(key) {
  const spec = islandscapeParamSpec();
  if (spec && Object.prototype.hasOwnProperty.call(spec, key)) return true;
  return SLIDERS.some(s => s.key === key);
}
function islandscapeClampParam(key, value) {
  const spec = islandscapeParamSpec();
  const slider = SLIDERS.find(s => s.key === key);
  const rules = (spec && spec[key]) || slider || null;
  let result = Number(value);
  if (!Number.isFinite(result)) result = Number(DEFAULTS[key]);
  if (rules) {
    if (rules.min !== undefined && rules.min !== null) result = Math.max(Number(rules.min), result);
    if (rules.max !== undefined && rules.max !== null) result = Math.min(Number(rules.max), result);
    const step = Number(rules.step);
    if (Number.isFinite(step) && step > 0) {
      // Round on the step grid, without floating point noise.
      let decimals = 0, probe = step;
      while (decimals < 6 && Math.abs(probe - Math.round(probe)) > 1e-9) { probe *= 10; decimals++; }
      result = Number((Math.round(result / step) * step).toFixed(decimals));
    }
  }
  return result;
}"""

APPLY_SETTINGS = """// 应用设置：只处理认识的参数；每个参数都按同一套范围和步长校验，
// 校验规则来自宿主发来的参数表，没有参数表时退回页面自己的 SLIDERS 定义。
// 岸线相关的要重算陆地场，皮划艇和海鸟要增减，棕榈树、海龟和鱼群每帧从 P
// 读取，改完下一帧就生效。
function applySettings(values) {
  if (!values || typeof values !== 'object') return;
  if (typeof values.seed === 'number' && values.seed !== seed) reseed(values.seed);   // 设置窗口的"刷新"：换一张（桌面和预览用同一个种子）
  let field = false, kay = false, bird = false;
  for (const key in values) {
    if (key === 'seed' || !islandscapeKnownParam(key)) continue;
    if (typeof P[key] !== 'number') continue;
    const next = islandscapeClampParam(key, values[key]);
    if (P[key] === next) continue;
    P[key] = next;
    if (key === 'sigma' || key === 'warp') field = true;
    else if (key === 'kayaks') kay = true;
    else if (key === 'birds') bird = true;
  }
  if (field && FB) refresh();
  if (kay) syncKayaks();
  if (bird) syncBirds();
}"""

RENDER_SCALE = """  // On larger Linux outputs, modestly lower the 2400px+ physical output's
  // internal render scale to keep both WebGL views near the 30fps target.
  const dpr = devicePixelRatio || 1;
  // Apply the large-display cap in physical-pixel space. A logical-width
  // check would under-render 4K panels at 150%/200% desktop scaling.
  const qualityCap = WALL && W * dpr >= 2400
    ? Math.min(P.quality, 0.90 * dpr)
    : P.quality;
  const scale = PREVIEW ? 0.45 : Math.min(dpr, qualityCap);"""


# --------------------------------------------------------------------------
# the steps
# --------------------------------------------------------------------------

def strip_prototype_chrome(text: str) -> str:
    """Remove the simulated Windows desktop: task bar, clock, panel, icons."""
    steps = [
        ("preview runtime", '<script src="preview-runtime.js"></script>\n', ""),
        ("desktop markup", '<div id="desktop"></div>\n', ""),
    ]
    for label, old, new in steps:
        text = replace_once(text, old, new, label)

    # Task bar and layout panel, from the first tag to the tag that follows
    # them. Each block below ends where the next one starts.
    blocks = [
        ("task bar and panel", '<div id="taskbar">', '<div id="nogl">'),
        ("statistics", "const statsEl = document.getElementById('stats');\n",
         "const GPU = (() => {"),
        ("statistics function", "function updateStats() {", "function syncPanel() {"),
        ("panel sync", "function syncPanel() {", "const slidersEl = document.getElementById('sliders');"),
        ("slider list", "const slidersEl = document.getElementById('sliders');",
         "document.querySelector('.seg').addEventListener("),
        ("layout segments", "document.querySelector('.seg').addEventListener(",
         "document.querySelectorAll('.toggles input')"),
        ("toggles", "document.querySelectorAll('.toggles input')",
         "document.getElementById('collapse').addEventListener("),
        ("collapse button", "document.getElementById('collapse').addEventListener(",
         "// 换一张：新的种子"),
        ("reseed button", "document.getElementById('btnSeed')",
         "document.getElementById('btnAdd')"),
        ("add file button", "document.getElementById('btnAdd')",
         "desktop.addEventListener('pointerdown'"),
        ("desktop and key handlers", "desktop.addEventListener('pointerdown'",
         "let resizeT = 0;"),
        ("clock", "function tickClock() {", "/* ---------- 启动 ---------- */"),
    ]
    for label, start, end in blocks:
        text = remove_between(text, start, end, label)

    # Call sites of the removed helpers.
    text = replace_once(
        text,
        "  if (++frameN % 10 === 0 && PROTOTYPE_STATS) updateStats();\n",
        "",
        "statistics call",
    )
    text = replace_once(
        text,
        "if (grid.cols * grid.rows > layoutCapacity && layoutCapacity < 40) { applyLayout(layoutKind); syncPanel(); return; }",
        "if (grid.cols * grid.rows > layoutCapacity && layoutCapacity < 40) { applyLayout(layoutKind); return; }",
        "layout overflow branch",
    )
    text = replace_once(
        text,
        "else { applyLayout('mine'); syncPanel(); }",
        "else { applyLayout('mine'); }",
        "startup branch",
    )
    # The fake icon desktop is gone, the icon factory stays for the prototype
    # mode but must not throw when its container is missing.
    text = replace_once(
        text,
        "  desktop.appendChild(el);",
        "  if (desktop) desktop.appendChild(el);",
        "icon factory",
    )
    return text


def set_defaults(text: str, params) -> str:
    """Write the parameter defaults of the theme into the page's P object."""
    match = re.search(r"const P = \{.*?\n\};", text, re.S)
    if not match:
        raise AdaptationError("could not find the P parameter object")
    block = match.group(0)
    updated = block
    for param in params:
        pattern = re.compile(r"(\b" + re.escape(param["key"]) + r"\s*:\s*)(-?\d+(?:\.\d+)?)")
        if not pattern.search(updated):
            raise AdaptationError(f"parameter {param['key']} is missing from the P object")
        value = int(param["default"]) if param["integer"] else param["default"]
        updated = pattern.sub(lambda m: m.group(1) + str(value), updated, count=1)
    return text[: match.start()] + updated + text[match.end() :]


def adapt(text: str, params) -> str:
    text = strip_prototype_chrome(text)

    # The Windows task bar is gone, the scene may use the whole screen.
    text = replace_once(
        text,
        "const CELL_W = 76, CELL_H = 100, GRID_X0 = 4, GRID_Y0 = 6, TASKBAR = 48;",
        "const CELL_W = 76, CELL_H = 100, GRID_X0 = 4, GRID_Y0 = 6, TASKBAR = 0;",
        "task bar height",
    )

    text = set_defaults(text, params)

    text = replace_once(
        text,
        "  const scale = PREVIEW ? 0.45 : Math.min(devicePixelRatio || 1, P.quality);",
        RENDER_SCALE,
        "render scale",
    )

    # The parameter helpers and the new settings handler. The whole original
    # handler is replaced, not just its header.
    text = remove_between(
        text,
        "// 应用设置：只处理认识的参数；岸线相关的要重算陆地场，精度要重建画布，皮划艇要增减\nfunction applySettings(v) {",
        "function drawGhosts() {",
        "settings handler",
    )
    text = insert_before(
        text,
        "function drawGhosts() {",
        PARAMETER_HELPERS + "\n\n" + APPLY_SETTINGS + "\n\n",
        "settings handler",
    )

    # The host bridge.
    text = replace_once(
        text,
        "  const host = window.chrome && window.chrome.webview;\n"
        "  if (!host) return;\n"
        "  host.addEventListener('message', ev => handle(JSON.parse(ev.data)));\n"
        "  host.postMessage('ready');",
        HOST_BRIDGE,
        "host bridge",
    )

    # The parameter table arrives before any value.
    text = replace_once(
        text,
        "  const handle = m => {\n    if (m.t === 'pause')",
        "  const handle = m => {\n"
        "    if (m.t === 'params') { window.__ISLANDSCAPE_PARAMS__ = m.v || null; return; }\n"
        "    if (m.t === 'pause')",
        "message dispatch",
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--params", required=True, help="theme.json of the theme")
    parser.add_argument("--library", default="")
    args = parser.parse_args()

    source = pathlib.Path(args.source)
    output = pathlib.Path(args.output)
    with open(source, "r", encoding="utf-8") as handle:
        text = handle.read()
    with open(args.params, "r", encoding="utf-8") as handle:
        theme = json.load(handle)
    library = tp.load_library(pathlib.Path(args.library)) if args.library else tp.load_library()
    params = tp.resolve_params(theme, library)

    try:
        adapted = adapt(text, params)
    except AdaptationError as error:
        print(f"adaptation failed: {error}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(adapted, encoding="utf-8")
    print(f"  adapted {source.name} -> {output} ({len(params)} parameters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
