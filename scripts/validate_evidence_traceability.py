#!/usr/bin/env python3
"""Verify every quoted material excerpt against its registered processed source."""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir

INLINE_QUOTE_RE = re.compile(r"\[来源:(P[0-9A-F]{8})\]\s*[:：]?\s*[\"“](.*?)[\"”]", re.S)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", str(value)).replace('"', "").replace("“", "").replace("”", "")


def _quote_matches(quote: str, source_text: str) -> bool:
    quote_n = _normalize(quote)
    source_n = _normalize(source_text)
    if quote_n in source_n:
        return True
    segments = [segment for segment in re.split(r"…{2,}|\.{3,}", quote_n) if len(segment) >= 2]
    if len(segments) < 2:
        return False
    cursor = 0
    for segment in segments:
        index = source_n.find(segment, cursor)
        if index < 0:
            return False
        cursor = index + len(segment)
    return True


def _iter_quotes(value, path: str = ""):
    if isinstance(value, str):
        for source_id, quote in INLINE_QUOTE_RE.findall(value):
            yield path, source_id, quote
    elif isinstance(value, dict):
        if isinstance(value.get("quote"), str) and isinstance(value.get("source"), str):
            source = str(value["source"])
            match = re.search(r"P[0-9A-F]{8}", source)
            if match:
                yield path, match.group(0), value["quote"]
        for key, child in value.items():
            yield from _iter_quotes(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_quotes(child, f"{path}[{index}]")


def _source_texts_for_process(process_dir: Path) -> dict[str, list[str]]:
    manifest_path = process_dir / "source-manifest.json"
    if not manifest_path.is_file():
        return {}
    manifest = _load(manifest_path)
    processed_dir = process_dir / "processed"
    source_texts: dict[str, list[str]] = {}
    for item in manifest.get("sources") or []:
        if not isinstance(item, dict):
            continue
        texts = []
        for rel in item.get("processed_files") or []:
            path = processed_dir / Path(str(rel))
            if path.is_file():
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
        source_texts[str(item.get("source_id") or "")] = texts
    return source_texts


def validate_journey_data_evidence(data: dict, process_dir: Path) -> list[dict]:
    """Validate a journey draft before it can be sealed and shown as final truth."""
    source_texts = _source_texts_for_process(process_dir)
    if not source_texts:
        return []
    errors: list[dict] = []
    for j_idx, journey in enumerate(data.get("journeys") or []):
        for b_idx, binding in enumerate(journey.get("evidence_bindings") or []):
            if binding.get("evidence_type") not in {"primary", "supplemental"}:
                continue
            source_ids = binding.get("source_ids") or []
            basis = str(binding.get("quote_or_basis") or "")
            path = f"04-journeys.draft.json:journeys[{j_idx}].evidence_bindings[{b_idx}]"
            if len(source_ids) != 1:
                errors.append({"code": "JOURNEY_EVIDENCE_NOT_ATOMIC", "path": path, "message": "每条材料证据绑定只能包含一个 source_id 和一段逐字原话。"})
            elif not any(_quote_matches(basis, text) for text in source_texts.get(str(source_ids[0]), [])):
                errors.append({"code": "JOURNEY_EVIDENCE_NOT_VERBATIM", "path": path, "message": "quote_or_basis 无法回到对应 processed 原文。"})
    return errors


def validate_evidence_traceability(workdir: Path) -> list[dict]:
    process_dir = resolve_process_dir(Path(workdir))
    manifest_path = process_dir / "source-manifest.json"
    if not manifest_path.is_file():
        return []
    source_texts = _source_texts_for_process(process_dir)

    errors: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    candidates = []
    for folder in ("extracted", "reduced"):
        root = process_dir / folder
        if root.is_dir():
            candidates.extend(root.rglob("*.json"))
    candidates.extend(path for path in (process_dir / "04-personas.json", process_dir / "04-journeys.json") if path.is_file())
    for file_path in candidates:
        try:
            data = _load(file_path)
        except Exception:
            continue
        rel = file_path.relative_to(process_dir).as_posix()
        for json_path, source_id, quote in _iter_quotes(data):
            key = (rel, json_path, source_id + quote)
            if key in seen:
                continue
            seen.add(key)
            texts = source_texts.get(source_id)
            if not texts:
                errors.append({"code": "EVIDENCE_SOURCE_UNKNOWN", "path": f"{rel}:{json_path}", "message": f"证据来源 {source_id} 未在 source-manifest 登记或没有 processed 文本。"})
            elif not any(_quote_matches(quote, text) for text in texts):
                errors.append({"code": "EVIDENCE_QUOTE_NOT_VERBATIM", "path": f"{rel}:{json_path}", "message": f"{source_id} 中找不到该逐字引文：{quote[:80]}"})

    journeys_path = process_dir / "04-journeys.json"
    if journeys_path.is_file():
        for item in validate_journey_data_evidence(_load(journeys_path), process_dir):
            item["path"] = item["path"].replace("04-journeys.draft.json", "04-journeys.json")
            errors.append(item)
    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    errors = validate_evidence_traceability(Path(args.workdir))
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
