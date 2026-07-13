#!/usr/bin/env python3
"""Resolve 05 component references from the user-confirmed 04 persona checkpoint."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

REF_RE = re.compile(r"^/personas/(\d+)/display_components/(\d+)$")
JOURNEY_LAYOUTS = {"layout-2b-journey", "layout-2c-journey"}
OVERVIEW_IDS = {"matrix", "distribution", "journey-l1"}


def _load_checkpoint(process_dir: Path) -> dict:
    data = json.loads((Path(process_dir) / "04-personas.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("04-personas.json must be an object")
    return data


def resolve_report_content_refs(report: dict, process_dir: Path) -> dict:
    confirmed = _load_checkpoint(process_dir)
    source_personas = confirmed.get("personas") or []
    resolved = copy.deepcopy(report)
    for p_idx, page in enumerate(resolved.get("personas") or []):
        if not isinstance(page, dict):
            continue
        for c_idx, component in enumerate(page.get("components") or []):
            if not isinstance(component, dict) or "content_ref" not in component:
                continue
            ref = str(component.get("content_ref") or "")
            match = REF_RE.fullmatch(ref)
            if not match:
                raise ValueError(f"invalid content_ref at personas[{p_idx}].components[{c_idx}]: {ref!r}")
            pi, ci = map(int, match.groups())
            try:
                canonical = source_personas[pi]["display_components"][ci]
            except (IndexError, KeyError, TypeError) as exc:
                raise ValueError(f"content_ref target does not exist: {ref}") from exc
            if not isinstance(canonical, dict) or not {"type", "props", "source_fields"} <= set(canonical):
                raise ValueError(f"content_ref target must contain type, props and source_fields: {ref}")
            if component.get("type") != canonical.get("type"):
                raise ValueError(f"content_ref type mismatch at {ref}")
            page["components"][c_idx] = {"type": canonical["type"], "props": copy.deepcopy(canonical["props"])}
    return resolved


def validate_report_content_refs(report: dict, process_dir: Path) -> list[dict]:
    errors: list[dict] = []
    seen: set[str] = set()
    confirmed = _load_checkpoint(process_dir)
    source_personas = confirmed.get("personas") or []
    actual_fields: dict[str, set[str]] = {
        str(item.get("id") or ""): set()
        for item in source_personas if isinstance(item, dict)
    }
    for p_idx, page in enumerate(report.get("personas") or []):
        if not isinstance(page, dict):
            continue
        requires_refs = page.get("layout") not in JOURNEY_LAYOUTS and page.get("id") not in OVERVIEW_IDS
        for c_idx, component in enumerate(page.get("components") or []):
            path = f"personas[{p_idx}].components[{c_idx}]"
            ref = component.get("content_ref") if isinstance(component, dict) else None
            if requires_refs and not ref:
                errors.append({"code": "PERSONA_CONTENT_REF_MISSING", "path": path, "message": "画像页和细节页只能引用 04-personas.json 已确认的 display_components。"})
            if ref:
                if str(ref) in seen:
                    errors.append({"code": "PERSONA_CONTENT_REF_DUPLICATE", "path": path, "message": f"同一确认组件被重复使用：{ref}"})
                seen.add(str(ref))
                if "props" in component:
                    errors.append({"code": "PERSONA_CONTENT_REF_WITH_PROPS", "path": path, "message": "使用 content_ref 时禁止在 05 同时写 props。"})
                match = REF_RE.fullmatch(str(ref))
                if match:
                    pi, ci = map(int, match.groups())
                    try:
                        canonical_persona = source_personas[pi]
                        canonical = canonical_persona["display_components"][ci]
                        persona_id = str(canonical_persona.get("id") or "")
                        actual_fields.setdefault(persona_id, set()).update(
                            str(field) for field in canonical.get("source_fields") or []
                        )
                    except (IndexError, KeyError, TypeError, AttributeError):
                        pass
    try:
        resolve_report_content_refs(report, process_dir)
    except Exception as exc:
        errors.append({"code": "PERSONA_CONTENT_REF_INVALID", "path": "05-report.json", "message": str(exc)})

    alignment_path = Path(process_dir) / "03-field-alignment.json"
    try:
        alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append({"code": "REPORT_FIELD_ALIGNMENT_MISSING", "path": alignment_path.name, "message": "无法核对 05 字段覆盖：缺少有效的 03-field-alignment.json。"})
        return errors
    field_map = alignment.get("fields_per_persona") if isinstance(alignment, dict) else {}
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    coverage_items = metadata.get("field_coverage") if isinstance(metadata.get("field_coverage"), list) else []
    coverage_by_id: dict[str, dict] = {}
    for idx, item in enumerate(coverage_items):
        if not isinstance(item, dict):
            continue
        persona_id = str(item.get("persona_id") or "")
        if persona_id in coverage_by_id:
            errors.append({"code": "REPORT_FIELD_COVERAGE_DUPLICATE", "path": f"metadata.field_coverage[{idx}]", "message": f"{persona_id} 重复出现。"})
        coverage_by_id[persona_id] = item

    for p_idx, persona in enumerate(source_personas):
        if not isinstance(persona, dict):
            continue
        persona_id = str(persona.get("id") or "")
        persona_name = str(persona.get("name") or "")
        selected = field_map.get(persona_id)
        if not isinstance(selected, list):
            selected = field_map.get(persona_name)
        if not isinstance(selected, list):
            selected = field_map.get("default")
        selected_set = {str(field) for field in selected or []}
        coverage = coverage_by_id.get(persona_id)
        if coverage is None:
            errors.append({"code": "REPORT_FIELD_COVERAGE_MISSING", "path": "metadata.field_coverage", "message": f"缺少 {persona_id} 的字段覆盖记录。"})
            continue
        included = {str(field) for field in coverage.get("included_fields") or []}
        omitted_items = coverage.get("omitted_fields") or []
        omitted = {str(item.get("field") or "") for item in omitted_items if isinstance(item, dict)}
        actual = actual_fields.get(persona_id, set())
        if included != actual:
            errors.append({"code": "REPORT_FIELD_COVERAGE_FALSE_CLAIM", "path": f"metadata.field_coverage[{persona_id}]", "message": f"included_fields={sorted(included)} 与实际 content_ref 字段={sorted(actual)} 不一致。"})
        if included & omitted:
            errors.append({"code": "REPORT_FIELD_COVERAGE_OVERLAP", "path": f"metadata.field_coverage[{persona_id}]", "message": f"字段同时被声明为纳入和省略：{sorted(included & omitted)}"})
        if included | omitted != selected_set:
            errors.append({"code": "REPORT_FIELD_COVERAGE_INCOMPLETE", "path": f"metadata.field_coverage[{persona_id}]", "message": f"03 已确认字段={sorted(selected_set)}，05 已说明字段={sorted(included | omitted)}。"})
        unknown = actual - selected_set
        if unknown:
            errors.append({"code": "REPORT_UNCONFIRMED_FIELD_INCLUDED", "path": f"personas[{p_idx}]", "message": f"05 纳入了 03 未确认字段：{sorted(unknown)}"})
    return errors
