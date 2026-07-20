#!/usr/bin/env python3
"""Render human-readable Chinese 04 checkpoint drafts from structured JSON.

The draft JSON is the machine working copy.  The generated Markdown is the
human review surface.  Stable IDs and renderer enums are deliberately omitted
from visible Markdown; the final JSON keeps them for recovery and rendering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


FIELD_LABELS = {
    "basic_profile": "基本画像",
    "knowledge_background": "知识与经验",
    "responsibilities": "工作职责",
    "high_freq_tasks": "高频任务",
    "high_frequency_tasks": "高频任务",
    "kpi": "工作目标与衡量标准/KPI",
    "collaboration": "上下游协作",
    "business_systems": "常用系统与工具",
    "pain_points": "核心痛点",
    "experience_goals": "体验目标",
    "one_sentence_need": "一句话诉求",
    "representative_quotes": "代表性原话",
    "role": "角色",
    "team": "团队",
    "experience": "相关经验",
    "work_focus": "工作重点",
    "domains": "领域知识",
    "tools": "工具",
    "platforms": "平台",
    "demand_source": "需求来源",
    "deliverables": "交付物",
    "downstream_flow": "后续流转",
    "title": "要点",
    "detail": "说明",
    "percentage": "投入占比",
    "mention_count": "提及人数",
    "mentioned_by": "相关受访者",
    "evidence_count": "证据数",
    "evidence_quotes": "证据原话",
    "full": "完整展示",
    "condensed": "压缩展示",
    "omitted": "省略",
}

NODE_TYPE_LABELS = {
    "start": "起点", "step": "步骤", "action": "行动", "decision": "判断",
    "doc": "交付物", "end": "终点",
}
LINE_STYLE_LABELS = {"solid": "实线", "dashed": "虚线"}
BRANCH_LABELS = {"yes": "是", "no": "否", True: "是", False: "否"}
EVIDENCE_LABELS = {
    "primary": "访谈原话", "supplemental": "补充材料",
    "user_context": "用户补充", "synthesis": "研究归纳",
}
EMOTION_LEVEL_LABELS = {"high": "积极", "middle": "平稳", "low": "消极"}
COMPONENT_LABELS = {
    "basic_info": "基本信息", "responsibility_donut": "职责分布", "collaboration_flow": "上下游协作",
    "scenario_grid": "典型场景", "titled_list": "要点列表", "quote": "代表性原话",
    "pain_points": "核心痛点", "goals": "体验目标", "systems": "系统与工具",
}


def _text(value: Any) -> str:
    if value is None:
        return "材料未提及"
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value).strip()
    text = re.sub(r"persona-([0-9]+)", r"画像 \1", text, flags=re.I)
    text = text.replace("tob_journey_l1", "整体旅程").replace("tob_journey_l2", "单角色旅程").replace("journey_2c", "消费者旅程")
    text = re.sub(
        r"\[来源:([^\]]+)\]",
        lambda match: match.group(0) if re.fullmatch(r"P[0-9A-F]{8}", match.group(1).strip()) else "[来源:匿名来源待修复]",
        text,
    )
    return text or "材料未提及"


def _escape(value: Any) -> str:
    if value in (None, ""):
        return ""
    return _text(value).replace("|", "\\|").replace("\n", "<br>")


def _label(key: str, custom: dict[str, str] | None = None) -> str:
    if custom and custom.get(key):
        return custom[key]
    return FIELD_LABELS.get(key, key.replace("_", " "))


def _simple_lines(value: Any, custom: dict[str, str] | None = None, level: int = 0) -> list[str]:
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            label = _label(str(key), custom)
            if isinstance(child, (dict, list)):
                lines.append(f"{'  ' * level}- **{label}**")
                lines.extend(_simple_lines(child, custom, level + 1))
            else:
                lines.append(f"{'  ' * level}- **{label}：**{_text(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or item.get("label")
                detail = item.get("detail") or item.get("description") or item.get("content")
                if title:
                    suffix = f"：{_text(detail)}" if detail else ""
                    lines.append(f"{'  ' * level}- **{_text(title)}**{suffix}")
                    extras = {k: v for k, v in item.items() if k not in {
                        "title", "name", "label", "detail", "description", "content",
                        "mentioned_by", "evidence_quotes",
                    } and v not in (None, "", [], {})}
                    lines.extend(_simple_lines(extras, custom, level + 1))
                else:
                    lines.extend(_simple_lines(item, custom, level))
            else:
                lines.append(f"{'  ' * level}- {_text(item)}")
        return lines
    return [f"{'  ' * level}- {_text(value)}"]


def _collect_quotes(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence_quotes" and isinstance(child, list):
                for item in child:
                    if isinstance(item, dict):
                        quote = _text(item.get("quote") or item.get("text") or "")
                        source = str(item.get("source") or "").strip()
                        safe_source = source if re.fullmatch(r"P[0-9A-F]{8}", source) else "匿名来源待修复"
                        if quote and quote != "材料未提及":
                            result.append(f'[来源:{safe_source}]: "{quote}"')
                    elif str(item).strip():
                        result.append(_text(item))
            else:
                result.extend(_collect_quotes(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_collect_quotes(child))
    return list(dict.fromkeys(result))


def _context_lines(data: dict[str, Any]) -> list[str]:
    context = data.get("context_snapshot") or {}
    return [
        "## 研究上下文",
        "",
        f"- 研究问题：{_text(context.get('research_question'))}",
        f"- 决策用途：{_text(context.get('decision_use'))}",
        f"- 业务类型：{_text(context.get('research_type'))}",
        f"- 画像方式：{_text(context.get('paradigm'))}",
        "",
    ]


def render_personas_md(data: dict[str, Any], field_labels: dict[str, str] | None = None) -> str:
    status = "已确认" if data.get("status") in {"confirmed", "validated"} else "待用户确认"
    lines = ["# 04 用户画像内容确认", "", f"确认状态：{status}", ""]
    lines.extend(_context_lines(data))
    lines += [
        "## 一眼看全局", "",
        f"- 画像数量：{len(data.get('personas') or [])}",
        f"- 画像名称：{'、'.join(_text(p.get('name')) for p in data.get('personas') or [])}",
        "- 阅读顺序：先看画像边界，再逐个核对正文、证据薄弱点和信息取舍。", "",
    ]
    for index, persona in enumerate(data.get("personas") or [], 1):
        lines += [f"## {index}. {_text(persona.get('name'))}", "", _text(persona.get("description")), ""]
        lines += ["### 画像边界", "", f"- 纳入受访者数量：{_text(persona.get('user_count'))}", ""]
        fields = persona.get("fields") or {}
        for key, value in fields.items():
            lines += [f"### {_label(str(key), field_labels)}", ""]
            lines.extend(_simple_lines(value, field_labels))
            quotes = _collect_quotes(value)
            if quotes:
                lines += ["", "<details>", "<summary>展开本字段的证据原话</summary>", ""]
                lines.extend(f"- {quote}" for quote in quotes)
                lines += ["", "</details>"]
            lines.append("")
        components = persona.get("display_components") or []
        if components:
            lines += ["### 最终报告正文核对", "", "<details>", "<summary>展开将进入最终报告的组件正文</summary>", ""]
            for component in components:
                component_type = str(component.get("type") or "")
                lines += [f"#### {COMPONENT_LABELS.get(component_type, '内容模块')}", ""]
                lines.extend(_simple_lines(component.get("props") or {}, field_labels))
                lines.append("")
            lines += ["</details>", ""]
        decisions = persona.get("field_decisions") or []
        if decisions:
            lines += ["### 字段展示取舍", "", "| 字段 | 处理方式 | 原因 | 信息损失 |", "|---|---|---|---|"]
            for item in decisions:
                lines.append("| {} | {} | {} | {} |".format(
                    _escape(_label(str(item.get("field") or ""), field_labels)),
                    _escape(FIELD_LABELS.get(str(item.get("presentation")), item.get("presentation"))),
                    _escape(item.get("reason")), _escape(item.get("information_loss")),
                ))
            lines.append("")
    if data.get("merge_rules"):
        lines += ["## 合并规则", ""] + _simple_lines(data["merge_rules"]) + [""]
    if data.get("risks"):
        lines += ["## 证据薄弱点与风险", ""] + _simple_lines(data["risks"]) + [""]
    lines += [
        "## 请确认", "",
        "请重点检查画像命名、边界、每项正文、证据薄弱点和信息取舍。需要修改时直接指出具体画像与具体内容。", "",
        "> 全部内容准确后，请单独回复“确认画像内容”。", "",
    ]
    digest = hashlib.sha256(json.dumps(data.get("personas") or [], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    lines.append(f"<!-- 机器内容指纹：{digest} -->")
    return "\n".join(lines)


def _stage_maps(props: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    stages = props.get("stages") or []
    stage_names = {
        str(item.get("id")): _text(item.get("name"))
        for item in stages if isinstance(item, dict)
    }
    for index, item in enumerate(stages):
        if not isinstance(item, dict):
            stage_names[str(index)] = _text(item)
    lanes = props.get("lanes") or []
    lane_names = {str(item.get("id")): _text(item.get("name")) for item in lanes}
    return stages, stage_names, lane_names


def _node_maps(props: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    nodes = props.get("nodes") or []
    return nodes, {str(item.get("id")): _text(item.get("label")) for item in nodes}


def _render_tob_journey(
    lines: list[str], journey: dict[str, Any], index: int,
    overall_stage_names: list[str] | None = None,
) -> None:
    props = journey.get("props") or {}
    stages, stage_names, lane_names = _stage_maps(props)
    nodes, node_names = _node_maps(props)
    kind = "整体旅程" if journey.get("component_type") == "tob_journey_l1" else "单角色旅程"
    title = props.get("banner_title") or f"旅程 {index}"
    lines += [f"## {index}. {kind}：{_text(title)}", ""]
    if props.get("banner_subtitle"):
        lines += [_text(props["banner_subtitle"]), ""]
    local_stage_names = [_text(s.get("name")) for s in stages]
    if kind == "整体旅程":
        location = f"全局地图 > 跨角色整体旅程 > {_text(title)}"
        relation = "这是所有单角色旅程的共同坐标系。"
    else:
        shared = [name for name in local_stage_names if name in (overall_stage_names or [])]
        location = f"全局地图 > 单角色旅程 > {_text(title)}"
        relation = (
            f"本段对应整体旅程中的：{'、'.join(shared)}。" if shared
            else "本段是该角色的局部工作链；请结合上方旅程总览地图判断其衔接位置。"
        )
    lines += ["### 你现在在这里", "", f"- 位置：{location}", f"- 与全局的关系：{relation}", ""]
    lines += ["### 一眼看全局", "", " → ".join(local_stage_names), ""]
    lines += ["| 顺序 | 阶段 | 子阶段 | 参与角色 | 该阶段的关键动作与判断 |", "|---:|---|---|---|---|"]
    for order, stage in enumerate(stages, 1):
        sid = str(stage.get("id"))
        stage_nodes = [n for n in nodes if str(n.get("stage")) == sid]
        participants = list(dict.fromkeys(lane_names.get(str(n.get("lane")), "未标注角色") for n in stage_nodes))
        actions = "；".join(_text(n.get("label")) for n in stage_nodes) or "材料未提及"
        sub = " / ".join(_text(x) for x in stage.get("subStages") or []) or "材料未提及"
        lines.append(f"| {order} | {_escape(stage.get('name'))} | {_escape(sub)} | {_escape('、'.join(participants))} | {_escape(actions)} |")
    lines.append("")
    if lane_names:
        lines += ["### 角色 × 阶段责任矩阵", ""]
        known_stage_ids = {str(s.get("id")) for s in stages}
        has_branch = any(str(node.get("stage")) not in known_stage_ids for node in nodes)
        headers = [_text(s.get("name")) for s in stages] + (["支线"] if has_branch else [])
        lines += ["| 角色 | " + " | ".join(_escape(x) for x in headers) + " |", "|---|" + "---|" * len(headers)]
        for lane_id, lane_name in lane_names.items():
            cells = []
            for stage in stages:
                labels = [_text(n.get("label")) for n in nodes if str(n.get("lane")) == lane_id and str(n.get("stage")) == str(stage.get("id"))]
                cells.append("；".join(labels) or "")
            if has_branch:
                branch_labels = [_text(n.get("label")) for n in nodes if str(n.get("lane")) == lane_id and str(n.get("stage")) not in known_stage_ids]
                cells.append("；".join(branch_labels) or "")
            lines.append(f"| {_escape(lane_name)} | " + " | ".join(_escape(x) for x in cells) + " |")
        lines.append("")
    edges = props.get("edges") or []
    if edges:
        lines += ["### 关键衔接与分支", "", "| 从哪里 | 到哪里 | 关系 | 分支条件 | 说明 |", "|---|---|---|---|---|"]
        key_edges = [edge for edge in edges if edge.get("branch") not in (None, "", False) or str(edge.get("style") or "solid") == "dashed"]
        for edge in key_edges or edges[:8]:
            branch = BRANCH_LABELS.get(edge.get("branch"), edge.get("branch") or "")
            lines.append("| {} | {} | {} | {} | {} |".format(
                _escape(node_names.get(str(edge.get("from")), "未找到起点")),
                _escape(node_names.get(str(edge.get("to")), "未找到终点")),
                _escape(LINE_STYLE_LABELS.get(str(edge.get("style") or "solid"), edge.get("style"))),
                _escape(branch), _escape(edge.get("label") or edge.get("note") or ""),
            ))
        lines.append("")
        if len(edges) > len(key_edges or edges[:8]):
            lines += ["<details>", "<summary>展开完整衔接清单</summary>", "", "| 从哪里 | 到哪里 | 关系 | 分支条件 |", "|---|---|---|---|"]
            for edge in edges:
                branch = BRANCH_LABELS.get(edge.get("branch"), edge.get("branch") or "")
                lines.append("| {} | {} | {} | {} |".format(
                    _escape(node_names.get(str(edge.get("from")), "未找到起点")),
                    _escape(node_names.get(str(edge.get("to")), "未找到终点")),
                    _escape(LINE_STYLE_LABELS.get(str(edge.get("style") or "solid"), edge.get("style"))),
                    _escape(branch),
                ))
            lines += ["", "</details>", ""]
    for title_key, key in (("关注点与痛点", "focusAreas"), ("工具与触点", "tools")):
        value = props.get(key)
        if value:
            lines += [f"### {title_key}", ""] + _simple_lines(value) + [""]


def _render_2c_journey(lines: list[str], journey: dict[str, Any], index: int) -> None:
    props = journey.get("props") or {}
    stages = props.get("stages") or []
    title = props.get("title") or props.get("banner_title") or f"旅程 {index}"
    lines += [f"## {index}. 消费者旅程：{_text(title)}", "", "### 一眼看全局", "", " → ".join(_text(s.get("name") if isinstance(s, dict) else s) for s in stages), ""]
    stage_names = [_text(s.get("name") if isinstance(s, dict) else s) for s in stages]
    cells = props.get("cells") or []
    dimensions = props.get("dimensions") or []
    if stage_names and isinstance(cells, (dict, list)):
        lines += ["| 维度 | " + " | ".join(_escape(x) for x in stage_names) + " |", "|---|" + "---|" * len(stage_names)]
        rows = list(cells.items()) if isinstance(cells, dict) else list(zip(dimensions, cells))
        for dimension, row in rows:
            values = list(row.values()) if isinstance(row, dict) else list(row or [])
            rendered = []
            for cell in values[:len(stage_names)]:
                if isinstance(cell, dict):
                    rendered.append("；".join(_text(cell.get(k)) for k in ("keyword", "summary", "text", "content") if cell.get(k)))
                else:
                    rendered.append(_text(cell))
            rendered += [""] * (len(stage_names) - len(rendered))
            lines.append(f"| {_escape(_label(str(dimension)))} | " + " | ".join(_escape(x) for x in rendered) + " |")
        lines.append("")


def _evidence_target_label(journey: dict[str, Any], target: Any) -> str:
    raw = str(target or "")
    props = journey.get("props") or {}
    _, stage_names, _ = _stage_maps(props)
    _, node_names = _node_maps(props)
    kind, _, ident = raw.partition(":")
    if kind == "stage":
        return f"阶段：{stage_names.get(ident, '对应阶段')}"
    if kind == "node":
        return f"步骤：{node_names.get(ident, '对应步骤')}"
    if kind == "edge":
        parts = re.split(r"(?:->|→)", ident)
        if len(parts) == 2:
            return f"衔接：{node_names.get(parts[0], '上一步')} → {node_names.get(parts[1], '下一步')}"
        return "流程衔接"
    return {"focus": "关注点或痛点", "tool": "工具或触点", "cell": "旅程单元格", "emotion": "情绪变化"}.get(kind, "旅程内容")
    emotions = props.get("emotion") or []
    if emotions:
        lines += ["### 情绪变化", "", "| 阶段 | 情绪说明 | 情绪倾向 |", "|---|---|---|"]
        for stage_name, emotion in zip(stage_names, emotions):
            if isinstance(emotion, dict):
                lines.append(f"| {_escape(stage_name)} | {_escape(emotion.get('stage_label'))} | {_escape(EMOTION_LEVEL_LABELS.get(str(emotion.get('level')), emotion.get('level')))} |")
        lines.append("")


def render_journeys_md(data: dict[str, Any]) -> str:
    status = "已确认" if data.get("status") in {"confirmed", "validated"} else "待用户确认"
    lines = ["# 04 用户旅程内容确认", "", f"确认状态：{status}", ""]
    lines.extend(_context_lines(data))
    journeys = data.get("journeys") or []
    overall = [j for j in journeys if j.get("component_type") == "tob_journey_l1"]
    individual = [j for j in journeys if j.get("component_type") != "tob_journey_l1"]
    lines += [
        "## 阅读导航", "",
        f"- 共 {len(journeys)} 条旅程，其中整体旅程 {len(overall)} 条，单角色或单画像旅程 {len(individual)} 条。",
        "- 2B/2D 先看阶段链和角色责任矩阵，再检查分支与证据。2C 直接看阶段 × 内容维度表。",
        "- 机器 ID、组件类型和连线编码保存在 JSON 中，不占用人类阅读空间。", "",
    ]
    if journeys:
        lines += ["## 旅程总览地图", "", "| 编号 | 层级 | 旅程 | 覆盖阶段 | 阅读目的 |", "|---:|---|---|---|---|"]
        for index, journey in enumerate(journeys, 1):
            props = journey.get("props") or {}
            component_type = journey.get("component_type")
            if component_type == "tob_journey_l1":
                level = "整体"
                purpose = "先确认共同阶段与角色分工"
            elif component_type == "tob_journey_l2":
                level = "单角色"
                purpose = "再确认该角色的局部流程"
            else:
                level = "单画像"
                purpose = "按阶段核对想法、行为、痛点与触点"
            title = props.get("banner_title") or props.get("title") or f"旅程 {index}"
            stage_names = [
                _text(stage.get("name") if isinstance(stage, dict) else stage)
                for stage in props.get("stages") or []
            ]
            lines.append(f"| {index} | {level} | {_escape(title)} | {_escape(' → '.join(stage_names))} | {purpose} |")
        lines.append("")
    try:
        from scripts.journey_alignment import expected_alignment_review
    except ImportError:
        from journey_alignment import expected_alignment_review  # type: ignore
    review = expected_alignment_review(data)
    if review["mode"] == "guided_rounds":
        lines += ["## 分轮确认进度", "", "| 轮次 | 核对内容 | 状态 | 用户确认语 |", "|---:|---|---|---|"]
        for number, item in enumerate(review["rounds"], 1):
            state = "已确认" if item["confirmed"] else "待确认"
            lines.append(f"| {number} | {item['label']} | {state} | {item['required_phrase']} |")
        pending = next((item for item in review["rounds"] if not item["confirmed"]), None)
        if pending:
            lines += ["", f"> 当前只核对：{pending['label']}。确认后请回复“{pending['required_phrase']}”。后续轮次暂不请求确认。", ""]
        else:
            lines += ["", "> 四轮均已完成。现在可以对整份旅程做最终确认。", ""]
    if not journeys:
        lines += ["## 本次不生成旅程", "", _text(data.get("not_applicable_reason")), ""]
    overall_stage_names: list[str] = []
    if overall:
        overall_stage_names = [
            _text(stage.get("name") if isinstance(stage, dict) else stage)
            for stage in (overall[0].get("props") or {}).get("stages") or []
        ]
    for index, journey in enumerate(journeys, 1):
        if journey.get("component_type") in {"tob_journey_l1", "tob_journey_l2"}:
            _render_tob_journey(lines, journey, index, overall_stage_names)
        else:
            _render_2c_journey(lines, journey, index)
        bindings = journey.get("evidence_bindings") or []
        if bindings:
            lines += ["<details>", "<summary>展开逐项证据与归纳依据</summary>", "", "| 序号 | 支持内容 | 证据类型 | 匿名来源 | 原话或归纳依据 |", "|---:|---|---|---|---|"]
            for number, binding in enumerate(bindings, 1):
                sources = "、".join(binding.get("source_ids") or []) or "无单一来源"
                lines.append(f"| {number} | {_escape(_evidence_target_label(journey, binding.get('target')))} | {_escape(EVIDENCE_LABELS.get(binding.get('evidence_type'), binding.get('evidence_type')))} | {_escape(sources)} | {_escape(binding.get('quote_or_basis'))} |")
            lines += ["", "</details>", ""]
    gaps = (data.get("quality_review") or {}).get("evidence_gaps") or []
    lines += ["## 证据缺口", ""] + (_simple_lines(gaps) if gaps else ["- 未记录证据缺口。"])
    lines += ["", "## 请确认", ""]
    if review["mode"] == "guided_rounds":
        pending = next((item for item in review["rounds"] if not item["confirmed"]), None)
        if pending:
            lines += [
                f"当前只确认“{pending['label']}”。如有问题，请指出旅程编号、阶段名称和具体内容；当前检查点继续保持待确认。", "",
                f"> 本轮准确后，请单独回复“{pending['required_phrase']}”。", "",
            ]
        else:
            lines += ["> 四轮内容均准确后，请单独回复“确认旅程内容”。", ""]
    else:
        lines += [
            "请按阶段顺序检查完整内容。任何一处看不清时，请要求模型缩小范围说明，当前内容保持待确认。", "",
            "> 全部旅程内容准确后，请单独回复“确认旅程内容”。", "",
        ]
    digest = hashlib.sha256(json.dumps(journeys, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    lines.append(f"<!-- 机器内容指纹：{digest} -->")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Chinese human-review Markdown from a structured 04 draft JSON.")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--stem", required=True, choices=["04-personas", "04-journeys"])
    parser.add_argument("--input", help="Draft JSON path. Defaults to <stem>.draft.json in process dir.")
    parser.add_argument("--output", help="Markdown path. Defaults to <stem>.md in process dir.")
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    input_path = Path(args.input) if args.input else process_dir / f"{args.stem}.draft.json"
    output_path = Path(args.output) if args.output else process_dir / f"{args.stem}.md"
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if args.stem == "04-personas":
        try:
            from scripts.privacy_guard import validate_privacy_in_report, validate_privacy_in_markdown
        except ImportError:
            from privacy_guard import validate_privacy_in_report, validate_privacy_in_markdown
        privacy_issues = validate_privacy_in_report(data, process_dir)
        if privacy_issues:
            raise ValueError("04-personas 草稿含隐私问题，禁止生成用户确认稿：" + json.dumps(privacy_issues, ensure_ascii=False))
        alignment_path = process_dir / "03-field-alignment.json"
        custom = {}
        if alignment_path.is_file():
            custom = json.loads(alignment_path.read_text(encoding="utf-8")).get("fields_display_names") or {}
        content = render_personas_md(data, custom)
        md_privacy_issues = validate_privacy_in_markdown(content, process_dir, path=output_path.name)
        if md_privacy_issues:
            raise ValueError("生成的 04-personas.md 未通过隐私检查：" + json.dumps(md_privacy_issues, ensure_ascii=False))
    else:
        content = render_journeys_md(data)
    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(json.dumps({"rendered": str(output_path), "source": str(input_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
