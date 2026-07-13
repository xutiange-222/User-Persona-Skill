#!/usr/bin/env python3
"""Validate source tiers, content deduplication and count semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir

ROOT = Path(__file__).resolve().parent.parent


def validate_source_manifest(workdir: Path) -> list[dict]:
    process_dir = resolve_process_dir(workdir)
    path = process_dir / "source-manifest.json"
    errors: list[dict] = []
    def add(code: str, message: str) -> None:
        errors.append({"code": code, "path": "source-manifest.json", "message": message})
    if not path.is_file():
        add("SOURCE_MANIFEST_MISSING", "按内容去重并标注证据层级的 source-manifest.json 缺失。")
        return errors
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add("SOURCE_MANIFEST_INVALID", str(exc))
        return errors
    schema = json.loads((ROOT / "scripts/schemas/source-manifest.schema.json").read_text(encoding="utf-8"))
    if Draft202012Validator is not None:
        for err in Draft202012Validator(schema).iter_errors(data):
            add("SOURCE_MANIFEST_SCHEMA_INVALID", f"{'.'.join(map(str, err.absolute_path)) or '$'}: {err.message}")
    sources = data.get("sources") if isinstance(data, dict) else []
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    primary = supplemental = assignments = 0
    processed_dir = process_dir / "processed"
    for i, item in enumerate(sources if isinstance(sources, list) else []):
        if not isinstance(item, dict):
            continue
        digest = item.get("content_sha256")
        expected_id = "P" + str(digest)[:8].upper()
        if item.get("source_id") != expected_id:
            add("SOURCE_ID_HASH_MISMATCH", f"sources[{i}].source_id 应为内容哈希派生值 {expected_id}。")
        if digest in seen_hashes:
            add("SOURCE_HASH_DUPLICATE", f"sources[{i}] 重复登记同一内容哈希。")
        seen_hashes.add(str(digest))
        tier = item.get("evidence_tier")
        primary += tier == "primary"
        supplemental += tier == "supplemental"
        assigned = item.get("assigned_personas") or []
        assignments += len(assigned) if isinstance(assigned, list) else 0
        for rel in item.get("processed_files") or []:
            rel = str(rel).replace("\\", "/")
            if rel in seen_paths:
                add("SOURCE_FILE_MULTIPLE_ENTRIES", f"{rel} 出现在多个来源条目。")
            seen_paths.add(rel)
            file_path = processed_dir / Path(rel)
            if not file_path.is_file():
                add("SOURCE_FILE_MISSING", f"清单文件不存在：{rel}")
            elif hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                add("SOURCE_HASH_MISMATCH", f"{rel} 的内容哈希与清单不一致。")
    actual_paths = {p.relative_to(processed_dir).as_posix() for p in processed_dir.rglob("*.txt") if p.is_file()} if processed_dir.is_dir() else set()
    missing = sorted(actual_paths - seen_paths)
    extra = sorted(seen_paths - actual_paths)
    if missing:
        add("SOURCE_FILES_UNREGISTERED", f"processed 中有 {len(missing)} 个文件未登记：{missing[:5]}")
    if extra:
        add("SOURCE_FILES_UNKNOWN", f"清单中有 {len(extra)} 个文件不在 processed：{extra[:5]}")
    counts = data.get("counts") if isinstance(data, dict) else {}
    expected = {"unique_primary_interviews": primary, "unique_supplemental_sources": supplemental, "analysis_assignment_count": assignments}
    if counts != expected:
        add("SOURCE_COUNT_MISMATCH", f"counts={counts!r}，按来源条目计算应为 {expected!r}。")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    errors = validate_source_manifest(Path(args.workdir))
    for item in errors:
        print(f"[ERROR] {item['code']}: {item['message']}")
    if not errors:
        print("[OK] source manifest")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
