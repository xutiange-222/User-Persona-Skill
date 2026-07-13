#!/usr/bin/env python3
"""Detect count drift, cross-persona sources and mechanical evidence reuse in 04."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_RE = re.compile(r"\[来源:(P[0-9A-F]{8})\]\s*[:：]?\s*[\"“](.*?)[\"”]", re.S)


def _source_ids(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value if re.fullmatch(r"P[0-9A-F]{8}", str(item))}
    return set(re.findall(r"P[0-9A-F]{8}", str(value or "")))


def _quotes(value: object) -> list[tuple[str, str]]:
    texts = value if isinstance(value, list) else [value]
    result: list[tuple[str, str]] = []
    for text in texts:
        result.extend((sid, re.sub(r"\s+", "", quote)) for sid, quote in SOURCE_RE.findall(str(text or "")))
    return result


def _evidence_nodes(value: object, path: str = ""):
    if isinstance(value, dict):
        if "evidence_quotes" in value:
            yield path, value
        for key, child in value.items():
            yield from _evidence_nodes(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _evidence_nodes(child, f"{path}[{index}]")


def validate_evidence_contract(process_dir: Path) -> list[dict]:
    process_dir = Path(process_dir)
    persona_path = process_dir / "04-personas.json"
    manifest_path = process_dir / "source-manifest.json"
    if not persona_path.is_file():
        return []
    data = json.loads(persona_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    assignments = {str(item.get("source_id")): set(map(str, item.get("assigned_personas") or [])) for item in manifest.get("sources") or [] if isinstance(item, dict)}
    errors: list[dict] = []
    for p_idx, persona in enumerate(data.get("personas") or []):
        if not isinstance(persona, dict):
            continue
        pid = str(persona.get("id") or "")
        members = set(map(str, persona.get("members") or []))
        bundle_paths: defaultdict[tuple, list[str]] = defaultdict(list)
        quote_paths: defaultdict[tuple, set[str]] = defaultdict(set)
        for path, node in _evidence_nodes(persona.get("fields") or {}):
            mentioned = _source_ids(node.get("mentioned_by"))
            count = node.get("mention_count")
            quotes = _quotes(node.get("evidence_quotes"))
            quote_sources = {sid for sid, _ in quotes}
            full_path = f"personas[{p_idx}].fields.{path}"
            if isinstance(count, int) and count != len(mentioned):
                errors.append({"code": "EVIDENCE_MENTION_COUNT_MISMATCH", "path": full_path, "message": f"mention_count={count}，mentioned_by 有 {len(mentioned)} 个独立来源。"})
            if mentioned - members:
                errors.append({"code": "EVIDENCE_CROSS_PERSONA_SOURCE", "path": full_path, "message": f"使用了不属于 {pid} 的来源：{sorted(mentioned - members)}"})
            if quote_sources - mentioned:
                errors.append({"code": "EVIDENCE_QUOTE_SOURCE_MISMATCH", "path": full_path, "message": f"引文来源未出现在 mentioned_by：{sorted(quote_sources - mentioned)}"})
            bundle = tuple(sorted(quotes))
            if bundle:
                bundle_paths[bundle].append(full_path)
                for quote in bundle:
                    quote_paths[quote].add(full_path)
        for bundle, paths in bundle_paths.items():
            if len(paths) >= 3:
                errors.append({"code": "EVIDENCE_BUNDLE_REUSED", "path": f"personas[{p_idx}]", "message": f"同一组 {len(bundle)} 条原话被完整复用于 {len(paths)} 个结论：{paths[:5]}。请为每个结论选择直接证据。"})
        for (source_id, quote), paths in quote_paths.items():
            if len(paths) >= 6:
                errors.append({"code": "EVIDENCE_QUOTE_OVERUSED", "path": f"personas[{p_idx}]", "message": f"{source_id} 的同一句原话支撑了 {len(paths)} 个结论，疑似机械复用：{quote[:40]}"})
        for source_id in members:
            if assignments and pid not in assignments.get(source_id, set()):
                errors.append({"code": "EVIDENCE_SOURCE_ASSIGNMENT_MISMATCH", "path": f"personas[{p_idx}].members", "message": f"{source_id} 未在 source-manifest.json 分配给 {pid}。"})
    return errors
