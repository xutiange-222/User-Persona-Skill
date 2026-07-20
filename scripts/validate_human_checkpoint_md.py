#!/usr/bin/env python3
"""Reject machine-schema leakage from the human-facing 04 Markdown files."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


RAW_FIELD_NAMES = {
    "basic_profile", "knowledge_background", "responsibilities",
    "high_freq_tasks", "high_frequency_tasks", "kpi", "collaboration",
    "business_systems", "pain_points", "experience_goals",
    "one_sentence_need", "representative_quotes",
}
RAW_ENUMS = {
    "tob_journey_l1", "tob_journey_l2", "journey_2c",
    "solid", "dashed", "start", "step", "action", "decision", "doc", "end",
}
PARADIGM_ROUTE_LABELS = (
    "A 合并为一个画像",
    "B 沿用已有分组",
    "C 按一个关键差异分类",
    "D 用两个区分点形成矩阵",
    "E 用多个区分点形成分布",
)


def _visible(md_text: str) -> str:
    return re.sub(r"<!--.*?-->", "", md_text, flags=re.S)


def _digest(items: Any) -> str:
    payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _schema_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            tokens.add(re.sub(r"^[#\s]+", "", line).strip(" `*_").lower())
        elif line.startswith("|") and "---" not in line:
            for cell in line.strip("|").split("|"):
                tokens.add(cell.strip(" `*_").lower())
    tokens.update(token.lower() for token in re.findall(r"`([A-Za-z][A-Za-z0-9_-]*)`", text))
    return tokens


def validate_human_checkpoint_md(process_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    paradigm_md = process_dir / "01-paradigm.md"
    if paradigm_md.is_file():
        paradigm_text = _visible(paradigm_md.read_text(encoding="utf-8"))
        # Enforce the user-language contract while 01 is being reviewed.  Do
        # not retroactively block a later render for wording in a legacy 01
        # that the user already confirmed.
        if "确认状态：已确认" not in paradigm_text:
            missing_routes = [label for label in PARADIGM_ROUTE_LABELS if label not in paradigm_text]
            if missing_routes:
                errors.append({
                    "code": "PARADIGM_MD_ROUTES_MISSING",
                    "path": paradigm_md.name,
                    "message": "01 用户稿必须先解释五种中文画像方式，再给推荐。缺少：" + "、".join(missing_routes),
                })
            if re.search(r"(?<![A-Za-z0-9])R[1-5](?![A-Za-z0-9])", paradigm_text, re.I) or "范式" in paradigm_text:
                errors.append({
                    "code": "PARADIGM_MD_INTERNAL_CODE_VISIBLE",
                    "path": paradigm_md.name,
                    "message": "01 用户稿出现内部路线代码或“范式”术语。请只使用中文画像方式名称，把内部代码写入 JSON。",
                })
            recommendation = paradigm_text.split("## 我的推荐", 1)[1] if "## 我的推荐" in paradigm_text else ""
            route_names = [label.split(" ", 1)[1] for label in PARADIGM_ROUTE_LABELS]
            if not any(name in recommendation for name in route_names):
                errors.append({
                    "code": "PARADIGM_MD_RECOMMENDATION_MISSING",
                    "path": paradigm_md.name,
                    "message": "01 用户稿解释五种方式后，还必须明确推荐一个中文画像方式，并说明理由和预期结果。",
                })
    for stem, root_key in (("04-personas", "personas"), ("04-journeys", "journeys")):
        md_path = process_dir / f"{stem}.md"
        json_path = process_dir / f"{stem}.json"
        if not md_path.is_file():
            continue
        md_text = md_path.read_text(encoding="utf-8")
        if stem == "04-personas":
            try:
                from scripts.privacy_guard import validate_privacy_in_markdown
            except ImportError:
                from privacy_guard import validate_privacy_in_markdown
            errors.extend(validate_privacy_in_markdown(md_text, process_dir, path=md_path.name))
        visible = _visible(md_text)
        schema_tokens = _schema_tokens(visible)
        for field in sorted(RAW_FIELD_NAMES):
            if field.lower() in schema_tokens:
                errors.append({"code": "HUMAN_MD_RAW_FIELD_NAME", "path": md_path.name, "message": f"人类对齐稿的标题或表头出现机器字段 {field!r}；请改用中文，必要时写成中文/{field}。"})
        if stem == "04-journeys":
            id_patterns = [r"`?s-[a-z0-9_-]+`?", r"`?lane-[a-z0-9_-]+`?", r"`?persona-[0-9]+`?", r"`?n[0-9]+`?"]
            if any(re.search(pattern, visible, re.I) for pattern in id_patterns):
                errors.append({"code": "HUMAN_MD_MACHINE_ID_VISIBLE", "path": md_path.name, "message": "旅程 MD 暴露了阶段、泳道、画像或节点 ID。人类稿必须用中文名称，ID 仅保留在 JSON。"})
            for enum in RAW_ENUMS:
                if enum.lower() in schema_tokens:
                    errors.append({"code": "HUMAN_MD_RAW_ENUM_VISIBLE", "path": md_path.name, "message": f"旅程 MD 暴露机器枚举 {enum!r}；请显示中文语义。"})
            data = None
            if json_path.is_file():
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass
            if isinstance(data, dict):
                required_sections = ("## 阅读导航",) if not data.get("journeys") else ("## 阅读导航", "## 旅程总览地图", "### 一眼看全局")
                for section in required_sections:
                    if section not in visible:
                        errors.append({"code": "JOURNEY_MD_GLOBAL_CONTEXT_MISSING", "path": md_path.name, "message": f"复杂旅程对齐稿缺少 {section!r}，用户无法定位局部内容在全局中的位置。"})
                research_type = str((data.get("context_snapshot") or {}).get("research_type") or "")
                if research_type in {"toB", "toD"} and data.get("journeys") and "### 角色 × 阶段责任矩阵" not in visible:
                    errors.append({"code": "JOURNEY_MD_ROLE_STAGE_MATRIX_MISSING", "path": md_path.name, "message": "2B/2D 旅程必须先提供角色 × 阶段责任矩阵，再展开节点与分支。"})
                if research_type in {"toB", "toD"} and data.get("journeys") and "### 你现在在这里" not in visible:
                    errors.append({"code": "JOURNEY_MD_LOCATION_MISSING", "path": md_path.name, "message": "2B/2D 每条旅程必须说明当前局部内容在总体旅程中的位置。"})
        if json_path.is_file():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = None
            if isinstance(data, dict) and isinstance(data.get(root_key), list):
                expected = _digest(data[root_key])
                marker = re.search(r"<!--\s*机器内容指纹：([0-9a-f]{64})\s*-->", md_text)
                if not marker or marker.group(1) != expected:
                    errors.append({"code": "HUMAN_MD_CONTENT_FINGERPRINT_MISMATCH", "path": md_path.name, "message": f"{md_path.name} 不是由当前 {json_path.name} 生成，或正文在生成后被局部改写。请更新结构化 JSON 后重新生成 MD。"})
    return errors
