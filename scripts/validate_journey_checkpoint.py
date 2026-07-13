#!/usr/bin/env python3
"""Validate the user-confirmed journey checkpoint against 03 and 05."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"jsonschema is required: {exc}")

from scripts.path_utils import resolve_process_dir

JOURNEY_TYPES = frozenset({"tob_journey_l1", "tob_journey_l2", "journey_2c"})
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "04-journeys.schema.json"
COMPONENT_SCHEMA_DIR = Path(__file__).resolve().parent / "components" / "schemas"
JOURNEY_CONFIRMATION_PHRASE = "确认旅程内容"
REJECTION_OR_SKIP_RE = re.compile(
    r"(?:不确认|先不确认|暂不确认|取消确认|别确认|不要确认|跳过确认|"
    r"不看了|看不懂|看得头晕|直接继续|你继续吧)", re.I,
)


def _journeys_sha256(journeys: list[dict[str, Any]]) -> str:
    payload = json.dumps(journeys, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _presentation_inventory(journeys: list[dict[str, Any]]) -> dict[str, Any]:
    stage_count = 0
    content_item_count = 0
    evidence_binding_count = 0
    journey_ids: list[str] = []
    for journey in journeys:
        persona_id = str(journey.get("persona_id") or "")
        component_type = str(journey.get("component_type") or "")
        journey_ids.append(f"{persona_id}|{component_type}")
        props = journey.get("props") or {}
        stages = props.get("stages") or []
        stage_count += len(stages)
        if component_type in {"tob_journey_l1", "tob_journey_l2"}:
            content_item_count += len(props.get("lanes") or [])
            content_item_count += len(props.get("nodes") or [])
            content_item_count += len(props.get("edges") or [])
            content_item_count += len(props.get("focuses") or [])
            content_item_count += sum(len(items or []) for items in props.get("tools_touchpoints") or [])
        elif component_type == "journey_2c":
            content_item_count += len(props.get("dimensions") or [])
            content_item_count += sum(len(row or []) for row in props.get("cells") or [])
            content_item_count += len(props.get("emotion") or [])
        evidence_binding_count += len(journey.get("evidence_bindings") or [])
    return {
        "journey_ids_presented": journey_ids,
        "journey_count": len(journeys),
        "stage_count": stage_count,
        "content_item_count": content_item_count,
        "evidence_binding_count": evidence_binding_count,
        "journeys_sha256": _journeys_sha256(journeys),
    }


def build_presentation_review(data: dict[str, Any]) -> dict[str, Any]:
    journeys = data.get("journeys") or []
    applicable = data.get("status") != "not_applicable"
    return {
        "confirmation_kind": "full_journey_content" if applicable else "no_journey_decision",
        "full_content_presented": applicable,
        **_presentation_inventory(journeys),
    }


def _normalized(value: object) -> str:
    return re.sub(r"[\s`*_#>|：:，,。.!！?？（）()\[\]{}\-_/\\]+", "", str(value)).lower()


def required_journey_md_values(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return every journey value that must have been visible in 04-journeys.md."""
    required: list[tuple[str, str]] = []

    def add(path: str, value: object) -> None:
        text = str(value or "").strip()
        if text and len(_normalized(text)) >= 1:
            required.append((path, text))

    for j_index, journey in enumerate(data.get("journeys") or []):
        prefix = f"journeys[{j_index}]"
        add(f"{prefix}.persona_id", journey.get("persona_id"))
        add(f"{prefix}.component_type", journey.get("component_type"))
        props = journey.get("props") or {}
        for key in ("banner_title", "banner_subtitle", "title", "subtitle", "note"):
            add(f"{prefix}.props.{key}", props.get(key))
        for s_index, stage in enumerate(props.get("stages") or []):
            if isinstance(stage, dict):
                add(f"{prefix}.stages[{s_index}].id", stage.get("id"))
                add(f"{prefix}.stages[{s_index}].name", stage.get("name"))
                for sub_index, substage in enumerate(stage.get("subStages") or []):
                    add(f"{prefix}.stages[{s_index}].subStages[{sub_index}]", substage)
            else:
                add(f"{prefix}.stages[{s_index}]", stage)
        for lane_index, lane in enumerate(props.get("lanes") or []):
            if isinstance(lane, dict):
                add(f"{prefix}.lanes[{lane_index}].id", lane.get("id"))
                add(f"{prefix}.lanes[{lane_index}].name", lane.get("name"))
                add(f"{prefix}.lanes[{lane_index}].tag", lane.get("tag"))
        for node_index, node in enumerate(props.get("nodes") or []):
            if isinstance(node, dict):
                for key in ("id", "lane", "stage", "type", "label"):
                    add(f"{prefix}.nodes[{node_index}].{key}", node.get(key))
        for edge_index, edge in enumerate(props.get("edges") or []):
            if isinstance(edge, dict):
                add(f"{prefix}.edges[{edge_index}]", f"{edge.get('from')} → {edge.get('to')}")
                add(f"{prefix}.edges[{edge_index}].branch", edge.get("branch"))
                add(f"{prefix}.edges[{edge_index}].style", edge.get("style"))
        for focus_index, focus in enumerate(props.get("focuses") or []):
            if not isinstance(focus, dict):
                continue
            for key in ("title", "body", "evidence"):
                add(f"{prefix}.focuses[{focus_index}].{key}", focus.get(key))
            for card_index, card in enumerate(focus.get("cards") or []):
                if isinstance(card, dict):
                    for key in ("title", "body", "evidence"):
                        add(f"{prefix}.focuses[{focus_index}].cards[{card_index}].{key}", card.get(key))
        for stage_index, tools in enumerate(props.get("tools_touchpoints") or []):
            for tool_index, tool in enumerate(tools or []):
                add(f"{prefix}.tools_touchpoints[{stage_index}][{tool_index}]", tool)
        for dim_index, dimension in enumerate(props.get("dimensions") or []):
            add(f"{prefix}.dimensions[{dim_index}]", dimension)
        for row_index, row in enumerate(props.get("cells") or []):
            for cell_index, cell in enumerate(row or []):
                if not isinstance(cell, dict):
                    continue
                for key in ("keyword", "summary", "frequency"):
                    add(f"{prefix}.cells[{row_index}][{cell_index}].{key}", cell.get(key))
                for tag_index, tag in enumerate(cell.get("touchpoints") or []):
                    add(f"{prefix}.cells[{row_index}][{cell_index}].touchpoints[{tag_index}]", tag)
                for quote_index, quote in enumerate(cell.get("evidence_quotes") or []):
                    if isinstance(quote, dict):
                        add(f"{prefix}.cells[{row_index}][{cell_index}].evidence[{quote_index}].quote", quote.get("quote"))
                        add(f"{prefix}.cells[{row_index}][{cell_index}].evidence[{quote_index}].source", quote.get("source"))
        for emotion_index, emotion in enumerate(props.get("emotion") or []):
            if isinstance(emotion, dict):
                for key in ("stage_label", "level", "emoji"):
                    add(f"{prefix}.emotion[{emotion_index}].{key}", emotion.get(key))
        for binding_index, binding in enumerate(journey.get("evidence_bindings") or []):
            if not isinstance(binding, dict):
                continue
            add(f"{prefix}.evidence_bindings[{binding_index}].target", binding.get("target"))
            add(f"{prefix}.evidence_bindings[{binding_index}].quote_or_basis", binding.get("quote_or_basis"))
            for source_index, source_id in enumerate(binding.get("source_ids") or []):
                add(f"{prefix}.evidence_bindings[{binding_index}].source_ids[{source_index}]", source_id)

    unique: dict[tuple[str, str], tuple[str, str]] = {}
    for path, value in required:
        unique.setdefault((path, _normalized(value)), (path, value))
    return list(unique.values())


def journey_presentation_errors(md_text: str, data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    try:
        from scripts.journey_alignment import alignment_review_errors
    except ImportError:
        from journey_alignment import alignment_review_errors  # type: ignore
    errors.extend(alignment_review_errors(data))
    exact_reply = str(data.get("confirmation_user_message") or "")
    if JOURNEY_CONFIRMATION_PHRASE not in exact_reply or REJECTION_OR_SKIP_RE.search(exact_reply):
        errors.append({
            "code": "JOURNEY_CONTENT_CONFIRMATION_MISSING",
            "path": "confirmation_user_message",
            "message": "旅程范围选择、拒绝审阅或要求继续都不能确认内容；用户原话必须明确且无矛盾地包含‘确认旅程内容’。",
        })
    expected_review = build_presentation_review(data)
    if data.get("presentation_review") != expected_review:
        errors.append({
            "code": "JOURNEY_PRESENTATION_INVENTORY_MISMATCH",
            "path": "presentation_review",
            "message": f"presentation_review 必须与旅程正文逐项计数和哈希一致：{expected_review}",
        })
    if data.get("status") == "not_applicable":
        reason = str(data.get("not_applicable_reason") or "").strip()
        if reason and _normalized(reason) not in _normalized(md_text):
            errors.append({
                "code": "JOURNEY_MD_CONTENT_INCOMPLETE",
                "path": "04-journeys.md",
                "message": "不生成旅程时，MD 必须展示用户确认的不生成原因。",
            })
        return errors

    expected_digest = _journeys_sha256(data.get("journeys") or [])
    marker = re.search(r"<!--\s*机器内容指纹：([0-9a-f]{64})\s*-->", md_text)
    required_sections = ["## 阅读导航", "## 旅程总览地图", "### 一眼看全局"]
    research_type = str((data.get("context_snapshot") or {}).get("research_type") or "")
    if research_type in {"toB", "toD"}:
        required_sections.extend(["### 你现在在这里", "### 角色 × 阶段责任矩阵"])
    missing_sections = [section for section in required_sections if section not in md_text]
    if not marker or marker.group(1) != expected_digest or missing_sections:
        errors.append({
            "code": "JOURNEY_MD_CONTENT_INCOMPLETE",
            "path": "04-journeys.md",
            "message": (
                "04-journeys.md 未由当前结构化旅程生成，或缺少全局导航。"
                f"内容指纹应为 {expected_digest}；缺少章节：{missing_sections}。"
            ),
        })
    return errors


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} root must be an object")
    return data


def _schema_errors(data: dict[str, Any]) -> list[dict[str, str]]:
    schema = _load_object(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors: list[dict[str, str]] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append({
            "code": "JOURNEY_CHECKPOINT_SCHEMA",
            "path": path,
            "message": error.message,
        })
    return errors


def _component_schema_errors(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for index, journey in enumerate(data.get("journeys") or []):
        component_type = journey.get("component_type")
        if component_type not in JOURNEY_TYPES:
            continue
        schema = _load_object(COMPONENT_SCHEMA_DIR / f"{component_type}.json")
        validator = Draft202012Validator(schema)
        for error in sorted(
            validator.iter_errors(journey.get("props")),
            key=lambda item: list(item.absolute_path),
        ):
            suffix = ".".join(str(part) for part in error.absolute_path)
            path = f"journeys[{index}].props" + (f".{suffix}" if suffix else "")
            errors.append({
                "code": "JOURNEY_COMPONENT_SCHEMA",
                "path": path,
                "message": f"{component_type}: {error.message}",
            })
    return errors


def _journeys_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    journeys: list[dict[str, Any]] = []
    for persona in report.get("personas") or []:
        persona_id = _base_persona_id(str(persona.get("id") or ""))
        for component in persona.get("components") or []:
            component_type = component.get("type")
            if component_type in JOURNEY_TYPES:
                journeys.append({
                    "persona_id": persona_id,
                    "component_type": component_type,
                    "props": component.get("props") or {},
                })
    return journeys


def _canonical(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparable = [
        {"persona_id": item.get("persona_id"), "component_type": item.get("component_type"), "props": item.get("props") or {}}
        for item in items
    ]
    return sorted(
        comparable,
        key=lambda item: (str(item.get("persona_id")), str(item.get("component_type"))),
    )


def _scope_errors(data: dict[str, Any], alignment: dict[str, Any] | None) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    journeys = data.get("journeys") or []
    scope = data.get("scope")
    overall = [item for item in journeys if item.get("component_type") == "tob_journey_l1"]
    individual = [item for item in journeys if item.get("component_type") != "tob_journey_l1"]
    pairs = [(item.get("persona_id"), item.get("component_type")) for item in journeys]
    if len(pairs) != len(set(pairs)):
        errors.append({"code": "JOURNEY_DUPLICATE", "path": "journeys", "message": "同一 persona_id 与 component_type 只能出现一次。"})

    valid_shape = {
        "none": not journeys,
        "single-persona": len(individual) == 1 and not overall,
        "per-persona": bool(individual) and not overall,
        "overall-only": len(overall) == 1 and not individual,
        "overall-and-per-persona": len(overall) == 1 and bool(individual),
    }.get(scope, False)
    if not valid_shape:
        errors.append({"code": "JOURNEY_SCOPE_SHAPE", "path": "scope", "message": f"scope={scope!r} 与 journeys 中的总体/单画像组件数量不一致。"})

    if alignment:
        research_type = str(alignment.get("research_type") or alignment.get("persona_type") or "")
        component_types = {item.get("component_type") for item in journeys}
        if research_type == "toC" and component_types - {"journey_2c"}:
            errors.append({"code": "JOURNEY_TYPE_MISMATCH", "path": "journeys", "message": "toC 只能使用 journey_2c。"})
        if research_type in {"toB", "toD"} and component_types & {"journey_2c"}:
            errors.append({"code": "JOURNEY_TYPE_MISMATCH", "path": "journeys", "message": f"{research_type} 不能使用 journey_2c。"})
        requested_scope = (alignment.get("add_on_pages") or {}).get("journey_scope")
        if requested_scope == "none" and scope != "none":
            errors.append({"code": "JOURNEY_SCOPE_ALIGNMENT", "path": "scope", "message": "03 的 journey_scope=none，04 也必须为 none。"})
        if requested_scope == "L1_and_L2" and scope != "overall-and-per-persona":
            errors.append({"code": "JOURNEY_SCOPE_ALIGNMENT", "path": "scope", "message": "03 的 L1_and_L2 必须固化为 overall-and-per-persona。"})
        if requested_scope == "L1_only" and scope != "overall-only":
            errors.append({"code": "JOURNEY_SCOPE_ALIGNMENT", "path": "scope", "message": "03 的 L1_only 必须固化为 overall-only。"})
        if requested_scope == "L2_only" and scope not in {"single-persona", "per-persona"}:
            errors.append({"code": "JOURNEY_SCOPE_ALIGNMENT", "path": "scope", "message": "03 的 L2_only 只能固化为 single-persona 或 per-persona。"})
    return errors


def _required_targets(journey: dict[str, Any]) -> set[str]:
    props = journey.get("props") or {}
    kind = journey.get("component_type")
    targets: set[str] = set()
    if kind in {"tob_journey_l1", "tob_journey_l2"}:
        targets |= {f"stage:{item.get('id')}" for item in props.get("stages") or [] if isinstance(item, dict)}
        targets |= {f"node:{item.get('id')}" for item in props.get("nodes") or [] if isinstance(item, dict)}
        targets |= {f"edge:{item.get('from')}>{item.get('to')}" for item in props.get("edges") or [] if isinstance(item, dict)}
        targets |= {f"focus:{i}" for i, _ in enumerate(props.get("focuses") or [])}
        targets |= {f"tool:{stage_index}:{tool_index}" for stage_index, tools in enumerate(props.get("tools_touchpoints") or []) for tool_index, _ in enumerate(tools or [])}
    elif kind == "journey_2c":
        targets |= {f"stage:{i}" for i, _ in enumerate(props.get("stages") or [])}
        targets |= {f"cell:{r}:{c}" for r, row in enumerate(props.get("cells") or []) for c, _ in enumerate(row or [])}
        targets |= {f"emotion:{i}" for i, _ in enumerate(props.get("emotion") or [])}
    return targets


def _base_persona_id(persona_id: str) -> str:
    return re.sub(r"-(?:journey|core|detail(?:-\d+)?)$", "", persona_id)


def _evidence_binding_errors(data: dict[str, Any], process_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    manifest_path = process_dir / "source-manifest.json"
    manifest = _load_object(manifest_path) if manifest_path.is_file() else {}
    source_rules = {str(item.get("source_id")): item for item in manifest.get("sources") or [] if isinstance(item, dict)}
    tiers = {source_id: item.get("evidence_tier") for source_id, item in source_rules.items()}
    for index, journey in enumerate(data.get("journeys") or []):
        persona_id = str(journey.get("persona_id") or "")
        bindings = journey.get("evidence_bindings") or []
        by_target: dict[str, list[dict]] = {}
        for binding in bindings:
            if isinstance(binding, dict):
                by_target.setdefault(str(binding.get("target") or ""), []).append(binding)
                for source_id in binding.get("source_ids") or []:
                    if source_id not in tiers:
                        errors.append({"code": "JOURNEY_EVIDENCE_SOURCE_UNKNOWN", "path": f"journeys[{index}].evidence_bindings", "message": f"source_id {source_id} 未在 source-manifest.json 登记。"})
                    elif binding.get("evidence_type") in {"primary", "supplemental"} and tiers[source_id] != binding.get("evidence_type"):
                        errors.append({"code": "JOURNEY_EVIDENCE_TIER_MISMATCH", "path": f"journeys[{index}].evidence_bindings", "message": f"{source_id} 的清单层级为 {tiers[source_id]}。"})
                    elif persona_id != "journey-l1" and _base_persona_id(persona_id) not in set(map(str, source_rules[source_id].get("assigned_personas") or [])):
                        errors.append({"code": "JOURNEY_EVIDENCE_CROSS_PERSONA", "path": f"journeys[{index}].evidence_bindings", "message": f"{source_id} 未分配给 {persona_id}，不能支撑该画像旅程。"})
        missing = sorted(_required_targets(journey) - set(by_target))
        if missing:
            errors.append({"code": "JOURNEY_EVIDENCE_TARGET_MISSING", "path": f"journeys[{index}]", "message": f"{len(missing)} 个旅程元素没有证据绑定：{missing[:8]}"})
        for target, target_bindings in by_target.items():
            if target.startswith(("node:", "cell:", "focus:", "tool:")):
                material = [b for b in target_bindings if b.get("evidence_type") in {"primary", "supplemental"}]
                if not material:
                    errors.append({"code": "JOURNEY_FACT_WITHOUT_MATERIAL", "path": f"journeys[{index}].{target}", "message": "行为、单元格和痛点必须有主访谈或补充材料证据。"})
                if material and not any(b.get("evidence_type") == "primary" for b in material):
                    errors.append({"code": "JOURNEY_SUPPLEMENTAL_ONLY", "path": f"journeys[{index}].{target}", "message": "补充材料不能单独定义核心旅程内容，至少需要一条主访谈证据。"})
    return errors


def validate_journey_checkpoint(process_dir: Path) -> list[dict[str, str]]:
    process_dir = resolve_process_dir(Path(process_dir))
    journey_path = process_dir / "04-journeys.json"
    journey_md_path = process_dir / "04-journeys.md"
    report_path = process_dir / "05-report.json"
    alignment_path = process_dir / "03-field-alignment.json"
    errors: list[dict[str, str]] = []

    if not journey_path.is_file():
        return [{
            "code": "JOURNEY_CHECKPOINT_MISSING",
            "path": journey_path.name,
            "message": "04-journeys.json is required before report assembly.",
        }]

    try:
        journey_data = _load_object(journey_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [{
            "code": "JOURNEY_CHECKPOINT_INVALID",
            "path": journey_path.name,
            "message": str(exc),
        }]

    errors.extend(_schema_errors(journey_data))
    errors.extend(_component_schema_errors(journey_data))
    errors.extend(_evidence_binding_errors(journey_data, process_dir))
    if not journey_md_path.is_file():
        errors.append({
            "code": "JOURNEY_MD_MISSING",
            "path": journey_md_path.name,
            "message": "04-journeys.md is required and must show the complete journey content.",
        })
    else:
        errors.extend(journey_presentation_errors(
            journey_md_path.read_text(encoding="utf-8"), journey_data
        ))

    alignment: dict[str, Any] | None = None
    if alignment_path.is_file():
        try:
            alignment = _load_object(alignment_path)
            journey_requested = bool((alignment.get("add_on_pages") or {}).get("journey"))
            if journey_requested and journey_data.get("status") == "not_applicable":
                errors.append({
                    "code": "JOURNEY_ALIGNMENT_MISMATCH",
                    "path": "04-journeys.json",
                    "message": "03 requests a journey but 04 marks it not_applicable.",
                })
            if not journey_requested and journey_data.get("status") != "not_applicable":
                errors.append({
                    "code": "JOURNEY_ALIGNMENT_MISMATCH",
                    "path": "04-journeys.json",
                    "message": "03 disables journeys but 04 contains confirmed journey data.",
                })
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append({
                "code": "JOURNEY_ALIGNMENT_INVALID",
                "path": alignment_path.name,
                "message": str(exc),
            })

    errors.extend(_scope_errors(journey_data, alignment))

    if report_path.is_file():
        try:
            report = _load_object(report_path)
            confirmed = _canonical(journey_data.get("journeys") or [])
            rendered = _canonical(_journeys_from_report(report))
            if confirmed != rendered:
                errors.append({
                    "code": "JOURNEY_REPORT_MISMATCH",
                    "path": report_path.name,
                    "message": (
                        "Journey components in 05-report.json must exactly match "
                        "the user-confirmed journeys in 04-journeys.json."
                    ),
                })
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append({
                "code": "JOURNEY_REPORT_INVALID",
                "path": report_path.name,
                "message": str(exc),
            })

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate 04 journey confirmation and 05 reuse.")
    parser.add_argument("--workdir", required=True, help="Run directory or process directory.")
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    errors = validate_journey_checkpoint(process_dir)
    print(json.dumps({
        "valid": not errors,
        "process_dir": str(process_dir),
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
