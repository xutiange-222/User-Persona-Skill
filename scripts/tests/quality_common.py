#!/usr/bin/env python3
"""Shared helpers for user-persona-v8 quality checks."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass
class Issue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(SKILL_ROOT.resolve()))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def emit_result(
    *,
    check_name: str,
    errors: list[Issue],
    warnings: list[Issue] | None = None,
    next_step: str = "修复 errors 后重跑同一检查。",
    extra: dict[str, Any] | None = None,
) -> int:
    warnings = warnings or []
    payload: dict[str, Any] = {
        "success": not errors,
        "check": check_name,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": [asdict(i) for i in errors],
        "warnings": [asdict(i) for i in warnings],
        "next_step": "可以进入下一层测试。" if not errors else next_step,
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def strip_html(html: str) -> str:
    text = re.sub(r"<script\b[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style\b[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def class_attr_contains(tag: str, class_name: str) -> bool:
    m = re.search(r'class=["\']([^"\']*)["\']', tag, flags=re.I)
    return bool(m and class_name in m.group(1).split())


def journey_sections(html: str) -> list[str]:
    return re.findall(
        r'<section\b[^>]*class=["\'][^"\']*\blayout-2c-journey\b[^"\']*["\'][^>]*>[\s\S]*?</section>',
        html,
        flags=re.I,
    )


def normalized_similarity(a: str, b: str) -> float:
    def normalize(value: str) -> str:
        value = strip_html(value)
        value = re.sub(r"persona-\d+-journey|p\d+-journey", " ", value, flags=re.I)
        value = re.sub(r"#[0-9a-fA-F]{3,8}", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def find_delivery_dirs(run_dir: Path) -> list[Path]:
    if not run_dir.exists():
        return []
    candidates = [p for p in run_dir.iterdir() if p.is_dir() and p.name.startswith("最终交付件-")]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def extract_personas(data: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("personas"), list):
        return data["personas"], data
    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)], {}
    if isinstance(data, dict):
        return [data], data
    return [], {}


def flatten_persona(persona: dict[str, Any]) -> dict[str, Any]:
    fields = persona.get("fields")
    if isinstance(fields, dict):
        merged = dict(persona)
        merged.pop("fields", None)
        merged.update(fields)
        return merged
    return persona


def iter_dict_items(value: Any, path: str = ""):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from iter_dict_items(child, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]"
            yield from iter_dict_items(child, child_path)
