#!/usr/bin/env python3
"""Validate selected-field coverage from extraction through confirmed personas."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _fields_for_persona(alignment: dict, persona: dict) -> list[str]:
    mapping = alignment.get("fields_per_persona") or {}
    for key in (persona.get("id"), persona.get("name"), "默认", "default"):
        value = mapping.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def validate_content_completeness(workdir: Path) -> list[dict]:
    process_dir = resolve_process_dir(Path(workdir))
    alignment = _load(process_dir / "03-field-alignment.json")
    personas_data = _load(process_dir / "04-personas.json")
    if not alignment or not personas_data:
        return []
    manifest = _load(process_dir / "source-manifest.json")
    errors: list[dict] = []

    def add(code: str, path: str, message: str) -> None:
        errors.append({"code": code, "path": path, "message": message})

    extracted_by_source: dict[str, tuple[str, dict]] = {}
    extracted_dir = process_dir / "extracted"
    for path in extracted_dir.rglob("*.json") if extracted_dir.is_dir() else []:
        data = _load(path)
        source_id = str(data.get("_source_id") or "")
        if source_id:
            extracted_by_source[source_id] = (path.relative_to(process_dir).as_posix(), data)

    source_rules = {str(item.get("source_id")): item for item in manifest.get("sources") or [] if isinstance(item, dict)}
    personas = personas_data.get("personas") or []
    for p_idx, persona in enumerate(personas):
        if not isinstance(persona, dict):
            continue
        persona_id = str(persona.get("id") or "")
        selected = _fields_for_persona(alignment, persona)
        if not selected:
            add("CONTENT_FIELDS_UNRESOLVED", f"personas[{p_idx}]", f"03 未提供 {persona_id} 可解析的字段列表。")
            continue
        fields = persona.get("fields") or {}
        missing_04 = sorted(set(selected) - set(fields))
        if missing_04:
            add("CONTENT_FIELDS_MISSING_04", f"personas[{p_idx}].fields", f"04 缺少已确认字段：{missing_04}")
        decisions = persona.get("field_decisions") or []
        decision_map = {
            str(item.get("field") or ""): item
            for item in decisions if isinstance(item, dict)
        }
        if set(decision_map) != set(selected):
            add("CONTENT_FIELD_DECISIONS_INCOMPLETE", f"personas[{p_idx}].field_decisions", f"字段决策必须恰好覆盖 03 已确认字段：{selected}")
        component_fields = {
            str(field)
            for component in persona.get("display_components") or [] if isinstance(component, dict)
            for field in component.get("source_fields") or []
        }
        expected_in_components = {
            field for field, decision in decision_map.items()
            if decision.get("presentation") in {"full", "condensed"}
        }
        explicitly_omitted = {
            field for field, decision in decision_map.items()
            if decision.get("presentation") == "omitted"
        }
        missing_components = sorted(expected_in_components - component_fields)
        if missing_components:
            add("CONTENT_FIELDS_MISSING_COMPONENT", f"personas[{p_idx}].display_components", f"已确认字段没有进入 04 展示组件：{missing_components}")
        wrongly_included = sorted(explicitly_omitted & component_fields)
        if wrongly_included:
            add("CONTENT_OMITTED_FIELD_RENDERED", f"personas[{p_idx}].display_components", f"声明省略的字段仍被组件引用：{wrongly_included}")
        unknown_component_fields = sorted(component_fields - set(selected))
        if unknown_component_fields:
            add("CONTENT_UNCONFIRMED_FIELD_RENDERED", f"personas[{p_idx}].display_components", f"组件引用了 03 未确认字段：{unknown_component_fields}")

        members = set(map(str, persona.get("members") or []))
        for source_id in members:
            rule = source_rules.get(source_id)
            if rule and persona_id not in set(map(str, rule.get("assigned_personas") or [])):
                add("CONTENT_SOURCE_ASSIGNMENT", f"personas[{p_idx}].members", f"{source_id} 未在 source-manifest 分配给 {persona_id}。")
            extracted = extracted_by_source.get(source_id)
            if not extracted:
                add("CONTENT_EXTRACTION_MISSING", "extracted/", f"{persona_id} 的来源 {source_id} 没有抽取 JSON。")
                continue
            rel, data = extracted
            missing_fields = sorted(set(selected) - set(data))
            if missing_fields:
                add("CONTENT_EXTRACTION_FIELD_MISSING", rel, f"{source_id} 缺少字段 {missing_fields}；未提及也要显式写入。")
            if data.get("_chunk_conflicts"):
                add("CONTENT_CHUNK_CONFLICT_UNRESOLVED", rel, f"{source_id} 存在未解决的分段冲突，不能直接归并。")

        for field in selected:
            reduced_path = process_dir / "reduced" / persona_id / f"{field}.json"
            aggregate_path = process_dir / "reduced" / f"{persona_id}.json"
            aggregate = _load(aggregate_path)
            aggregate_fields = aggregate.get("fields") if isinstance(aggregate.get("fields"), dict) else {}
            if not reduced_path.is_file() and field not in aggregate_fields:
                add("CONTENT_REDUCED_FIELD_MISSING", reduced_path.relative_to(process_dir).as_posix(), f"{persona_id} 缺少字段 {field} 的归并快照；允许逐字段文件或 reduced/{persona_id}.json 聚合文件。")
    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    errors = validate_content_completeness(Path(args.workdir))
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
