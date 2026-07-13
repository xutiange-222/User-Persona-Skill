#!/usr/bin/env python3
"""Render a delta-only human review surface for 05-report.draft.json."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


LAYOUT_LABELS = {
    "layout-matrix-2d": "二维矩阵总览",
    "layout-distribution-multi": "多维分布总览",
    "layout-2b-grid": "画像主页",
    "layout-2b-grid-detail": "画像详情页",
    "layout-2b-journey": "用户旅程页",
    "layout-2c-portrait": "画像主页",
    "layout-2c-detail": "画像详情页",
    "layout-2c-journey": "用户旅程页",
}
COMPONENT_LABELS = {
    "matrix_guidance_strip": "矩阵读图说明", "matrix_2d": "二维画像矩阵",
    "distribution_multi": "多维画像分布", "identity_card": "画像身份",
    "persona_quote_pull": "代表性原声", "section_blocks_grid": "画像内容",
    "detail_headline": "详情摘要", "mockup_list": "场景与任务",
    "detail_analysis": "详细分析", "journey_2c": "消费者旅程",
    "tob_journey_l1": "整体旅程", "tob_journey_l2": "单角色旅程",
}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path.name} 必须是 JSON 对象。")
    return data


def _page_kind(page: dict[str, Any]) -> str:
    return LAYOUT_LABELS.get(str(page.get("layout") or ""), "报告页面")


def _baseline(process_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    metadata = report.get("metadata") or {}
    pages = report.get("personas") or []
    personas_path = process_dir / "04-personas.json"
    journeys_path = process_dir / "04-journeys.json"
    persona_data = _load(personas_path) if personas_path.is_file() else {}
    journey_data = _load(journeys_path) if journeys_path.is_file() else {}
    persona_count = len(persona_data.get("personas") or []) or int(metadata.get("persona_count") or 0)
    journey_count = len(journey_data.get("journeys") or [])
    overview_count = sum(_page_kind(page).endswith("总览") for page in pages)
    baseline_count = overview_count + persona_count + journey_count
    detail_pages = [page for page in pages if "详情页" in _page_kind(page)]
    return {
        "persona_count": persona_count,
        "journey_count": journey_count,
        "overview_count": overview_count,
        "baseline_count": baseline_count,
        "detail_pages": detail_pages,
    }


def render_report_checkpoint_md(process_dir: Path, report: dict[str, Any]) -> str:
    metadata = report.get("metadata") or {}
    pages = report.get("personas") or []
    baseline = _baseline(process_dir, report)
    proposed_count = len(pages)
    omitted = [
        {"persona": item.get("persona_id"), **field}
        for item in metadata.get("field_coverage") or []
        for field in item.get("omitted_fields") or []
    ]
    delta = proposed_count - baseline["baseline_count"]
    lines = [
        "# 05 最终页面编排确认", "", "确认状态：待用户确认", "",
        "本步骤只确认画像与旅程内容如何分配到最终页面。此前已经确认的画像方式、字段、色卡和旅程内容直接沿用，不再重复选择。", "",
        "## 本次新增决定", "",
        f"- 上游确认可直接形成：**{baseline['baseline_count']} 页**（总览 {baseline['overview_count']} 页、画像 {baseline['persona_count']} 页、旅程 {baseline['journey_count']} 页）。",
        f"- 当前建议最终形成：**{proposed_count} 页**。",
        f"- 最终页数：{proposed_count}",
    ]
    if delta > 0:
        lines.append(f"- 新增：**{delta} 页**，用于完整容纳已经确认的内容，避免拥挤或静默删减。")
    elif delta < 0:
        lines.append(f"- 减少：**{-delta} 页**。请重点核对下面的信息损失。")
    else:
        lines.append("- 页数没有增加或减少。")
    if baseline["detail_pages"]:
        names = "、".join(str(page.get("name") or "对应画像") for page in baseline["detail_pages"])
        lines.append(f"- 新增详情页：{names}。")
    lines += ["", "## 信息损失", ""]
    if omitted:
        lines += ["| 画像 | 未进入报告的内容 | 原因 |", "|---|---|---|"]
        for item in omitted:
            lines.append(f"| {item.get('persona') or '对应画像'} | {item.get('field') or ''} | {item.get('reason') or ''} |")
    else:
        lines.append("- 没有字段被删除。已确认内容仅在不同页面之间重新分配。")
    lines += ["", "## 最终页面清单", "", "| 页码 | 页面 | 页面作用 | 主要内容 |", "|---:|---|---|---|"]
    for index, page in enumerate(pages, 1):
        components = "、".join(
            COMPONENT_LABELS.get(str(item.get("type") or ""), "已确认内容")
            for item in page.get("components") or []
        )
        lines.append(f"| {index} | {page.get('name') or f'第 {index} 页'} | {_page_kind(page)} | {components or '已确认内容'} |")
    alignment_path = process_dir / "03-field-alignment.json"
    alignment = _load(alignment_path) if alignment_path.is_file() else {}
    visual = alignment.get("visual_spec") or {}
    lines += [
        "", "<details>", "<summary>展开已确认并沿用的设置</summary>", "",
        f"- 画像方式：{(metadata.get('context_snapshot') or {}).get('paradigm') or '沿用上游'}",
        f"- 画像数量：{baseline['persona_count']}",
        f"- 旅程数量：{baseline['journey_count']}",
        f"- 视觉模板与色卡：沿用 03 已确认设置（{visual.get('template_id') or '已确认'} / {visual.get('palette_id') or '已确认'}）",
        "- 画像正文与旅程正文：逐项沿用 04，不在本步骤改写。", "", "</details>", "",
        "## 请确认", "",
        f"> 请只确认最终 **{proposed_count} 页**及上述页面分配。确认后回复“确认报告结构”。", "",
    ]
    digest = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    lines.append(f"<!-- 机器内容指纹：{digest} -->")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate delta-only 05-report.md from 05-report.draft.json.")
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    draft_path = process_dir / "05-report.draft.json"
    if not draft_path.is_file():
        raise SystemExit("05-report.draft.json 不存在。先组装结构化报告草稿，禁止提前写 05-report.json。")
    report = _load(draft_path)
    try:
        from scripts.preflight_render import run_preflight
    except ImportError:
        from preflight_render import run_preflight
    preflight = run_preflight(process_dir, report)
    if not preflight["valid"]:
        raise SystemExit(
            "渲染预检未通过。05 确认稿尚未生成，避免用户确认后再进入修补循环。\n"
            + json.dumps(preflight, ensure_ascii=False, indent=2)
        )
    md_path = process_dir / "05-report.md"
    md_path.write_text(render_report_checkpoint_md(process_dir, report).rstrip() + "\n", encoding="utf-8")
    print(json.dumps({"rendered": str(md_path), "source": str(draft_path), "user_message": f"最终页面编排稿已生成：{md_path}。请先审阅本次新增决定；确认短语位于 MD 末尾。"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
