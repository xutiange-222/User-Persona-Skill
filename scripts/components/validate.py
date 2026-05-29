#!/usr/bin/env python3
"""P8 F 阶段:components JSON 事前校验。

CLI:
    python scripts/validate_components_json.py path/to/05-report.json
    python -m scripts.components.validate path/to/05-report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError as e:
    print(json.dumps({
        "success": False,
        "issues": [{
            "level": "ERROR",
            "code": "P8-NO-JSONSCHEMA",
            "path": "",
            "message": f"未安装 jsonschema 库,无法做事前校验:{e}",
        }],
    }, ensure_ascii=False, indent=2))
    sys.exit(1)

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


def _load_schema(name: str) -> dict:
    p = SCHEMAS_DIR / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"schema 文件不存在:{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _format_path(absolute_path) -> str:
    parts = []
    for x in absolute_path:
        if isinstance(x, int):
            parts.append(f"[{x}]")
        else:
            if parts:
                parts.append(f".{x}")
            else:
                parts.append(str(x))
    return "".join(parts) or "$"


_OVERVIEW_SLIDE_IDS = frozenset({"matrix", "distribution"})

_TOB_THEMES = frozenset({"2b", "2d"})
_TOC_THEMES = frozenset({"2c"})

_TOB_FORBIDDEN_LAYOUTS = frozenset({
    "layout-2c-portrait",
    "layout-2c-detail",
    "layout-2c-journey",
})
_TOC_FORBIDDEN_LAYOUTS = frozenset({
    "layout-2b-grid",
    "layout-2b-grid-detail",
    "layout-2b-journey",
})

_TOB_FORBIDDEN_COMPONENTS = frozenset({
    "identity_card",
    "section_blocks_grid",
    "journey_2c",
})
_TOC_FORBIDDEN_COMPONENTS = frozenset({
    "identity_panel",
    "tob_journey_l1",
    "tob_journey_l2",
})

_OVERVIEW_FORBIDDEN_COMPONENTS = frozenset({
    "identity_card",
    "identity_panel",
    "section_blocks_grid",
    "persona_quote_pull",
    "journey_2c",
    "tob_journey_l1",
    "tob_journey_l2",
    "resp_rings",
    "painpoint_list",
    "collab_flow",
    "scenario_grid",
    "ai_scenario_grid",
})


def _check_journey_2c_shape(props: dict, base_path: str) -> list[dict]:
    issues: list[dict] = []
    dimensions = props.get("dimensions")
    stages = props.get("stages")
    cells = props.get("cells")
    emotion = props.get("emotion")

    if not isinstance(dimensions, list) or not isinstance(stages, list):
        return issues
    if not isinstance(cells, list):
        return issues

    n_dims = len(dimensions)
    n_stages = len(stages)
    n_rows = len(cells)
    inner_lens = [len(row) for row in cells if isinstance(row, list)]

    shape_ok = (
        n_rows == n_dims
        and inner_lens
        and all(length == n_stages for length in inner_lens)
    )
    if not shape_ok:
        inner_repr = f"{inner_lens[0]}列" if inner_lens and len(set(inner_lens)) == 1 else "列数不一"
        issues.append({
            "level": "ERROR",
            "code": "P8-JOURNEY-CELLS-SHAPE",
            "path": f"{base_path}.props.cells",
            "message": (
                f"journey_2c.cells 应为「维度×阶段」({n_dims}×{n_stages})，"
                f"当前为 {n_rows}×{inner_repr}；外层对齐 dimensions，内层对齐 stages"
            ),
        })

    if isinstance(emotion, list) and len(emotion) != n_stages:
        issues.append({
            "level": "ERROR",
            "code": "P8-JOURNEY-CELLS-SHAPE",
            "path": f"{base_path}.props.emotion",
            "message": (
                f"journey_2c.emotion 应与 stages 对齐({n_stages} 项)，当前为 {len(emotion)} 项"
            ),
        })

    return issues


def _check_tob_journey_l2_tools(props: dict, base_path: str) -> list[dict]:
    issues: list[dict] = []
    tools = props.get("tools_touchpoints")
    stages = props.get("stages")
    if tools is None or not isinstance(stages, list):
        return issues
    if len(tools) != len(stages):
        issues.append({
            "level": "ERROR",
            "code": "P8-L2-TOOLS-LEN",
            "path": f"{base_path}.props.tools_touchpoints",
            "message": (
                f"tob_journey_l2.tools_touchpoints 应与 stages 对齐({len(stages)} 项)，"
                f"当前为 {len(tools)} 项"
            ),
        })
    return issues


def _is_overview_persona(persona: dict) -> bool:
    persona_id = persona.get("id")
    if persona_id in _OVERVIEW_SLIDE_IDS:
        return True
    layout = persona.get("layout", "")
    return layout in {"layout-matrix-2d", "layout-distribution-multi"}


def _check_theme_layout(report: dict) -> list[dict]:
    issues: list[dict] = []
    metadata = report.get("metadata", {})
    if not isinstance(metadata, dict):
        return issues

    theme = metadata.get("theme")
    if theme not in _TOB_THEMES | _TOC_THEMES:
        return issues

    for p_idx, persona in enumerate(report.get("personas", [])):
        if not isinstance(persona, dict) or _is_overview_persona(persona):
            continue

        base_path = f"personas[{p_idx}]"
        layout = persona.get("layout", "")
        components = persona.get("components", [])
        if not isinstance(components, list):
            continue

        if theme in _TOB_THEMES:
            if layout in _TOB_FORBIDDEN_LAYOUTS:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-THEME-LAYOUT-MISMATCH",
                    "path": f"{base_path}.layout",
                    "message": (
                        f"metadata.theme={theme} 时禁止使用 toC layout {layout}；"
                        "象限/画像子页应使用 layout-2b-grid 或 layout-2b-journey"
                    ),
                })
            for c_idx, comp in enumerate(components):
                if not isinstance(comp, dict):
                    continue
                comp_type = comp.get("type")
                if comp_type in _TOB_FORBIDDEN_COMPONENTS:
                    issues.append({
                        "level": "ERROR",
                        "code": "P8-THEME-LAYOUT-MISMATCH",
                        "path": f"{base_path}.components[{c_idx}].type",
                        "message": (
                            f"metadata.theme={theme} 时禁止使用 toC 组件 {comp_type}"
                        ),
                    })

        if theme in _TOC_THEMES:
            if layout in _TOC_FORBIDDEN_LAYOUTS:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-THEME-LAYOUT-MISMATCH",
                    "path": f"{base_path}.layout",
                    "message": (
                        f"metadata.theme={theme} 时禁止使用 toB layout {layout}；"
                        "画像子页应使用 layout-2c-portrait / layout-2c-detail / layout-2c-journey"
                    ),
                })
            for c_idx, comp in enumerate(components):
                if not isinstance(comp, dict):
                    continue
                comp_type = comp.get("type")
                if comp_type in _TOC_FORBIDDEN_COMPONENTS:
                    issues.append({
                        "level": "ERROR",
                        "code": "P8-THEME-LAYOUT-MISMATCH",
                        "path": f"{base_path}.components[{c_idx}].type",
                        "message": (
                            f"metadata.theme={theme} 时禁止使用 toB 组件 {comp_type}"
                        ),
                    })

    return issues


def _check_overview_components(report: dict) -> list[dict]:
    issues: list[dict] = []
    for p_idx, persona in enumerate(report.get("personas", [])):
        if not isinstance(persona, dict) or not _is_overview_persona(persona):
            continue
        base_path = f"personas[{p_idx}]"
        for c_idx, comp in enumerate(persona.get("components", [])):
            if not isinstance(comp, dict):
                continue
            comp_type = comp.get("type")
            if comp_type in _OVERVIEW_FORBIDDEN_COMPONENTS:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-OVERVIEW-FORBIDDEN-COMPONENT",
                    "path": f"{base_path}.components[{c_idx}].type",
                    "message": (
                        f"总览 slide({persona.get('layout', persona.get('id'))}) "
                        f"禁止使用画像/旅程组件 {comp_type}；"
                        "应仅用 matrix_2d / distribution_multi 等总览容器"
                    ),
                })
    return issues


def validate_report_json(report: dict) -> list[dict]:
    issues: list[dict] = []

    try:
        top_schema = _load_schema("report")
    except FileNotFoundError as e:
        issues.append({
            "level": "ERROR",
            "code": "P8-SCHEMA-MISSING",
            "path": "",
            "message": str(e),
        })
        return issues

    top_validator = Draft202012Validator(top_schema)
    for err in top_validator.iter_errors(report):
        issues.append({
            "level": "ERROR",
            "code": "P8-TOP-SCHEMA",
            "path": _format_path(err.absolute_path),
            "message": err.message,
        })

    for p_idx, persona in enumerate(report.get("personas", [])):
        if not isinstance(persona, dict):
            continue
        for c_idx, comp in enumerate(persona.get("components", [])):
            if not isinstance(comp, dict):
                continue
            comp_type = comp.get("type")
            props = comp.get("props", {})
            base_path = f"personas[{p_idx}].components[{c_idx}]"

            if not comp_type:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-COMPONENT-NO-TYPE",
                    "path": base_path,
                    "message": "组件缺少 type 字段",
                })
                continue

            schema_file = SCHEMAS_DIR / f"{comp_type}.json"
            if not schema_file.exists():
                issues.append({
                    "level": "ERROR",
                    "code": "P8-UNKNOWN-COMPONENT",
                    "path": base_path,
                    "message": f"未注册的组件类型:{comp_type}(找不到 schemas/{comp_type}.json)",
                })
                continue

            try:
                comp_schema = json.loads(schema_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-SCHEMA-MALFORMED",
                    "path": base_path,
                    "message": f"schema 文件解析失败:{e}",
                })
                continue

            comp_validator = Draft202012Validator(comp_schema)
            for err in comp_validator.iter_errors(props):
                issues.append({
                    "level": "ERROR",
                    "code": "P8-COMPONENT-PROPS",
                    "path": f"{base_path}.props.{_format_path(err.absolute_path)}",
                    "message": f"{comp_type}: {err.message}",
                })

            if comp_type == "journey_2c":
                issues.extend(_check_journey_2c_shape(props, base_path))
            if comp_type == "tob_journey_l2":
                issues.extend(_check_tob_journey_l2_tools(props, base_path))

    issues.extend(_check_theme_layout(report))
    issues.extend(_check_overview_components(report))

    return issues


def format_issues_for_human(issues: list[dict]) -> str:
    if not issues:
        return ""
    lines = []
    for i in issues:
        lines.append(f"  [{i.get('level','?')}] {i.get('code','?')} @ {i.get('path','?')}: {i.get('message','')}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P8 组件 JSON 事前校验")
    parser.add_argument("input", help="components JSON 文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 输出(默认人读格式)")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[ERROR] 文件不存在: {in_path}", file=sys.stderr)
        return 2

    try:
        report = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        return 2

    issues = validate_report_json(report)
    errors = [i for i in issues if i["level"] == "ERROR"]

    if args.json:
        print(json.dumps({
            "success": not errors,
            "issue_count": len(issues),
            "error_count": len(errors),
            "issues": issues,
        }, ensure_ascii=False, indent=2))
    else:
        if errors:
            print(f"[FAIL] {len(errors)} 个 ERROR:")
            print(format_issues_for_human(errors))
        else:
            print(f"[OK] schema 校验通过 ({len(issues)} 个总 issue)")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
