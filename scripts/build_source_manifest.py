#!/usr/bin/env python3
"""Create a hash-deduplicated source manifest from process/processed."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


def stable_id(digest: str) -> str:
    return "P" + digest[:8].upper()


def build_manifest(workdir: Path) -> dict:
    process_dir = resolve_process_dir(workdir)
    processed = process_dir / "processed"
    if not processed.is_dir():
        raise FileNotFoundError(f"processed directory missing: {processed}")
    by_hash: dict[str, list[Path]] = {}
    for path in sorted(p for p in processed.rglob("*.txt") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash.setdefault(digest, []).append(path)
    if not by_hash:
        raise ValueError("processed contains no .txt sources")
    group_labels = sorted({
        rel.parts[0] if len(rel.parts) > 1 else "default"
        for paths in by_hash.values() for rel in (path.relative_to(processed) for path in paths)
    })
    group_to_persona = {label: f"persona-{index + 1}" for index, label in enumerate(group_labels)}
    sources = []
    for digest, paths in sorted(by_hash.items()):
        relative = [p.relative_to(processed).as_posix() for p in paths]
        groups = sorted({p.parts[0] if len(p.parts) > 1 else "default" for p in (x.relative_to(processed) for x in paths)})
        sources.append({
            "source_id": stable_id(digest),
            "processed_files": relative,
            "content_sha256": digest,
            "evidence_tier": "primary",
            "assigned_personas": [group_to_persona[group] for group in groups],
            "inclusion_reason": f"待审核：processed 分组为 {', '.join(groups)}；确认画像编号和证据层级",
            "supplemented_fields": [],
        })
    return {
        "version": "1.0",
        "status": "draft",
        "sources": sources,
        "reference_files": [],
        "counts": {
            "unique_primary_interviews": len(sources),
            "unique_supplemental_sources": 0,
            "analysis_assignment_count": sum(len(item["assigned_personas"]) for item in sources),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成按内容去重的来源清单")
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    manifest = build_manifest(process_dir)
    output = process_dir / "source-manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DRAFT] {output}")
    print("审核 evidence_tier、assigned_personas、inclusion_reason 与 supplemented_fields 后，将 status 改为 reviewed。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
