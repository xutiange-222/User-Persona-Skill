#!/usr/bin/env python3
"""03-field-alignment.json 硬门禁 — 防止聚类后静默跳过字段池确认。

用法:
  python scripts/validate_field_alignment.py --input <过程稿/03-field-alignment.json>
  python scripts/validate_field_alignment.py --workdir <项目运行目录或过程稿目录>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    resolve_process_dir = None  # type: ignore

# 模型常写的「假确认」摘要 — 无用户原话锚点
_GENERIC_SUMMARY_PATTERNS = [
    re.compile(r"^按推荐(来)?$"),
    re.compile(r"^用户确认按推荐"),
    re.compile(r"^recommended_by_goal$", re.I),
    re.compile(r"^模型推荐"),
    re.compile(r"^自动推荐"),
    re.compile(r"^默认字段"),
]

_PLACEHOLDER_FIELD_VALUES = {
    "按推荐来",
    "recommended",
    "recommended_by_goal",
    "默认: 按推荐来",
    "默认",
}


def _normalize_summary(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def validate_field_alignment(data: dict[str, Any]) -> list[str]:
    """返回错误信息列表;空列表表示通过。"""
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["根对象必须是 JSON object"]

    # --- 基础必填 ---
    for key in (
        "version",
        "fields_per_persona",
        "user_confirmed",
        "confirmation_message_summary",
        "add_on_pages",
    ):
        if key not in data:
            errors.append(f"缺少必填字段: {key}")

    if data.get("user_confirmed") is not True:
        errors.append("user_confirmed 必须为 true(须用户实际看过字段池并回复)")

    summary = str(data.get("confirmation_message_summary") or "").strip()
    if len(summary) < 10:
        errors.append(
            "confirmation_message_summary 须 ≥ 10 字,记录用户对字段/旅程的原话摘要锚点"
        )
    else:
        norm = _normalize_summary(summary)
        for pat in _GENERIC_SUMMARY_PATTERNS:
            if pat.search(norm):
                errors.append(
                    "confirmation_message_summary 过于笼统,须包含用户原话要点"
                    "(不能只写「按推荐来」或模型自述)"
                )
                break

    # --- 字段池已向用户展示 ---
    if data.get("field_pool_presented") is not True:
        errors.append(
            "field_pool_presented 必须为 true — 聚类确认后须先展示完整字段池(★/□)"
            "并等待用户回复,才能写本 JSON"
        )

    display_names = data.get("fields_display_names")
    if not isinstance(display_names, dict) or not display_names:
        errors.append(
            "缺少 fields_display_names — 须记录向用户展示的中文字段名"
            "(key=schema 字段 key,value=画像页展示中文名)"
        )
    else:
        empty_vals = [k for k, v in display_names.items() if not str(v).strip()]
        if empty_vals:
            errors.append(
                f"fields_display_names 下列 key 的中文名为空: {empty_vals[:5]}"
            )

    fields_map = data.get("fields_per_persona")
    if not isinstance(fields_map, dict) or not fields_map:
        errors.append("fields_per_persona 必须是非空对象")
    else:
        for persona_key, fields in fields_map.items():
            if not isinstance(fields, list) or not fields:
                errors.append(f"fields_per_persona['{persona_key}'] 须为非空数组")
                continue
            if all(str(f).strip() in _PLACEHOLDER_FIELD_VALUES for f in fields):
                errors.append(
                    f"fields_per_persona['{persona_key}'] 不能全是占位符"
                    "(须为具体 schema 字段 key 列表)"
                )

    # alignment_mode  alone 不能代替用户确认
    if data.get("alignment_mode") == "recommended_by_goal":
        if data.get("user_confirmed") is not True or len(summary) < 10:
            errors.append(
                "仅有 alignment_mode=recommended_by_goal 不能视为已确认;"
                "须 user_confirmed + 用户原话摘要"
            )

    add_on = data.get("add_on_pages")
    if not isinstance(add_on, dict):
        errors.append("add_on_pages 必须是对象")
    elif "journey" not in add_on:
        errors.append("add_on_pages.journey 必填(布尔,表示用户是否加旅程页)")

    # 抽取前素材门禁
    visual = data.get("visual_assets")
    if not isinstance(visual, dict) or visual.get("assets_asked") is not True:
        errors.append(
            "visual_assets.assets_asked 必须为 true — 字段对齐 Step 5.0 须问过头像/截图"
        )

    # toB/toD 多角色 L1 判定
    persona_count = int(data.get("persona_count") or 0)
    persona_type = str(data.get("persona_type") or "").lower()
    if persona_count >= 2 and persona_type in ("tob", "tod"):
        if not isinstance(add_on, dict):
            pass
        else:
            for jkey in (
                "journey_scope",
                "journey_l1_eligible",
                "organizational_cohesion",
            ):
                if jkey not in add_on:
                    errors.append(
                        f"toB/toD 多角色(≥2)时 add_on_pages.{jkey} 必填"
                    )

    return errors


def load_field_alignment(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_field_alignment_file(workdir: Path) -> Path | None:
    workdir = Path(workdir)
    candidates = [
        workdir / "03-field-alignment.json",
        workdir / "过程稿" / "03-field-alignment.json",
    ]
    if resolve_process_dir is not None:
        try:
            proc = resolve_process_dir(workdir)
            candidates.insert(0, proc / "03-field-alignment.json")
        except Exception:
            pass
    for p in candidates:
        if p.is_file():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 03-field-alignment.json")
    parser.add_argument("--input", help="03-field-alignment.json 路径")
    parser.add_argument("--workdir", help="项目运行目录或过程稿目录")
    args = parser.parse_args()

    if args.input:
        path = Path(args.input)
    elif args.workdir:
        path = find_field_alignment_file(Path(args.workdir))
        if path is None:
            print(json.dumps({"valid": False, "errors": ["未找到 03-field-alignment.json"]}, ensure_ascii=False))
            return 1
    else:
        parser.error("请指定 --input 或 --workdir")

    if not path.is_file():
        print(json.dumps({"valid": False, "errors": [f"文件不存在: {path}"]}, ensure_ascii=False))
        return 1

    data = load_field_alignment(path)
    errors = validate_field_alignment(data)
    payload = {"valid": not errors, "path": str(path), "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
