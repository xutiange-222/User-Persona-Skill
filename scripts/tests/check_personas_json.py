#!/usr/bin/env python3
"""Check v8 personas JSON data contracts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from quality_common import (
    Issue,
    emit_result,
    extract_personas,
    flatten_persona,
    iter_dict_items,
    normalized_similarity,
    read_json,
)

try:
    from path_utils import resolve_process_dir
except Exception:  # pragma: no cover
    resolve_process_dir = None

FULL_NAME_SOURCE_RE = re.compile(r"\bU\d+[_-][\u4e00-\u9fff]{2,4}\b", re.I)
GENERIC_RESPONDENT_RE = re.compile(r"受访者\d+")


def evidence_sources(evidence_quotes: Any) -> list[str]:
    sources: list[str] = []
    if not isinstance(evidence_quotes, list):
        return sources
    for item in evidence_quotes:
        if isinstance(item, dict):
            source = item.get("source") or item.get("name")
            if source:
                sources.append(str(source))
        elif isinstance(item, str):
            m = re.search(r"\[来源:([^\]]+)\]", item)
            if m:
                sources.append(m.group(1))
    return sources


def check_evidence_contract(persona_name: str, value: Any, path: str, errors: list[Issue]) -> None:
    if not isinstance(value, dict):
        return
    if not {"mention_count", "mentioned_by", "evidence_quotes"} <= set(value.keys()):
        return
    mentioned_by = value.get("mentioned_by")
    evidence_quotes = value.get("evidence_quotes")
    mention_count = value.get("mention_count")
    if not isinstance(mentioned_by, list) or not isinstance(evidence_quotes, list):
        errors.append(Issue(
            "personas.evidence_shape",
            f"{persona_name} {path} 的 mentioned_by 和 evidence_quotes 必须是数组。",
            path,
        ))
        return
    if mention_count != len(mentioned_by) or mention_count != len(evidence_quotes):
        errors.append(Issue(
            "personas.evidence_count",
            f"{persona_name} {path} 不满足 mention_count = mentioned_by.length = evidence_quotes.length。",
            path,
        ))
    sources = evidence_sources(evidence_quotes)
    for source in mentioned_by:
        source_text = str(source)
        if not any(source_text in s or s in source_text for s in sources):
            errors.append(Issue(
                "personas.evidence_source_missing",
                f"{persona_name} {path} 的 {source_text} 在 evidence_quotes 中没有对应来源。",
                path,
            ))


def check_display_text(value: Any, path: str, errors: list[Issue]) -> None:
    if isinstance(value, str):
        if GENERIC_RESPONDENT_RE.search(value):
            errors.append(Issue("personas.generic_respondent", "展示文本中出现受访者编号。", path))
        if FULL_NAME_SOURCE_RE.search(value):
            errors.append(Issue("personas.full_name_source", "展示文本中出现 U编号_真实姓名 source。", path))
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in {"source_documents", "members"}:
                continue
            check_display_text(child, f"{path}.{key}" if path else str(key), errors)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            check_display_text(child, f"{path}[{idx}]", errors)


def check_journeys(personas: list[dict[str, Any]], root_data: dict[str, Any], errors: list[Issue]) -> None:
    add_on = root_data.get("add_on_pages") if isinstance(root_data, dict) else None
    journey_requested = root_data.get("include_journey") is True or (isinstance(add_on, dict) and add_on.get("journey") is True)
    any_journey = any(isinstance(p.get("journey"), dict) or isinstance(flatten_persona(p).get("journey"), dict) for p in personas)
    if (journey_requested or any_journey) and len(personas) > 1:
        l1_eligible = isinstance(add_on, dict) and add_on.get("journey_l1_eligible") is True
        l1_forbidden = isinstance(add_on, dict) and add_on.get("journey_l1_eligible") is False
        if journey_requested and l1_eligible and not isinstance(root_data.get("overall_journey"), dict):
            errors.append(Issue("personas.overall_journey_missing", "journey_l1_eligible=true 但缺少 overall_journey(L1 数据)。", "overall_journey"))
        if l1_forbidden and isinstance(root_data.get("overall_journey"), dict):
            errors.append(Issue("personas.overall_journey_forbidden", "journey_l1_eligible=false(完全独立) 不应有 overall_journey。", "overall_journey"))
        journey_texts: list[tuple[str, str]] = []
        for idx, persona in enumerate(personas):
            flat = flatten_persona(persona)
            journey = flat.get("journey")
            name = str(flat.get("name") or f"persona-{idx}")
            if not isinstance(journey, dict):
                errors.append(Issue("personas.journey_missing", f"{name} 缺少独立 journey 对象。", f"personas[{idx}].journey"))
                continue
            journey_texts.append((name, repr(journey)))
        for i in range(len(journey_texts)):
            for j in range(i + 1, len(journey_texts)):
                ratio = normalized_similarity(journey_texts[i][1], journey_texts[j][1])
                if ratio > 0.70:
                    errors.append(Issue(
                        "personas.journey_duplicate",
                        f"{journey_texts[i][0]} 与 {journey_texts[j][0]} 的旅程内容相似度 {ratio:.0%},超过 70%。",
                        "journey",
                    ))


def validate_personas_file(path: Path) -> tuple[list[Issue], list[Issue], dict[str, Any]]:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    data = read_json(path)
    personas, root_data = extract_personas(data)
    if not personas:
        errors.append(Issue("personas.empty", "没有识别到 personas 数组或画像对象。", str(path)))
        return errors, warnings, {"persona_count": 0}

    for idx, persona in enumerate(personas):
        flat = flatten_persona(persona)
        name = str(flat.get("name") or f"persona-{idx}")
        for required in ("name",):
            if not flat.get(required):
                errors.append(Issue("personas.required", f"{name} 缺少必填字段 {required}。", f"personas[{idx}].{required}"))
        if "description" not in flat and "summary" not in flat:
            warnings.append(Issue(
                "personas.description_missing",
                f"{name} 缺少 description 或 summary。",
                f"personas[{idx}]",
                "warning",
            ))
        for item_path, item in iter_dict_items(flat):
            check_evidence_contract(name, item, f"personas[{idx}].{item_path}", errors)
        check_display_text(flat, f"personas[{idx}]", errors)

    check_journeys(personas, root_data if isinstance(root_data, dict) else {}, errors)
    return errors, warnings, {"persona_count": len(personas)}


def resolve_input(args) -> Path:
    if args.input:
        return Path(args.input).resolve()
    workdir = Path(args.workdir).resolve()
    if resolve_process_dir:
        workdir = resolve_process_dir(workdir)
    return workdir / "04-personas.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="04-personas.json 路径")
    parser.add_argument("--workdir", default=".", help="项目运行目录或过程稿目录")
    args = parser.parse_args()

    path = resolve_input(args)
    if not path.exists():
        return emit_result(
            check_name="personas_json",
            errors=[Issue("personas.not_found", "未找到 04-personas.json。", str(path))],
            next_step="先生成或传入 04-personas.json。",
        )
    errors, warnings, extra = validate_personas_file(path)
    return emit_result(
        check_name="personas_json",
        errors=errors,
        warnings=warnings,
        next_step="修复画像 JSON 的证据、脱敏或旅程结构后重跑。",
        extra=extra,
    )


if __name__ == "__main__":
    raise SystemExit(main())
