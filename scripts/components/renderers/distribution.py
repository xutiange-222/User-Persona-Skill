from __future__ import annotations

from collections import defaultdict
from math import cos, sin, pi

from ._utils import escape, escape_for_data_attr


LEVEL_Y = {"high": 90, "middle": 235, "low": 380}
LEVEL_ORDER = {"high": 0, "middle": 1, "low": 2}
Y_LABELS = {"high": "\u9ad8", "middle": "\u4e2d", "low": "\u4f4e"}


def _level_name(value_variables: list[dict], variable_idx: int, level: str) -> str:
    for item in value_variables[variable_idx]["levels"]:
        if item["level"] == level:
            return item["name"]
    return value_variables[variable_idx]["levels"][0]["name"]


def _format_quote(raw: object, persona: dict, variable_name: str, level_name: str) -> str:
    if isinstance(raw, dict):
        quote = str(raw.get("quote") or raw.get("text") or "").strip()
        respondent = str(raw.get("respondent") or raw.get("source") or "").strip()
        if quote and respondent:
            return f'"{quote}"\n\u2014 {respondent}\uff08{persona["name"]} \u00b7 {variable_name} = {level_name}\uff09'
        if quote:
            return f'"{quote}"\n\u2014 {persona["name"]} \u00b7 {variable_name} = {level_name}'
    text = str(raw).strip()
    if text:
        if "\n\u2014" in text or "\u2014" in text:
            return text
        return f'"{text}"\n\u2014 {persona["name"]} \u00b7 {variable_name} = {level_name}'
    return ""


def _point_evidence(persona: dict, pos: dict, variable_name: str, level_name: str) -> str:
    quotes = pos.get("evidence_quotes") or pos.get("quotes") or []
    if isinstance(quotes, str):
        quotes = [quotes]
    formatted = [
        item for item in (_format_quote(q, persona, variable_name, level_name) for q in quotes)
        if item
    ]
    if formatted:
        return "\n\n".join(formatted)

    evidence = pos.get("evidence")
    if evidence:
        return _format_quote(evidence, persona, variable_name, level_name)

    respondents = persona.get("respondents", [])
    if not respondents:
        return f'{persona["name"]}\n"{variable_name}: {level_name}"'
    return "\n\n".join(
        f'{persona["name"]} / {name}\n"{variable_name}: {level_name}"'
        for name in respondents
    )


def _x_positions(n_vars: int) -> list[float]:
    x_base = 225
    x_max = 855
    x_step = (x_max - x_base) / max(n_vars - 1, 1)
    return [x_base + idx * x_step for idx in range(n_vars)]


def _cluster_offsets(count: int) -> list[tuple[float, float]]:
    if count <= 1:
        return [(0, 0)]
    radius = 6 if count <= 3 else 8
    return [
        (cos(2 * pi * i / count) * radius, sin(2 * pi * i / count) * radius)
        for i in range(count)
    ]


def _render_chart_svg(value_variables: list[dict], personas: list[dict]) -> str:
    n_vars = len(value_variables)
    x_positions = _x_positions(n_vars)
    parts: list[str] = ['<svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">']

    for y in LEVEL_Y.values():
        parts.append(f'<line class="snake-grid-line" x1="100" y1="{y}" x2="980" y2="{y}"/>')
    for x in x_positions:
        parts.append(f'<line class="snake-grid-col" x1="{x:.0f}" y1="70" x2="{x:.0f}" y2="410"/>')

    for level, y in LEVEL_Y.items():
        parts.append(f'<text class="snake-axis-y-label" x="86" y="{y + 5}">{escape(Y_LABELS[level])}</text>')

    for idx, variable in enumerate(value_variables):
        x = x_positions[idx]
        levels = sorted(variable["levels"], key=lambda item: LEVEL_ORDER[item["level"]])
        for level_item in levels:
            level = level_item["level"]
            y = LEVEL_Y[level]
            dy = 24 if level != "low" else 22
            parts.append(
                f'<text class="snake-point-level-label snake-level-name" '
                f'x="{x:.0f}" y="{y + dy:.0f}">{escape(level_item["name"])}</text>'
            )
        parts.append(f'<text class="snake-axis-x-label" x="{x:.0f}" y="452">{escape(variable["name"])}</text>')

    point_records: list[dict] = []
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for persona in personas:
        sorted_positions = sorted(persona["positions"], key=lambda pos: int(pos["variable_idx"]))
        points = []
        for pos in sorted_positions:
            variable_idx = int(pos["variable_idx"])
            x = x_positions[variable_idx]
            y = LEVEL_Y[pos["level"]]
            points.append((x, y, pos))
        poly = " ".join(f"{x:.0f},{y:.0f}" for x, y, _ in points)
        parts.append(
            f'<polyline class="snake-line" points="{poly}" '
            f'stroke="{escape(persona["color"], quote=True)}" data-target="{escape(persona["id"], quote=True)}"/>'
        )
        for x, y, pos in points:
            variable_idx = int(pos["variable_idx"])
            level_name = _level_name(value_variables, variable_idx, pos["level"])
            evidence = _point_evidence(persona, pos, value_variables[variable_idx]["name"], level_name)
            record = {
                "x": x,
                "y": y,
                "color": persona["color"],
                "target": persona["id"],
                "evidence": evidence,
            }
            point_records.append(record)
            grouped[(round(x), round(y))].append(record)

    for (x_key, y_key), group in grouped.items():
        offsets = _cluster_offsets(len(group))
        for record, (dx, dy) in zip(group, offsets):
            parts.append(
                f'<circle class="snake-point" cx="{record["x"] + dx:.1f}" cy="{record["y"] + dy:.1f}" r="7" '
                f'fill="{escape(record["color"], quote=True)}" data-target="{escape(record["target"], quote=True)}" '
                f'data-evidence="{escape_for_data_attr(record["evidence"])}"/>'
            )

    parts.append('</svg>')
    return '<div class="distribution-chart">' + "".join(parts) + '</div>'


def render_distribution_multi(props: dict) -> str:
    legend = "".join(
        f'<button class="distribution-legend-btn active" data-target="{escape(p["id"], quote=True)}" '
        f'style="color: {escape(p["color"], quote=True)};">'
        f'<span class="distribution-legend-swatch" style="background: {escape(p["color"], quote=True)};"></span>'
        f'<span class="distribution-legend-name">{escape(p["name"])}</span>'
        f'<span class="distribution-legend-count">{len(p.get("respondents", []))} \u4eba</span>'
        f'</button>'
        for p in props["personas"]
    )
    footer = ""
    if props.get("footer_hint"):
        footer = (
            '<div class="distribution-footer">'
            f'<div><strong>\u8bfb\u56fe\u65b9\u5f0f</strong>\uff1a{escape(props["footer_hint"])}</div>'
            '<div class="distribution-footer-hint">\u60ac\u505c\u8282\u70b9\u67e5\u770b\u539f\u8bdd \u00b7 \u70b9\u51fb\u56fe\u4f8b\u6216\u86c7\u5f62\u7ebf\u5207\u5230\u5bf9\u5e94\u753b\u50cf</div>'
            '</div>'
        )
    return (
        f'<div class="distribution-header">'
        f'<div class="distribution-title">{escape(props["title"])}</div>'
        f'<div class="distribution-subtitle">{escape(props["subtitle"])}</div>'
        f'<div class="distribution-legend">{legend}</div>'
        f'</div>'
        f'{_render_chart_svg(props["value_variables"], props["personas"])}'
        f'{footer}'
    )
