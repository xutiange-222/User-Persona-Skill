#!/usr/bin/env python3
"""Block mojibake and ungrounded or truncated technical tokens in confirmed content."""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9+._-]{2,})(?![A-Za-z0-9])")
TITLE_TRUNCATION_RE = re.compile(r"(?:…|……|\.{3,})\s*$")
MOJIBAKE_RE = re.compile(r"�|(?:Ã.|Â.|â€|锟斤拷|馃|鈥[^一-鿿])")
SKIP_KEYS = {
    "id", "persona_id", "checkpoint", "status", "type", "layout", "theme", "density",
    "accent", "content_ref", "source", "source_id", "source_ids", "members", "target",
    "evidence_type", "template_id", "palette_id", "alignment_md_sha256", "generated_at",
    "icon", "style", "class", "marker_id", "branch", "presentation", "provenance",
    "field", "source_fields", "included_fields", "confirmed_value_sections", "variable_levels",
    "evidence_quotes", "quote", "quote_or_basis", "source_documents", "merge_rules",
    "lane", "stage", "from", "to", "node_id", "edge_id",
    "scope", "component_type", "notes",
}
WHITELIST = {
    "ai", "api", "b2b", "b2c", "b2d", "css", "csv", "devops", "html", "json", "kpi",
    "llm", "md", "npu", "pc", "ppt", "qa", "rl", "sdk", "sql", "toc", "tob", "tod",
    "ui", "url", "ux", "svg", "pdf", "python", "javascript", "powershell", "source",
    "primary", "supplemental", "synthesis", "user_context", "not_applicable",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_visible_strings(value, path: str = ""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in SKIP_KEYS or str(key).lower().endswith(("_id", "_ids", "_path", "_sha256")):
                continue
            yield from _iter_visible_strings(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_visible_strings(child, f"{path}[{index}]")


def validate_language_quality(workdir: Path) -> list[dict]:
    process_dir = resolve_process_dir(Path(workdir))
    grounding_parts: list[str] = []
    processed = process_dir / "processed"
    if processed.is_dir():
        for path in processed.rglob("*.txt"):
            grounding_parts.append(path.read_text(encoding="utf-8", errors="replace"))
    for name in ("00-research-goal.json", "01-paradigm.json", "02-classification.json", "03-field-alignment.json"):
        path = process_dir / name
        if path.is_file():
            grounding_parts.append(path.read_text(encoding="utf-8", errors="replace"))
    glossary_path = process_dir / "terminology-glossary.json"
    if glossary_path.is_file():
        grounding_parts.append(glossary_path.read_text(encoding="utf-8", errors="replace"))
    grounding = "\n".join(grounding_parts).lower()
    grounding_tokens = {token.strip("._-").lower() for token in TOKEN_RE.findall(grounding)}

    errors: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for name in ("04-personas.json", "04-journeys.json", "05-report.json"):
        file_path = process_dir / name
        if not file_path.is_file():
            continue
        try:
            data = _load(file_path)
        except (OSError, json.JSONDecodeError):
            continue
        for json_path, text in _iter_visible_strings(data):
            if MOJIBAKE_RE.search(text):
                errors.append({"code": "LANGUAGE_MOJIBAKE", "path": f"{name}:{json_path}", "message": f"发现乱码或错误编码文本：{text[:80]}"})
            is_human_title = json_path.endswith(".title") or json_path.endswith(".identity_name.name")
            if is_human_title and TITLE_TRUNCATION_RE.search(text):
                errors.append({
                    "code": "LANGUAGE_TITLE_TRUNCATED",
                    "path": f"{name}:{json_path}",
                    "message": f"标题疑似用省略号截断：{text!r}。请保留动作、对象或完整名称。",
                })
            token_text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
            for token in TOKEN_RE.findall(token_text):
                normalized = token.strip("._/-").lower()
                if len(normalized) < 3 or normalized in WHITELIST or re.fullmatch(r"p[0-9a-f]{8}", normalized):
                    continue
                if normalized in grounding_tokens:
                    continue
                hyphen_parts = [part for part in normalized.split("-") if len(part) >= 2]
                if len(hyphen_parts) >= 2 and all(part in grounding_tokens or part in WHITELIST for part in hyphen_parts):
                    continue
                key = (name, json_path, normalized)
                if key in seen:
                    continue
                seen.add(key)
                longer = sorted(candidate for candidate in grounding_tokens if len(candidate) > len(normalized) and candidate.startswith(normalized))
                if longer:
                    errors.append({
                        "code": "LANGUAGE_TECH_TOKEN_TRUNCATED", "path": f"{name}:{json_path}",
                        "message": f"技术 token {token!r} 疑似被截断；材料中存在 {longer[:3]}。保留完整术语或回到原文核对。",
                    })
                else:
                    errors.append({
                        "code": "LANGUAGE_TECH_TOKEN_UNGROUNDED", "path": f"{name}:{json_path}",
                        "message": f"技术 token {token!r} 未出现在材料、00-03 用户上下文或术语表中。请核对来源，禁止猜词。",
                    })
    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    errors = validate_language_quality(Path(args.workdir))
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
