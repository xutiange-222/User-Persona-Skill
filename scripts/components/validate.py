#!/usr/bin/env python3
"""P8 F 阶段:components JSON 事前校验。

CLI:
    python scripts/validate_components_json.py path/to/05-report.json
    python -m scripts.components.validate path/to/05-report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.components.visual_system import load_visual_system, toc_palette_for_accent

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


def _check_tob_journey_structure(props: dict, base_path: str) -> list[dict]:
    """Validate identifiers and normalize-safe slot semantics before rendering."""
    issues: list[dict] = []
    stages = props.get("stages") if isinstance(props.get("stages"), list) else []
    lanes = props.get("lanes") if isinstance(props.get("lanes"), list) else []
    nodes = props.get("nodes") if isinstance(props.get("nodes"), list) else []

    for field, values in (("stages", stages), ("lanes", lanes), ("nodes", nodes)):
        ids = [item.get("id") for item in values if isinstance(item, dict)]
        duplicates = sorted({value for value in ids if value is not None and ids.count(value) > 1})
        if duplicates:
            issues.append({
                "level": "ERROR",
                "code": "P8-JOURNEY-DUPLICATE-ID",
                "path": f"{base_path}.props.{field}",
                "message": f"{field}[].id 必须唯一；重复值：{duplicates}",
            })

    by_cell: dict[tuple[str, str], list[int]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        lane = node.get("lane")
        stage = node.get("stage")
        slot = node.get("slot")
        if isinstance(lane, str) and isinstance(stage, str) and isinstance(slot, int):
            by_cell.setdefault((lane, stage), []).append(slot)
    for (lane, stage), slots in by_cell.items():
        ordered = sorted(slots)
        if ordered != list(range(len(ordered))):
            issues.append({
                "level": "WARN",
                "code": "P8-JOURNEY-SPARSE-SLOTS",
                "path": f"{base_path}.props.nodes",
                "message": (
                    f"lane={lane}, stage={stage} 的 slot 为 {ordered}；"
                    "渲染器会按顺序压紧，建议保存为连续 0..N-1。"
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


def _check_visual_spec_alignment(report: dict, process_dir: Path) -> list[dict]:
    """Ensure 05-report.json.metadata.visual_spec matches 03-field-alignment.json."""
    issues: list[dict] = []
    alignment_path = process_dir / "03-field-alignment.json"
    if not alignment_path.is_file():
        return issues

    try:
        alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return issues

    alignment_spec = alignment.get("visual_spec")
    report_spec = (report.get("metadata") or {}).get("visual_spec")
    if not isinstance(alignment_spec, dict):
        return issues

    if not isinstance(report_spec, dict):
        issues.append({
            "level": "ERROR",
            "code": "P8-VISUAL-SPEC-MISSING",
            "path": "metadata.visual_spec",
            "message": "05-report.json 必须包含 metadata.visual_spec,并与 03-field-alignment.json 保持一致",
        })
        return issues

    for key in ("template_id", "palette_id"):
        expected = str(alignment_spec.get(key) or "").strip()
        actual = str(report_spec.get(key) or "").strip()
        if expected and actual != expected:
            issues.append({
                "level": "ERROR",
                "code": "P8-VISUAL-SPEC-MISMATCH",
                "path": f"metadata.visual_spec.{key}",
                "message": (
                    f"metadata.visual_spec.{key}={actual!r} 与 03-field-alignment.json 的 {expected!r} 不一致"
                ),
            })

    alignment_map = alignment_spec.get("persona_palette_map")
    report_map = report_spec.get("persona_palette_map")
    if isinstance(alignment_map, dict) and alignment_map and alignment_map != report_map:
        issues.append({
            "level": "ERROR",
            "code": "P8-VISUAL-SPEC-MISMATCH",
            "path": "metadata.visual_spec.persona_palette_map",
            "message": "05-report.json 的 persona_palette_map 与 03-field-alignment.json 不一致",
        })

    return issues


def _base_persona_id(persona_id: str) -> str:
    return re.sub(r"-(?:detail(?:-\d+)?|journey|core)$", "", persona_id)


def _check_toc_palette_mapping(report: dict) -> list[dict]:
    """Lock one 2C persona to one palette across portrait, detail, journey and overview."""
    issues: list[dict] = []
    metadata = report.get("metadata") or {}
    if metadata.get("theme") != "2c":
        return issues

    if metadata.get("density") != "low":
        issues.append({
            "level": "ERROR",
            "code": "P8-2C-DENSITY",
            "path": "metadata.density",
            "message": "2C 报告必须使用 density=low",
        })

    visual_spec = metadata.get("visual_spec") or {}
    palette_map = visual_spec.get("persona_palette_map")
    if not isinstance(palette_map, dict):
        palette_map = {}

    grouped: dict[str, list[tuple[int, str, str]]] = {}
    palette_by_base: dict[str, str] = {}
    for idx, persona in enumerate(report.get("personas", [])):
        if not isinstance(persona, dict):
            continue
        layout = str(persona.get("layout") or "")
        if layout not in {"layout-2c-portrait", "layout-2c-detail", "layout-2c-journey"}:
            continue
        persona_id = str(persona.get("id") or "")
        base_id = _base_persona_id(persona_id)
        accent = str(persona.get("accent") or "")
        try:
            style, _values = toc_palette_for_accent(accent)
            pack = load_visual_system()["themes"]["2c"]["palette_packs"][style]
            palette_id = str(pack["palette_id"])
            palette_by_base[base_id] = palette_id
        except (KeyError, ValueError) as exc:
            issues.append({
                "level": "ERROR",
                "code": "P8-2C-PALETTE-UNKNOWN",
                "path": f"personas[{idx}].accent",
                "message": str(exc),
            })
            palette_id = ""
        grouped.setdefault(base_id, []).append((idx, accent, palette_id))

    for base_id, entries in grouped.items():
        accents = {accent for _idx, accent, _palette in entries}
        palettes = {palette for _idx, _accent, palette in entries if palette}
        if len(accents) > 1 or len(palettes) > 1:
            issues.append({
                "level": "ERROR",
                "code": "P8-2C-PALETTE-PAGE-MISMATCH",
                "path": base_id,
                "message": f"{base_id} 的画像页、详情页、旅程页必须使用同一 accent 与 palette pack",
            })

    template_id = str(visual_spec.get("template_id") or "")
    requires_map = template_id == "2c-complex-distribution-report" or len(grouped) > 1
    if requires_map and not palette_map:
        issues.append({
            "level": "ERROR",
            "code": "P8-2C-PALETTE-MAP-MISSING",
            "path": "metadata.visual_spec.persona_palette_map",
            "message": "2C 多画像报告必须显式记录 persona_palette_map",
        })
    if palette_map:
        missing = sorted(set(grouped) - set(palette_map))
        extra = sorted(set(palette_map) - set(grouped))
        if missing or extra:
            issues.append({
                "level": "ERROR",
                "code": "P8-2C-PALETTE-MAP-KEYS",
                "path": "metadata.visual_spec.persona_palette_map",
                "message": f"persona_palette_map 与画像基础 id 不一致; missing={missing}, extra={extra}",
            })
        for base_id, expected_palette in palette_by_base.items():
            actual_palette = palette_map.get(base_id)
            if actual_palette is not None and actual_palette != expected_palette:
                issues.append({
                    "level": "ERROR",
                    "code": "P8-2C-PALETTE-MAP-MISMATCH",
                    "path": f"metadata.visual_spec.persona_palette_map.{base_id}",
                    "message": f"{base_id} 的 accent 对应 {expected_palette},映射却是 {actual_palette}",
                })

    expected_count = len(grouped)
    if expected_count and metadata.get("persona_count") != expected_count:
        issues.append({
            "level": "ERROR",
            "code": "P8-2C-PERSONA-COUNT",
            "path": "metadata.persona_count",
            "message": f"persona_count 应等于画像基础角色数 {expected_count}",
        })

    packs = load_visual_system()["themes"]["2c"]["palette_packs"]
    chart_color_by_palette = {
        pack["palette_id"]: str(pack["chart_color"]).lower()
        for pack in packs.values()
    }
    for p_idx, persona in enumerate(report.get("personas", [])):
        if not isinstance(persona, dict) or persona.get("layout") != "layout-distribution-multi":
            continue
        for c_idx, component in enumerate(persona.get("components", [])):
            if not isinstance(component, dict) or component.get("type") != "distribution_multi":
                continue
            for item_idx, item in enumerate((component.get("props") or {}).get("personas", [])):
                if not isinstance(item, dict):
                    continue
                base_id = str(item.get("id") or "")
                palette_id = palette_map.get(base_id)
                expected_color = chart_color_by_palette.get(palette_id)
                actual_color = str(item.get("color") or "").lower()
                if expected_color and actual_color != expected_color:
                    issues.append({
                        "level": "ERROR",
                        "code": "P8-2C-DISTRIBUTION-PALETTE-MISMATCH",
                        "path": f"personas[{p_idx}].components[{c_idx}].props.personas[{item_idx}].color",
                        "message": f"分布图 {base_id} 应使用 {palette_id} 的 {expected_color.upper()},当前为 {actual_color}",
                    })

    return issues


def validate_report_json(report: dict, process_dir: Path | None = None) -> list[dict]:
    issues: list[dict] = []

    if process_dir is not None:
        try:
            from scripts.resolve_content_refs import resolve_report_content_refs, validate_report_content_refs
            for item in validate_report_content_refs(report, process_dir):
                issues.append({"level": "ERROR", **item})
            report = resolve_report_content_refs(report, process_dir)
        except Exception as exc:
            issues.append({"level": "ERROR", "code": "P8-CONTENT-REF", "path": "05-report.json", "message": str(exc)})

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
            if comp_type in {"tob_journey_l1", "tob_journey_l2"}:
                issues.extend(_check_tob_journey_structure(props, base_path))

    issues.extend(_check_theme_layout(report))
    issues.extend(_check_overview_components(report))
    issues.extend(_check_toc_palette_mapping(report))

    if process_dir is not None:
        issues.extend(_check_visual_spec_alignment(report, process_dir))
        try:
            from scripts.privacy_guard import validate_privacy_in_report
        except ImportError:
            from privacy_guard import validate_privacy_in_report
        issues.extend(validate_privacy_in_report(report, process_dir))

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
    parser.add_argument(
        "--workdir",
        default=None,
        help="过程稿或项目运行目录(用于真名泄露检查)",
    )
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

    pdir = Path(args.workdir).resolve() if args.workdir else None
    issues = validate_report_json(report, pdir)
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
