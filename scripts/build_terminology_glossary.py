#!/usr/bin/env python3
"""Compile authoritative Markdown terminology audit tables into machine-readable JSON."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


def parse_table(path: Path) -> list[dict]:
    terms: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in {"原文 token", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        raw, decision, treatment, basis = cells[:4]
        canonical = re.sub(r"^[→\-＞>\s]+", "", treatment).strip()
        if canonical == "保留":
            canonical = raw
        raw_terms = [part.strip() for part in re.split(r"\s*/\s*", raw) if part.strip()]
        terms.append({
            "raw_terms": raw_terms,
            "canonical": canonical,
            "decision": decision,
            "basis": basis,
            "source_label": path.name,
        })
    return terms


def main() -> int:
    parser = argparse.ArgumentParser(description="汇总术语审计表")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    paths = sorted(Path(args.input_dir).rglob("术语审计表*.md"))
    if not paths:
        raise SystemExit("未找到术语审计表*.md")
    terms = [item for path in paths for item in parse_table(path)]
    data = {"version": "1.0", "status": "authoritative", "source_files": [p.name for p in paths], "terms": terms}
    output = resolve_process_dir(Path(args.workdir)) / "terminology-glossary.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {output} ({len(terms)} term rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
