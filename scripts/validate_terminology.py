#!/usr/bin/env python3
"""Block known garbled terminology from confirmed persona and report values."""
from __future__ import annotations

import json
from pathlib import Path


def validate_terminology(process_dir: Path) -> list[dict]:
    process_dir = Path(process_dir)
    glossary_path = process_dir / "terminology-glossary.json"
    manifest_path = process_dir / "source-manifest.json"
    errors: list[dict] = []
    if not glossary_path.is_file():
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if any(item.get("reference_type") == "terminology" for item in manifest.get("reference_files") or []):
                errors.append({"code": "TERMINOLOGY_GLOSSARY_MISSING", "path": glossary_path.name, "message": "来源清单声明了术语审计材料，但没有生成 terminology-glossary.json。"})
        return errors
    try:
        glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [{"code": "TERMINOLOGY_GLOSSARY_INVALID", "path": glossary_path.name, "message": f"术语表不是有效 JSON：{exc}"}]
    if not isinstance(glossary, dict) or not isinstance(glossary.get("terms"), list):
        return [{"code": "TERMINOLOGY_GLOSSARY_INVALID", "path": glossary_path.name, "message": "术语表根节点必须是对象，且 terms 必须是数组。"}]
    targets = []
    for name in ("04-personas.json", "04-journeys.json", "05-report.json"):
        path = process_dir / name
        if path.is_file():
            targets.append((name, path.read_text(encoding="utf-8").lower()))
    for index, rule in enumerate(glossary.get("terms") or []):
        if not isinstance(rule, dict):
            errors.append({"code": "TERMINOLOGY_GLOSSARY_INVALID", "path": f"{glossary_path.name}:terms[{index}]", "message": "每条术语规则必须是对象。"})
            continue
        if not isinstance(rule.get("raw_terms", []), list):
            errors.append({"code": "TERMINOLOGY_GLOSSARY_INVALID", "path": f"{glossary_path.name}:terms[{index}].raw_terms", "message": "raw_terms 必须是数组。"})
            continue
        decision = str(rule.get("decision") or "").lower()
        if "真术语" in decision:
            continue
        canonical = str(rule.get("canonical") or "")
        for raw in rule.get("raw_terms") or []:
            token = str(raw).strip()
            if len(token) < 3 or token.lower() == canonical.lower():
                continue
            for name, text in targets:
                if token.lower() in text:
                    errors.append({"code": "TERMINOLOGY_GARBLE_PRESENT", "path": name, "message": f"发现术语审计已判定的错误形式 {token!r}；应使用 {canonical!r}。"})
    return errors
