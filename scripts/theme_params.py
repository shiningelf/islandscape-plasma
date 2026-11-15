#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Shared parameter handling for the Islandscape Plasma wallpapers.

One theme describes its parameters in a ``theme.json`` file:

    {
        "id": "beach",
        "packageId": "org.islandscape.plasma.beach",
        "name": "Islandscape - Beach",
        "entry": "flat.html",
        "params": {
            "library": "coastal",          # shared numeric constraints
            "extra": {"turtles": {...}},   # theme-only parameters
            "groups": [{"name": {"en": "...", "zh": "..."}, "keys": ["sigma", "warp"]}],
            "labels": {
                "sigma": {
                    "label": {"en": "...", "zh": "..."},
                    "hint": {"en": "...", "zh": "..."},
                    "unit": {"en": "px", "zh": "px"}
                }
            },
            "defaults": {"sigma": 100}
        }
    }

The same specification drives

* the Plasma configuration UI (``contents/ui/config.qml``),
* the KConfig schema (``contents/config/main.xml``),
* the parameter table compiled into the wallpaper host (``main.qml``),
* and the constraint table pushed to the theme page.

Nothing else is allowed to restate ranges, steps or defaults: the QML UI and
the page must never disagree about what a valid value is.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "src" / "linux" / "param-library.json"


class ThemeError(Exception):
    """Raised when a theme description is incomplete or inconsistent."""


def load_json(path: pathlib.Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_library(path: pathlib.Path = LIBRARY_PATH) -> Dict[str, Any]:
    return load_json(path)["libraries"]


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ThemeError(f"{label} must be a number, got {value!r}")
    return float(value)


def resolve_params(theme: Dict[str, Any], library: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the ordered, fully resolved parameter list of a theme."""
    spec = theme.get("params") or {}
    library_name = spec.get("library")
    library_params = library.get(library_name, {}) if library_name else {}
    extra_params = spec.get("extra") or {}
    labels = spec.get("labels") or {}
    defaults = spec.get("defaults") or {}
    groups = spec.get("groups") or []

    resolved: List[Dict[str, Any]] = []
    seen = set()

    for group in groups:
        group_name = _translations(group.get("name") or "")
        for key in group.get("keys") or []:
            if key in seen:
                raise ThemeError(f"parameter {key!r} is listed in more than one group")
            seen.add(key)

            constraints = extra_params.get(key) or library_params.get(key)
            if constraints is None:
                raise ThemeError(f"parameter {key!r} has no range definition")
            if key not in labels:
                raise ThemeError(f"parameter {key!r} has no label")
            if key not in defaults:
                raise ThemeError(f"parameter {key!r} has no default")

            label = labels[key]
            minimum = _number(constraints["min"], f"{key}.min")
            maximum = _number(constraints["max"], f"{key}.max")
            step = _number(constraints.get("step", 1), f"{key}.step")
            if maximum < minimum:
                raise ThemeError(f"parameter {key!r} has max < min")
            if step <= 0:
                raise ThemeError(f"parameter {key!r} has a non-positive step")

            default = _number(defaults[key], f"{key}.default")
            if default < minimum or default > maximum:
                raise ThemeError(
                    f"default {default} of {key!r} is outside [{minimum}, {maximum}]"
                )

            resolved.append(
                {
                    "key": key,
                    "group": group_name,
                    "label": _translations(label.get("label") or key),
                    "hint": _translations(label.get("hint") or ""),
                    "unit": _translations(label.get("unit") or ""),
                    "format": label.get("format") or "",
                    "min": minimum,
                    "max": maximum,
                    "step": step,
                    "default": default,
                    "control": constraints.get("control") or "slider",
                    "integer": step >= 1,
                }
            )

    unknown = set(defaults) - seen
    if unknown:
        raise ThemeError(f"defaults without a group: {sorted(unknown)}")
    return resolved


def page_spec(params: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Constraint table handed to the theme page so it can validate values."""
    return {
        param["key"]: {
            "min": param["min"],
            "max": param["max"],
            "step": param["step"],
            "default": param["default"],
        }
        for param in params
    }


def config_binding(params: List[Dict[str, Any]]) -> str:
    """QML binding that reads the stored configuration of every parameter.

    QQmlPropertyMap exposes its keys as bindable properties, so the binding
    re-evaluates whenever the stored value changes. The valueChanged() signal
    is not usable here, it is not emitted for changes that come from the
    configuration file.
    """
    lines = []
    for param in params:
        key = param["key"]
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            raise ThemeError(f"parameter {key!r} is not a valid QML property name")
        lines.append(f'        "{key}": configuration ? configuration.{key} : undefined,')
    return "({\n" + "\n".join(lines) + "\n    })"


def qml_literal(value: Any) -> str:
    """JSON is a valid QML/JavaScript literal for the values we emit."""
    return json.dumps(value, ensure_ascii=False, sort_keys=False)


def render_config_xml(params: List[Dict[str, Any]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"',
        '      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '      xsi:schemaLocation="http://www.kde.org/standards/kcfg/1.0',
        '      http://www.kde.org/standards/kcfg/1.0/kcfg.xsd" >',
        '  <kcfgfile name=""/>',
        "",
        '  <group name="General">',
    ]
    for param in params:
        kind = "Int" if param["integer"] else "Double"
        default = int(param["default"]) if param["integer"] else param["default"]
        lines.append(f'    <entry name="{param["key"]}" type="{kind}">')
        lines.append(f"      <label>{_escape(_bilingual_text(param['label']))}</label>")
        hint = _bilingual_text(param["hint"])
        if hint:
            lines.append(f"      <tooltip>{_escape(hint)}</tooltip>")
        lines.append(f"      <default>{default}</default>")
        lines.append("    </entry>")
    lines += ["  </group>", "", "</kcfg>", ""]
    return "\n".join(lines)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _translations(value: Any) -> Dict[str, str]:
    """Normalize a string or an {en, zh} map for generated QML."""
    if isinstance(value, dict):
        english = str(value.get("en") or value.get("zh") or "")
        chinese = str(value.get("zh") or value.get("en") or "")
        return {"en": english, "zh": chinese}
    text = str(value or "")
    return {"en": text, "zh": text}


def _bilingual_text(value: Dict[str, str]) -> str:
    english, chinese = value.get("en", ""), value.get("zh", "")
    if english and chinese and english != chinese:
        return f"{english} / {chinese}"
    return english or chinese


def render_config_qml(params: List[Dict[str, Any]]) -> str:
    """Build contents/ui/config.qml from the resolved parameter list."""
    properties = []
    for param in params:
        kind = "int" if param["integer"] else "double"
        properties.append(
            f"    // {_bilingual_text(param['group'])}\n"
            f"    property {kind} cfg_{param['key']}: {_default_literal(param)}\n"
            f"    property {kind} cfg_{param['key']}Default: {_default_literal(param)}"
        )

    grouped_params: Dict[str, Tuple[Dict[str, str], List[Dict[str, Any]]]] = {}
    for param in params:
        group_name = param["group"]
        group_key = json.dumps(group_name, ensure_ascii=False, sort_keys=True)
        if group_key not in grouped_params:
            grouped_params[group_key] = (group_name, [])
        grouped_params[group_key][1].append(param)

    controls = []
    for group_name, group_params in grouped_params.values():
        rows = "\n\n".join(_render_control(param) for param in group_params)
        controls.append(
            "        QQC2.GroupBox {\n"
            f"            title: root.localized({qml_literal(group_name)})\n"
            "            Layout.fillWidth: true\n"
            "            ColumnLayout {\n"
            "                anchors.fill: parent\n"
            "                spacing: 8\n\n"
            f"{rows}\n"
            "            }\n"
            "        }"
        )

    reset = []
    for param in params:
        reset.append(f"        cfg_{param['key']} = {_default_literal(param)};")

    return (
        _CONFIG_TEMPLATE.replace("@@PROPERTIES@@", "\n\n".join(properties))
        .replace("@@CONTROLS@@", "\n\n".join(controls))
        .replace("@@RESET@@", "\n".join(reset))
    )


def _default_literal(param: Dict[str, Any]) -> str:
    if param["integer"]:
        return str(int(param["default"]))
    return repr(float(param["default"]))


def _render_control(param: Dict[str, Any]) -> str:
    key = param["key"]
    if param["control"] == "toggle":
        return (
            "        RowLayout {\n"
            "            Layout.fillWidth: true\n"
            "            QQC2.CheckBox {\n"
            f"                text: root.localized({qml_literal(param['label'])})\n"
            f"                checked: cfg_{key} > 0\n"
            f"                onClicked: cfg_{key} = checked ? 1 : 0\n"
            "            }\n"
            "        }"
        )

    minimum = int(param["min"]) if param["integer"] else param["min"]
    maximum = int(param["max"]) if param["integer"] else param["max"]
    step = int(param["step"]) if param["integer"] else param["step"]
    unit = param["unit"]
    suffix = f' + " " + root.localized({qml_literal(unit)})' if unit.get("en") or unit.get("zh") else ""
    hint = ""
    if param["hint"]:
        hint = (
            "                HoverHandler { id: "
            f"{key}Hover }}\n"
            "                QQC2.ToolTip.visible: "
            f"{key}Hover.hovered\n"
            f"                QQC2.ToolTip.text: root.localized({qml_literal(param['hint'])})\n"
        )
    return (
        "        RowLayout {\n"
        "            Layout.fillWidth: true\n"
        "            spacing: 10\n"
        "            QQC2.Label {\n"
        f"                text: root.localized({qml_literal(param['label'])})\n"
        "                Layout.preferredWidth: 150\n"
        "                elide: Text.ElideRight\n"
        "            }\n"
        "            QQC2.Slider {\n"
        f"                id: {key}Slider\n"
        "                Layout.fillWidth: true\n"
        f"                from: {minimum}\n"
        f"                to: {maximum}\n"
        f"                stepSize: {step}\n"
        f"                value: cfg_{key}\n"
        f"                onMoved: cfg_{key} = {_rounded(key, param['integer'])}\n"
        f"{hint}"
        "            }\n"
        "            QQC2.Label {\n"
        f'                text: {key}Slider.value{suffix}\n'
        "                Layout.preferredWidth: 70\n"
        "                horizontalAlignment: Text.AlignRight\n"
        "            }\n"
        "        }"
    )


def _rounded(key: str, integer: bool) -> str:
    return "Math.round(value)" if integer else "value"


_CONFIG_TEMPLATE = """// SPDX-License-Identifier: GPL-3.0-only
// Generated from the theme's parameter specification by scripts/build-packages.sh.
// Edit src/themes/<theme>/theme.json instead of this file.

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

ColumnLayout {
    id: root
    Layout.fillWidth: true
    Layout.fillHeight: true

    // The Plasma wallpaper configuration dialog expects these two.
    property alias formLayout: root
    property var parentLayout
    // Plasma injects these when it loads a wallpaper's configuration UI.
    // Declare them even when this settings form does not need to read them.
    property var configDialog
    property var wallpaperConfiguration
    signal configurationChanged()

    // Injected by Plasma from contents/config/main.xml.
@@PROPERTIES@@

    ColumnLayout {
        id: settingsContent
        Layout.fillWidth: true
        Layout.maximumWidth: 820
        Layout.alignment: Qt.AlignHCenter
        Layout.margins: 12
        spacing: 10

@@CONTROLS@@
    QQC2.Button {
        id: resetButton
        text: root.localized({"en": "Restore defaults", "zh": "恢复默认值"})
        Layout.alignment: Qt.AlignRight
        Layout.topMargin: 2
        onClicked: root.resetToDefaults()
    }
    }

    function localized(value) {
        if (typeof value === "string")
            return value;
        var languages = Qt.locale().uiLanguages;
        if (!languages || languages.length === 0)
            languages = [Qt.locale().name];
        for (var i = 0; i < languages.length; ++i) {
            var language = String(languages[i]).toLowerCase();
            if (language.indexOf("zh") === 0)
                return value.zh || value.en || "";
            if (language.indexOf("en") === 0)
                return value.en || value.zh || "";
        }
        return value.en || value.zh || "";
    }

    function resetToDefaults() {
@@RESET@@
    }
}
"""
