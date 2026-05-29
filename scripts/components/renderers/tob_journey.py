from __future__ import annotations

import math

from ._utils import escape, screenshot_exists


def _render_banner(title: str, subtitle: str) -> str:
    return (
        '<div class="tob-banner"><div class="tob-banner-main">'
        f'<div class="tob-banner-title">{escape(title)}</div>'
        f'<div class="tob-banner-subtitle">{escape(subtitle)}</div>'
        '</div></div>'
    )


def _render_stage_header(stages: list[dict]) -> str:
    return "".join(
        '<div class="tob-stage-tag">'
        f'<span class="tob-stage-number">{escape(stage["number"])}</span>{escape(stage["name"])}'
        '</div>'
        for stage in stages
    )


def render_substage_row(stages_substages: list[list[str]]) -> str:
    cells = []
    for stage_subs in stages_substages:
        arrows = []
        for i, sub in enumerate(stage_subs):
            cls = "tob-substage-arrow" + (" is-terminal" if i == len(stage_subs) - 1 else "")
            arrows.append(f'<span class="{cls}">{escape(sub)}</span>')
        cells.append(f'<div class="tob-substage-cell">{"".join(arrows)}</div>')
    return "".join(cells)


def render_l1_substage_cells(stages_substages: list[list[str]]) -> str:
    cells = []
    sep = '<span class="sep">&rsaquo;</span>'
    for stage_subs in stages_substages:
        content = sep.join(f'<span>{escape(sub)}</span>' for sub in stage_subs)
        cells.append(f'<div class="tob-substage-cell l1-substage-bar">{content}</div>')
    return "".join(cells)


def _render_flow_cell(cell: dict, terminal: bool = False, highlight: bool = False) -> str:
    cell_cls = "tob-flow-cell" + (" is-terminal" if terminal else "")
    pill_cls = "tob-flow-pill" + (" is-highlight" if highlight else "")
    evidence = escape(cell.get("evidence", ""), quote=True)
    ev_attr = f' data-evidence="{evidence}"' if evidence else ""
    return (
        f'<div class="{cell_cls}">'
        f'<span class="{pill_cls}"{ev_attr}>{escape(cell["text"])}</span>'
        '</div>'
    )


def _render_focus_card(focus: dict, stage_idx: int, persona_id: str, reserve_image_slot: bool = False) -> str:
    cls = "tob-focus-card"
    if focus.get("is_pain"):
        cls += " is-pain"
    screenshot_name = focus.get("screenshot") or f"focus-{persona_id}-{stage_idx}.png"
    if screenshot_exists(screenshot_name):
        cls += " has-screenshot"
        mock = f'<img class="tob-focus-card-mock" src="assets/界面截图/{escape(screenshot_name, quote=True)}">'
    elif reserve_image_slot:
        cls += " has-screenshot"
        mock = '<div class="tob-focus-card-mock is-reserved">截图占位</div>'
    else:
        mock = '<div class="tob-focus-card-mock is-empty">无截图</div>'
    evidence_attr = f' data-evidence="{escape(focus.get("evidence", ""), quote=True)}"' if focus.get("evidence") else ""
    return (
        f'<div class="{cls}"{evidence_attr}>{mock}'
        f'<div class="tob-focus-card-title">{escape(focus["title"])}</div>'
        f'<div class="tob-focus-card-body">{escape(focus["body"])}</div>'
        '</div>'
    )


def _render_focus_cell(focuses: list[dict], persona_id: str = "persona", reserve_image_slot: bool = False) -> str:
    cells = []
    for stage_idx, focus in enumerate(focuses):
        cards = focus.get("cards") or [focus]
        cards_html = "".join(_render_focus_card(card, stage_idx, persona_id, reserve_image_slot) for card in cards)
        cells.append(f'<div class="tob-focus-cell">{cards_html}</div>')
    return "".join(cells)

def _render_uml_stage_header(stages: list[dict]) -> str:
    return "".join(
        '<div class="tob-stage-tag">'
        f'<span class="tob-stage-number">{idx + 1}</span>{escape(stage["name"])}'
        '</div>'
        for idx, stage in enumerate(stages)
    )


def _render_tools_touchpoint_cells(stages: list[dict], tools_touchpoints: list | None) -> str:
    tools = tools_touchpoints if tools_touchpoints is not None else [[] for _ in stages]
    cells = []
    for idx, _stage in enumerate(stages):
        tags = tools[idx] if idx < len(tools) else []
        if tags:
            inner = "".join(f'<span class="tob-tools-tag">{escape(tag)}</span>' for tag in tags)
        else:
            inner = '<span class="tob-tools-empty">—</span>'
        cells.append(f'<div class="tob-tools-cell">{inner}</div>')
    return "".join(cells)


def _check_l2_tools_touchpoints(stages: list[dict], tools_touchpoints: list | None) -> None:
    if tools_touchpoints is None:
        return
    if len(tools_touchpoints) != len(stages):
        raise ValueError(
            f"P8-L2-TOOLS-LEN: tob_journey_l2.tools_touchpoints 应与 stages 等长"
            f"({len(stages)} 项)，当前为 {len(tools_touchpoints)} 项"
        )


def _render_l2_uml_hybrid(props: dict) -> str:
    stages = props["stages"]
    substages = [stage.get("subStages", []) for stage in stages]
    tools_touchpoints = props.get("tools_touchpoints")
    _check_l2_tools_touchpoints(stages, tools_touchpoints)
    focuses = props.get("focuses", [])
    reserve_image_slot = props.get("focus_mode") == "image_placeholder"
    focus_cells = _render_focus_cell(focuses, "l2", reserve_image_slot) if focuses else ""
    return (
        f'<div class="tob-l2-uml-hybrid" style="--stages:{len(stages)};--rail-rows:42px 42px 42px 180px 1fr;--main-rows:42px 42px 42px 180px 1fr;">'
        f'{_render_banner(props["banner_title"], props["banner_subtitle"])}'
        '<div class="tob-body"><div class="tob-rail">'
        '<div class="tob-rail-cell tob-rail-stages">阶段</div>'
        '<div class="tob-rail-cell tob-rail-substages">子阶段</div>'
        '<div class="tob-rail-cell tob-rail-tools">工具/触点</div>'
        '<div class="tob-rail-cell tob-rail-dim">工作流程</div>'
        '<div class="tob-rail-cell tob-rail-dim">关注点 / 痛点</div>'
        '</div><div class="tob-main">'
        f'{_render_uml_stage_header(stages)}{render_l1_substage_cells(substages)}'
        f'{_render_tools_touchpoint_cells(stages, tools_touchpoints)}'
        f'<div class="tob-l2-uml-cell">{_render_uml_journey(props, show_lane_rail=False, density_mode="l2")}</div>'
        f'{focus_cells}'
        '</div></div></div>'
    )


def _render_stage_board(stages: list[dict]) -> str:
    n = len(stages)
    if n == 3:
        row_style = ""
        cell_style = ""
    else:
        row_style = f' style="grid-template-columns:92px repeat({n}, 1fr);"'
        cell_style = ' style="grid-column:span 1;"'
    stage_cells = "".join(
        f'<div class="l1-stage-cell"{cell_style}>'
        f'<div class="l1-stage-tag"><span class="l1-stage-num">{i + 1}</span>{escape(stage["name"])}</div>'
        f'</div>'
        for i, stage in enumerate(stages)
    )
    substage_cells = "".join(
        f'<div class="l1-substage-bar"{cell_style}>'
        + '<span class="sep">›</span>'.join(f'<span>{escape(sub)}</span>' for sub in stage["subStages"])
        + '</div>'
        for stage in stages
    )
    return (
        f'<div class="l1-row stage-row"{row_style}>'
        f'<div class="l1-rail-cell head">阶段</div>{stage_cells}</div>'
        f'<div class="l1-row substage-row"{row_style}>'
        f'<div class="l1-rail-cell head">子阶段</div>{substage_cells}</div>'
    )


def _uml_node_size(node_type: str, label: str, variant: str = "dense") -> tuple[int, int]:
    n = len(label)
    if variant == "wide_uml":
        if node_type in ("start", "end"):
            return (170, 52) if n > 4 else (118, 36)
        if node_type == "decision":
            return 116, 64
        if node_type == "doc":
            return 150, 40
        if node_type == "action":
            if n <= 4:
                return 100, 52
            return max(120, min(135, n * 11 + 36)), 56
        if node_type == "step":
            if n <= 4:
                return 100, 52
            return max(105, min(160, n * 11 + 38)), 52
        return max(100, min(150, n * 11 + 38)), 52

    if node_type in ("start", "end"):
        return max(76, min(94, n * 7 + 36)), 26
    if node_type == "decision":
        return max(82, min(98, n * 7 + 36)), 44
    if node_type == "doc":
        return max(80, min(96, n * 7 + 36)), 24
    if node_type == "action":
        return max(76, min(94, n * 7 + 36)), 28
    return max(66, min(92, n * 7 + 36)), 28


def _anchor(pos: dict, side: str) -> tuple[float, float]:
    if side == "top":
        return pos["cx"], pos["y"]
    if side == "right":
        return pos["x"] + pos["w"], pos["cy"]
    if side == "bottom":
        return pos["cx"], pos["y"] + pos["h"]
    if side == "left":
        return pos["x"], pos["cy"]
    raise ValueError(f"unsupported anchor side: {side}")




def _branch_label_near_source(from_pos: dict, to_pos: dict) -> tuple[float, float]:
    same_track = abs(from_pos["cy"] - to_pos["cy"]) < 1
    same_lane = from_pos.get("lane") == to_pos.get("lane")
    same_stage = from_pos.get("stage") == to_pos.get("stage")
    moving_right = to_pos["cx"] >= from_pos["cx"]

    if same_track:
        if moving_right:
            return from_pos["x"] + from_pos["w"] + 14, from_pos["cy"] - 11
        return from_pos["x"] - 14, from_pos["cy"] - 11

    if same_stage:
        dx = to_pos["cx"] - from_pos["cx"]
        if abs(dx) > 10:
            if dx > 0:
                return from_pos["x"] + from_pos["w"] + 14, from_pos["cy"] - 11
            return from_pos["x"] - 14, from_pos["cy"] - 11
        if from_pos["cy"] < to_pos["cy"]:
            return from_pos["cx"] + 13, from_pos["y"] + from_pos["h"] + 13
        return from_pos["cx"] + 13, from_pos["y"] - 13

    if same_lane:
        if moving_right:
            return from_pos["x"] + from_pos["w"] + 14, from_pos["cy"] - 11
        return from_pos["x"] - 14, from_pos["cy"] - 11

    if moving_right:
        return from_pos["x"] + from_pos["w"] + 14, from_pos["cy"] - 11
    return from_pos["x"] - 14, from_pos["cy"] - 11


def _edge_path(from_pos: dict, to_pos: dict) -> tuple[str, float, float]:
    same_track = abs(from_pos["cy"] - to_pos["cy"]) < 1
    same_lane = from_pos.get("lane") == to_pos.get("lane")
    same_stage = from_pos.get("stage") == to_pos.get("stage")
    moving_right = to_pos["cx"] >= from_pos["cx"]

    if same_track:
        if moving_right:
            sx, sy = _anchor(from_pos, "right")
            tx, ty = _anchor(to_pos, "left")
            return f"M {sx:.0f} {sy:.0f} H {tx:.0f}", from_pos["x"] + from_pos["w"] + 14, sy - 6
        sx, sy = _anchor(from_pos, "left")
        tx, ty = _anchor(to_pos, "right")
        return f"M {sx:.0f} {sy:.0f} H {tx:.0f}", from_pos["x"] - 14, sy - 6

    # Same-stage cross-row edges can leave a decision diamond from any side.
    # Pick the side facing the target first, which reduces stacked lines near the
    # top/bottom points and keeps the final segment pointing into the target.
    if same_stage:
        dx = to_pos["cx"] - from_pos["cx"]
        target_above = to_pos["cy"] < from_pos["cy"]
        if abs(dx) > 10:
            if dx > 0:
                sx, sy = _anchor(from_pos, "right")
            else:
                sx, sy = _anchor(from_pos, "left")
            tx, ty = _anchor(to_pos, "bottom" if target_above else "top")
            return f"M {sx:.0f} {sy:.0f} H {tx:.0f} V {ty:.0f}", sx + (14 if dx > 0 else -14), sy - 6
        if target_above:
            sx, sy = _anchor(from_pos, "top")
            tx, ty = _anchor(to_pos, "bottom")
        else:
            sx, sy = _anchor(from_pos, "bottom")
            tx, ty = _anchor(to_pos, "top")
        mid_y = (sy + ty) / 2
        label_y = sy + 13 if ty > sy else sy - 13
        return f"M {sx:.0f} {sy:.0f} V {mid_y:.0f} H {tx:.0f} V {ty:.0f}", sx + 13, label_y


    if same_lane:
        if moving_right:
            sx, sy = _anchor(from_pos, "right")
            tx, ty = _anchor(to_pos, "left")
            mid_x = (sx + tx) / 2
        else:
            sx, sy = _anchor(from_pos, "left")
            tx, ty = _anchor(to_pos, "right")
            mid_x = (sx + tx) / 2
        return f"M {sx:.0f} {sy:.0f} H {mid_x:.0f} V {ty:.0f} H {tx:.0f}", from_pos["x"] + (from_pos["w"] + 14 if moving_right else -14), sy - 6

    if moving_right:
        sx, sy = _anchor(from_pos, "right")
        tx, ty = _anchor(to_pos, "left")
    else:
        sx, sy = _anchor(from_pos, "left")
        tx, ty = _anchor(to_pos, "right")
    mid_x = (sx + tx) / 2
    return f"M {sx:.0f} {sy:.0f} H {mid_x:.0f} V {ty:.0f} H {tx:.0f}", from_pos["x"] + (from_pos["w"] + 14 if moving_right else -14), sy - 6


def _render_node(pos: dict) -> str:
    """渲染单个 UML 节点。

    label 用纯 escape(不走 escape_allow_strong),因为 SVG foreignObject 内的
    label 是结构化标签文字(start/end/step/action/decision/doc),没有高亮诉求。
    与 toc.py 的 escape_allow_strong 风格不同是有意为之。
    """
    node_type = pos["type"]
    w = pos["w"]
    h = pos["h"]
    if node_type in ("start", "end"):
        shape = f'<rect width="{w:.0f}" height="{h:.0f}" rx="18"/>'
    elif node_type == "step":
        shape = f'<rect width="{w:.0f}" height="{h:.0f}" rx="3"/>'
    elif node_type == "action":
        shape = f'<rect width="{w:.0f}" height="{h:.0f}" rx="5"/>'
    elif node_type == "decision":
        shape = f'<polygon points="{w / 2:.0f},0 {w:.0f},{h / 2:.0f} {w / 2:.0f},{h:.0f} 0,{h / 2:.0f}"/>'
    elif node_type == "doc":
        shape = f'<path d="M0,0 H{w:.0f} V{h - 4:.0f} Q{w * 0.75:.0f},{h + 4:.0f} {w / 2:.0f},{h:.0f} Q{w * 0.25:.0f},{h - 4:.0f} 0,{h:.0f} Z"/>'
    else:
        shape = f'<rect width="{w:.0f}" height="{h:.0f}" rx="3"/>'
    label_cls = "l1-node-label small" if len(pos["label"]) > 6 else "l1-node-label"
    return (
        f'<g class="l1-node l1-{escape(node_type, quote=True)}" transform="translate({pos["x"]:.0f} {pos["y"]:.0f})">'
        f'{shape}'
        f'<foreignObject width="{w:.0f}" height="{h:.0f}"><div xmlns="http://www.w3.org/1999/xhtml" class="{label_cls}">{escape(pos["label"])}</div></foreignObject>'
        '</g>'
    )


# 协同语义门禁阈值(2026-05-29 新增)。
# 只对「多角色全景 L1」(lanes >= 3 且 stages >= 3)生效;L2 单泳道 / 小流程豁免。
#
# 定位:这是「反退化下限」,不是「真值上限」。阈值刻意标在 skill 现有合格样例
# (golden_samples / gallery 里的 tob_journey_l1)之下 —— 那些样例 decision 2~3 /
# doc 1~2 / dashed 2 / 跨泳道 20~53%,真值(电力调度员)更高(5/8/11/46%),
# 退化的「N 条平行流水线」则全是 0。门禁负责挡住「全是 0」的退化(被 4 个维度
# 独立命中);把图拉到真值级丰富度是 REGISTRY §3.0 协同语义清单 + 真值范例的活,
# 那是「指引/上限」,不该用硬 reject 去逼(否则连 skill 自带的合格样例都会被误杀)。
# branch:yes/no 同理 —— 现有合格样例都没标 branch,所以只写进清单指引,不进硬门禁。
COOP_MIN_LANES = 3
COOP_MIN_STAGES = 3
COOP_MIN_CROSS_LANE_EDGE_RATIO = 0.15  # 真值 46% / 样例 20~53% / 退化 0%
COOP_MIN_DECISION_NODES = 2            # 真值 5 / 样例 2~3 / 退化 0
COOP_MIN_DOC_NODES = 1                 # 真值 8 / 样例 1~2 / 退化 0
COOP_MIN_DASHED_EDGES = 1              # 真值 11 / 样例 2 / 退化 0(async/系统推送)

# L2 工作流语义门禁(2026-05-29) — 与 L1 共用 decision/doc/branch 语义,无跨泳道要求
L2_MAX_NODES_PER_CELL = 4

# L1 多角色与 L2 单角色 UML 共用几何常量(密度/协同门禁除外)
TRACK_MIN_GAP = 4
STAGGER_ROW_Y_TOP = 0.34
STAGGER_ROW_Y_BOTTOM = 0.66


def _normalize_focus_token(text: str) -> str:
    import re

    return re.sub(r"[\s\?？!！。、,，:：;；]", "", (text or "").strip())


def _is_decision_question(label: str) -> bool:
    t = (label or "").strip()
    if not t:
        return False
    if t.endswith("?") or t.endswith("？"):
        return True
    return any(
        kw in t
        for kw in ("是否", "能否", "可否", "要不要", "需不需要", "会不会", "有没有")
    )


def _ancestors_via_yes_path(edges: list[dict], node_id: str) -> set[str]:
    """沿非 branch:no 的入边反向追溯,得主线上的前序节点。"""
    ancestors: set[str] = set()
    stack = [node_id]
    while stack:
        cur = stack.pop()
        for e in edges:
            if e.get("to") != cur or e.get("branch") == "no":
                continue
            src = e.get("from", "")
            if src and src not in ancestors:
                ancestors.add(src)
                stack.append(src)
    return ancestors


def _is_valid_no_branch(decision_id: str, target_id: str, edges: list[dict]) -> bool:
    """否分支须指向「如果否会怎么办」的独立任务,不能回指主线上已有节点。"""
    if not decision_id or not target_id or decision_id == target_id:
        return False
    yes_targets = {
        e["to"]
        for e in edges
        if e.get("from") == decision_id and e.get("branch") == "yes"
    }
    if target_id in yes_targets:
        return False
    if target_id in _ancestors_via_yes_path(edges, decision_id):
        return False
    return True


def _sanitize_invalid_no_branches(edges: list[dict]) -> int:
    """移除装饰性否分支(回指主线前序节点)。返回删除条数。"""
    removed = 0
    i = 0
    while i < len(edges):
        e = edges[i]
        if e.get("branch") == "no":
            dec_id = e.get("from", "")
            tgt_id = e.get("to", "")
            if not _is_valid_no_branch(dec_id, tgt_id, edges):
                edges.pop(i)
                removed += 1
                continue
        i += 1
    return removed


def _workflow_decision_semantics_gate(
    nodes: list,
    edges: list,
    focuses: list | None = None,
    *,
    context: str = "L1/L2",
) -> None:
    """L1 与 L2 共用:菱形=问句判断;是=主线;否=可选且须指向独立补救任务。"""
    _sanitize_invalid_no_branches(edges)

    focuses = focuses or []
    focus_titles = {
        _normalize_focus_token(f.get("title", ""))
        for f in focuses
        if f.get("title")
    }

    edges_by_from: dict[str, list[dict]] = {}
    for edge in edges:
        edges_by_from.setdefault(edge.get("from", ""), []).append(edge)

    problems: list[str] = []
    for node in nodes:
        if node.get("type") != "decision":
            continue
        label = str(node.get("label", ""))
        nid = node.get("id", "")
        norm = _normalize_focus_token(label)
        if norm and norm in focus_titles:
            problems.append(
                f"decision「{label}」与下方 focuses 标题重复 — "
                f"「如果否」的说明写 focuses,菱形只保留主线判断"
            )
        elif not _is_decision_question(label):
            problems.append(
                f"decision「{label}」不是问句型判断 — "
                f"须用「是否/能否/…?」表达,不能把痛点标题塞进菱形"
            )

        outs = edges_by_from.get(nid, [])
        if not outs:
            problems.append(f"decision「{label}」没有出边")
            continue

        has_yes = any(e.get("branch") == "yes" for e in outs)
        has_unlabeled = any(not e.get("branch") for e in outs)
        if not has_yes and not has_unlabeled:
            problems.append(
                f"decision「{label}」须至少一条 branch:yes 或未标注的主线出边"
            )

        for e in outs:
            if e.get("branch") != "no":
                continue
            tgt = e.get("to", "")
            if not _is_valid_no_branch(nid, tgt, edges):
                problems.append(
                    f"decision「{label}」的 branch:no 指向「{tgt}」"
                    f" — 须为独立补救任务(如补全/退回/记录旁路),"
                    f"不能回指主线上已有节点;若无此类任务则删掉否分支,"
                    f"把「如果否」写进 focuses 或 skill 指引"
                )

    by_cell: dict[tuple[str, str], list[dict]] = {}
    for node in nodes:
        by_cell.setdefault((node.get("lane"), node.get("stage")), []).append(node)
    for (lane_id, stage_id), cell_nodes in by_cell.items():
        if len(cell_nodes) > L2_MAX_NODES_PER_CELL:
            problems.append(
                f"(lane={lane_id}, stage={stage_id}) 有 {len(cell_nodes)} 个节点"
                f"(建议 ≤{L2_MAX_NODES_PER_CELL}),请用 slot/track 错位或拆阶段"
            )

    if problems:
        detail = "".join(f"\n  - {p}" for p in problems)
        raise ValueError(
            f"tob_journey: {context} 工作流判断语义不足:{detail}\n"
            f"规则(L1/L2 统一):菱形=问句;「是」走主线任务;"
            f"「否」仅当图上有独立补救节点时才画,否则删掉否分支、"
            f"把「如果否」写 focuses。参考 REGISTRY.md §3.0.2。"
        )


def _l2_workflow_semantics_gate(
    nodes: list,
    edges: list,
    focuses: list | None = None,
) -> None:
    _workflow_decision_semantics_gate(nodes, edges, focuses, context="L2")


def _coop_semantics_gate(lanes: list, stages: list, nodes: list, edges: list) -> None:
    """协同语义门禁(2026-05-29 新增,issue:L1 协同语义不足)。

    密度门禁(_density_threshold)只保证「节点够多」,但 LLM 仍可能把多角色 L1
    写成 N 条互不相干的纵向流水线(全 step / 0 跨泳道 / 0 decision / 0 doc),
    渲染器会静默接受 —— 真值(电力调度员)却是「跨角色协同 UML 流程图」。

    本门禁只对多角色全景 L1(lanes >= 3 且 stages >= 3)生效,缺任一协同要素即
    fail-loud,逼 LLM 回字段对齐补真实的角色交接 / 判断 / 产物,而不是换皮打补丁。
    L2 单泳道、小流程(< 3 lane 或 < 3 stage)直接豁免,不误伤。
    """
    if len(lanes) < COOP_MIN_LANES or len(stages) < COOP_MIN_STAGES:
        return

    node_lane = {n["id"]: n.get("lane") for n in nodes}
    decision_count = sum(1 for n in nodes if n.get("type") == "decision")
    doc_count = sum(1 for n in nodes if n.get("type") == "doc")
    dashed_count = sum(1 for e in edges if e.get("style") == "dashed")
    total_edges = len(edges)
    cross_lane = sum(
        1 for e in edges if node_lane.get(e.get("from")) != node_lane.get(e.get("to"))
    )
    cross_ratio = (cross_lane / total_edges) if total_edges else 0.0

    problems: list[str] = []
    if cross_ratio < COOP_MIN_CROSS_LANE_EDGE_RATIO:
        problems.append(
            f"跨泳道边只占 {cross_ratio:.0%}(需 ≥ {COOP_MIN_CROSS_LANE_EDGE_RATIO:.0%},"
            f"实际 {cross_lane}/{total_edges} 条)。跨泳道边 = 角色交接;"
            f"没有交接,这张图只是 {len(lanes)} 条互不相干的平行流水线,不是协同图"
        )
    if decision_count < COOP_MIN_DECISION_NODES:
        problems.append(
            f"decision 节点只有 {decision_count} 个(需 ≥ {COOP_MIN_DECISION_NODES})。"
            f"真实流程一定有分叉判断(如「评审通过?」「构建成功?」「测试通过?」),"
            f"并给 decision 的出边标 branch:yes / branch:no"
        )
    if doc_count < COOP_MIN_DOC_NODES:
        problems.append(
            f"doc 节点只有 {doc_count} 个(需 ≥ {COOP_MIN_DOC_NODES})。"
            f"流程有交付产物沉淀(如 PRD、测试报告、上线方案、监控看板、审计日志);"
            f"理想是每个阶段都有产物"
        )
    if dashed_count < COOP_MIN_DASHED_EDGES:
        problems.append(
            f"没有 dashed 边(需 ≥ {COOP_MIN_DASHED_EDGES})。"
            f"异步通知 / 系统推送 / 旁路记录用 style:dashed 表达"
        )

    if problems:
        detail = "".join(f"\n  - {p}" for p in problems)
        raise ValueError(
            f"tob_journey: 多角色 L1 协同语义不足({len(lanes)} 角色 × {len(stages)} 阶段)"
            f"—— 当前 DSL 把它画成了平行流水线而非跨角色协同 UML 流程图:{detail}\n"
            f"请回字段对齐,按各角色 collaboration 的真实上下游补「交接边(跨泳道)+ 判断节点 + "
            f"产物 doc + 异步 dashed」。参考 golden_samples/tob_journey_l1_coop.json 与 "
            f"REGISTRY.md §3.0 协同语义清单。"
        )


def _density_threshold(lanes: list, stages: list) -> int:
    """节点密度下限:角色数 × 子阶段总数 × 0.5(向下取整,至少 1)。

    用户拍板的密度规则(2026-05-28):L1 UML 旅程不允许节点过度稀疏。
    子阶段总数 = sum(len(stage.subStages) for stage),反映真实任务流颗粒度。
    """
    substages_total = sum(len(stage.get("subStages", []) or []) for stage in stages)
    if substages_total == 0:
        substages_total = len(stages)
    threshold = int(len(lanes) * substages_total * 0.5)
    return max(1, threshold)


def _density_threshold_l2(stages: list) -> int:
    """L2 节点密度下限:ceil(子阶段总数 × 1.2),至少 1。"""
    substages_total = sum(len(stage.get("subStages", []) or []) for stage in stages)
    if substages_total == 0:
        substages_total = len(stages)
    return max(1, math.ceil(substages_total * 1.2))


def _assign_tracks_for_cell(
    sorted_nodes: list[dict],
    stage_id: str,
    node_x_ranges: dict[str, tuple[float, float]],
    *,
    stages: list,
    lanes: list,
) -> dict[str, int]:
    """同一 (lane, stage) cell 内横向 interval 重叠时,最少节点下沉第二行。

    L1/L2 共用;与 REGISTRY §3.3「同格错位」一致(按 cell 而非整条 lane 聚合)。
    """
    if not sorted_nodes:
        return {}
    cell_slots = [int(n.get("slot", 0)) for n in sorted_nodes]
    n_slots = max(max(cell_slots) + 1, len(sorted_nodes))
    x_left, x_right = node_x_ranges[stage_id]
    slot_w = (x_right - x_left) / n_slots
    wide_uml = len(stages) == 3 and len(lanes) == 4
    intervals = []
    for n in sorted_nodes:
        slot = int(n.get("slot", 0))
        w, _ = _uml_node_size(
            n["type"],
            n["label"],
            "wide_uml" if wide_uml else "dense",
        )
        x_center = x_left + (slot + 0.5) * slot_w
        preferred = int(n.get("track", n.get("row", 0))) % 2
        intervals.append(
            {
                "id": n["id"],
                "left": x_center - w / 2,
                "right": x_center + w / 2,
                "preferred": preferred,
            }
        )
    intervals.sort(key=lambda item: (item["left"], item["right"], item["id"]))
    conflicts = []
    for i, left_item in enumerate(intervals):
        for j in range(i + 1, len(intervals)):
            right_item = intervals[j]
            if right_item["left"] - left_item["right"] >= TRACK_MIN_GAP:
                break
            conflicts.append((i, j))
    if not conflicts:
        return {item["id"]: 0 for item in intervals}

    n = len(intervals)
    best_mask = None
    best_score = None
    if n <= 18:
        for mask in range(1 << n):
            valid = True
            for i, j in conflicts:
                if ((mask >> i) & 1) == ((mask >> j) & 1):
                    valid = False
                    break
            if not valid:
                continue
            second_row_count = mask.bit_count()
            preferred_penalty = sum(
                1
                for idx, item in enumerate(intervals)
                if ((mask >> idx) & 1) != item["preferred"]
            )
            score = (second_row_count, preferred_penalty)
            if best_score is None or score < best_score:
                best_score = score
                best_mask = mask
    if best_mask is not None:
        return {
            item["id"]: (best_mask >> idx) & 1
            for idx, item in enumerate(intervals)
        }

    row_ends = [-10_000.0, -10_000.0]
    assignment: dict[str, int] = {}
    for item in intervals:
        if item["left"] - row_ends[0] >= TRACK_MIN_GAP:
            row = 0
        elif item["left"] - row_ends[1] >= TRACK_MIN_GAP:
            row = 1
        else:
            row = 0 if row_ends[0] <= row_ends[1] else 1
        assignment[item["id"]] = row
        row_ends[row] = max(row_ends[row], item["right"])
    return assignment


def _render_uml_journey(
    props: dict,
    show_lane_rail: bool = True,
    *,
    density_mode: str = "l1",
    validate_density: bool = True,
) -> str:
    stages = props["stages"]
    lanes = props["lanes"]
    nodes = props["nodes"]
    edges = props["edges"]

    svg_w = 1180
    rail_w = 87 if show_lane_rail else 0
    # Issue 1a 修复(2026-05-28):lane_heights 改为基于 16:9 画布预算的动态计算
    # 画布 1280×720,扣掉 banner(~80) + stage_board(~80) + subtitle(~24) + padding(~40) ≈ 220px
    # SVG 实际可用高度 ≈ 500px。对 N lanes,按 N 均分,封顶 120px 防止 3-4 lane 时过空。
    if len(stages) == 3 and len(lanes) == 4:
        head_h = 48
        lane_heights = [104, 104, 104, 140]
        viewbox = "0 48 1180 452"
    else:
        head_h = 0
        n_lanes = len(lanes)
        canvas_svg_budget = 500  # 16:9 画布扣掉页眉组件后的 SVG 预算
        per_lane = min(120, max(72, canvas_svg_budget // max(1, n_lanes)))
        lane_heights = [per_lane for _ in lanes]
        viewbox = f"0 0 {svg_w} {sum(lane_heights)}"
    svg_h = head_h + sum(lane_heights)
    stage_w = (svg_w - rail_w) / len(stages)

    stage_x_ranges = {}
    node_x_ranges = {}
    edge_pad = 40 if not (len(stages) == 3 and len(lanes) == 4) else 24
    for idx, stage in enumerate(stages):
        x1 = rail_w + idx * stage_w
        x2 = x1 + stage_w
        stage_x_ranges[stage["id"]] = (x1, x2)
        node_x1 = x1 + (edge_pad if idx == 0 else 0)
        node_x2 = x2 - (edge_pad if idx == len(stages) - 1 else 0)
        if node_x2 - node_x1 < stage_w * 0.72:
            node_x1, node_x2 = x1, x2
        node_x_ranges[stage["id"]] = (node_x1, node_x2)

    lane_y_ranges = {}
    y_cursor = head_h
    for idx, lane in enumerate(lanes):
        y1 = y_cursor
        y_cursor += lane_heights[idx]
        lane_y_ranges[lane["id"]] = (y1, y_cursor)

    by_cell: dict[tuple[str, str], list[dict]] = {}
    for node in nodes:
        by_cell.setdefault((node["lane"], node["stage"]), []).append(node)

    # P8 修复(2026-05-25):
    #  1) 未知 lane/stage 不再静默 continue,改为 raise ValueError(fail-loud)
    #  2) slot 改为"按值定位",N = max(slot) + 1 至少 = node 数,
    #     x_center = x_left + (slot + 0.5) * (cell_w / N)
    #     这样 slot:0 与 slot:5 的视觉位置不同(原实现 slot 仅用于排序,位置由 enumerate idx 均分)
    valid_lane_ids = sorted(lane_y_ranges.keys())
    valid_stage_ids = sorted(stage_x_ranges.keys())
    node_track_assignments: dict[str, int] = {}
    for (cell_lane_id, cell_stage_id), raw_cell_nodes in by_cell.items():
        if cell_stage_id not in stage_x_ranges:
            continue
        sorted_nodes = sorted(raw_cell_nodes, key=lambda item: int(item.get("slot", 0)))
        node_track_assignments.update(
            _assign_tracks_for_cell(
                sorted_nodes,
                cell_stage_id,
                node_x_ranges,
                stages=stages,
                lanes=lanes,
            )
        )

    node_positions: dict[str, dict] = {}
    for (lane_id, stage_id), cell_nodes in by_cell.items():
        if lane_id not in lane_y_ranges:
            offending = [n["id"] for n in cell_nodes]
            raise ValueError(
                f"tob_journey: 节点 {offending} 引用了不存在的 lane '{lane_id}',"
                f"合法 lane id: {valid_lane_ids}"
            )
        if stage_id not in stage_x_ranges:
            offending = [n["id"] for n in cell_nodes]
            raise ValueError(
                f"tob_journey: 节点 {offending} 引用了不存在的 stage '{stage_id}',"
                f"合法 stage id: {valid_stage_ids}"
            )
        # 保留按 slot 排序(影响 HTML 文档顺序,跟旧实现一致)
        cell_nodes.sort(key=lambda item: int(item.get("slot", 0)))
        # slot 校验 + 算槽数 N
        cell_slots = [int(n.get("slot", 0)) for n in cell_nodes]
        # 同 cell 内 slot 重复 → 报错(避免两个节点叠在一起)
        if len(cell_slots) != len(set(cell_slots)):
            dup_ids = [n["id"] for n in cell_nodes]
            raise ValueError(
                f"tob_journey: 同一 (lane={lane_id}, stage={stage_id}) cell 内 slot 重复,"
                f"涉及节点 {dup_ids},slot 值 {cell_slots}"
            )
        n_slots = max(max(cell_slots) + 1, len(cell_nodes))
        x_left, x_right = node_x_ranges[stage_id]
        y_top, y_bottom = lane_y_ranges[lane_id]
        lane_h = y_bottom - y_top
        slot_w = (x_right - x_left) / n_slots
        # 按 (lane, stage) cell 判断是否启用双行(与 L1 多角色同一算法)
        use_stagger_tracks = (
            not (len(stages) == 3 and len(lanes) == 4)
            and any(node_track_assignments.get(n["id"], 0) % 2 == 1 for n in cell_nodes)
        )
        for node in cell_nodes:
            slot = int(node.get("slot", 0))
            w, h = _uml_node_size(node["type"], node["label"], "wide_uml" if len(stages) == 3 and len(lanes) == 4 else "dense")
            x_center = x_left + (slot + 0.5) * slot_w
            if use_stagger_tracks:
                track = node_track_assignments.get(node["id"], 0)
                y_center = y_top + lane_h * (
                    STAGGER_ROW_Y_TOP if track % 2 == 0 else STAGGER_ROW_Y_BOTTOM
                )
            else:
                y_center = (y_top + y_bottom) / 2
            node_positions[node["id"]] = {
                "x": x_center - w / 2,
                "y": y_center - h / 2,
                "cx": x_center,
                "cy": y_center,
                "w": w,
                "h": h,
                "type": node["type"],
                "label": node["label"],
                "lane": lane_id,
                "lane_bg": "#f4f7fb" if valid_lane_ids.index(lane_id) % 2 else "#ffffff",
                "stage": stage_id,
            }

    bg_parts = [f'<rect x="0" y="{head_h}" width="{svg_w}" height="{svg_h - head_h}" fill="#fff"/>']
    y_cursor = head_h
    lane_tops = []
    for idx, lane in enumerate(lanes):
        y = y_cursor
        lane_h = lane_heights[idx]
        lane_tops.append(y)
        y_cursor += lane_h
        alt = " alt" if idx % 2 else ""
        if show_lane_rail:
            bg_parts.append(f'<rect class="l1-role-bg" x="0" y="{y}" width="{rail_w}" height="{lane_h}"/>')
        bg_parts.append(f'<rect class="l1-lane-bg{alt}" x="{rail_w}" y="{y}" width="{svg_w - rail_w}" height="{lane_h}"/>')
    for y in lane_tops:
        bg_parts.append(f'<line class="l1-lane-line" x1="0" y1="{y}" x2="{svg_w}" y2="{y}"/>')
    bg_parts.append(f'<line class="l1-lane-line" x1="0" y1="{svg_h}" x2="{svg_w}" y2="{svg_h}"/>')
    if show_lane_rail:
        bg_parts.append(f'<line class="l1-lane-line" x1="{rail_w}" y1="{head_h}" x2="{rail_w}" y2="{svg_h}"/>')
    y_cursor = head_h
    for idx, lane in enumerate(lanes):
        y = y_cursor
        y_cursor += lane_heights[idx]
        if show_lane_rail:
            name_x = 34 if head_h else 36
            tag_x = 57 if head_h else 60
            bg_parts.append(f'<text class="l1-role-text" x="{name_x}" y="{y + 22}">{escape(lane["name"])}</text>')
            if lane.get("tag"):
                bg_parts.append(f'<text class="l1-role-tag" x="{tag_x}" y="{y + 28}">{escape(lane["tag"])}</text>')
    for idx in range(1, len(stages)):
        x = rail_w + idx * stage_w
        bg_parts.append(f'<line class="l1-lane-line" x1="{x:.0f}" y1="{head_h}" x2="{x:.0f}" y2="{svg_h}" stroke-dasharray="3 3"/>')

    # 节点密度门禁(issue 1b 修复,2026-05-28):
    # 结构校验通过后再检查信息密度。L1 用 lanes×substages×0.5;L2 用 ceil(substages×1.2)。
    substages_total = sum(len(stage.get("subStages", []) or []) for stage in stages)
    if substages_total == 0:
        substages_total = len(stages)
    if density_mode == "l2":
        min_nodes = _density_threshold_l2(stages)
        threshold_desc = f"ceil(子阶段总数({substages_total}) × 1.2)"
    else:
        min_nodes = _density_threshold(lanes, stages)
        threshold_desc = f"lanes({len(lanes)}) × substages_total({substages_total}) × 0.5"
    if validate_density and len(nodes) < min_nodes:
        density_hint = (
            "单角色工作流须覆盖各子阶段的具体任务,不能仅放主线节点。"
            if density_mode == "l2"
            else "UML 旅程必须体现各角色在各子阶段的真实任务流,不能仅放主线节点。"
        )
        raise ValueError(
            f"tob_journey: 节点信息密度不足 — 实际 {len(nodes)} 个节点,"
            f"按 {threshold_desc} 至少需要 {min_nodes} 个。"
            f"{density_hint}"
            f"请回到字段对齐补充每个 (lane × stage) cell 的具体任务。"
        )

    # 语义门禁:L1/L2 共用判断分支规则;L1 另查协同语义。
    _workflow_decision_semantics_gate(
        nodes, edges, props.get("focuses"), context="L2" if density_mode == "l2" else "L1"
    )
    if density_mode != "l2":
        _coop_semantics_gate(lanes, stages, nodes, edges)

    # P8 修复(2026-05-25):坏 edge 不再静默 continue;未知 from/to node id 直接 raise
    marker_id = props.get("marker_id") or props.get("_marker_id") or "l1-arrow"
    valid_node_ids = sorted(node_positions.keys())
    edge_parts = []
    branch_label_parts = []
    for edge in edges:
        from_pos = node_positions.get(edge["from"])
        to_pos = node_positions.get(edge["to"])
        if from_pos is None:
            raise ValueError(
                f"tob_journey: edge {{from: '{edge['from']}', to: '{edge['to']}'}} "
                f"引用了不存在的 from node id '{edge['from']}',合法 node ids: {valid_node_ids}"
            )
        if to_pos is None:
            raise ValueError(
                f"tob_journey: edge {{from: '{edge['from']}', to: '{edge['to']}'}} "
                f"引用了不存在的 to node id '{edge['to']}',合法 node ids: {valid_node_ids}"
            )
        d, label_x, label_y = _edge_path(from_pos, to_pos)
        cls = "l1-connector soft" if edge.get("style") == "dashed" else "l1-connector"
        edge_parts.append(f'<path class="{cls}" d="{d}" marker-end="url(#{marker_id})"/>')
        if edge.get("branch") in ("yes", "no"):
            text = "\u662f" if edge["branch"] == "yes" else "\u5426"
            label_x, label_y = _branch_label_near_source(from_pos, to_pos)
            label_bg = from_pos.get("lane_bg", "#ffffff")
            branch_label_parts.append(
                f'<g class="l1-branch-label-pill">'
                f'<rect class="l1-branch-label-bg" x="{label_x - 11:.0f}" y="{label_y - 9:.0f}" width="22" height="18" rx="3" fill="{label_bg}"/>'
                f'<text class="l1-branch-label" x="{label_x:.0f}" y="{label_y:.0f}" '
                f'text-anchor="middle" dominant-baseline="central">{text}</text>'
                f'</g>'
            )

    node_parts = [_render_node(pos) for pos in node_positions.values()]
    note = props.get("note")
    note_html = f'<div class="l1-note">{escape(note)}</div>' if note else ""
    return "".join([
        '<div class="l1-frame">',
        f'<div class="l1-flow-title">{escape(props["banner_title"])}</div>',
        f'<div class="l1-flow-subtitle">{escape(props["banner_subtitle"])}</div>',
        f'<div class="l1-stage-board">{_render_stage_board(stages)}</div>',
        '<div class="l1-uml-wrap">',
        f'<svg class="l1-uml-svg" viewBox="{viewbox}" role="img">',
        f'<defs><marker id="{marker_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8a95a3"/></marker></defs>',
        f'{"".join(bg_parts)}{"".join(edge_parts)}{"".join(node_parts)}{"".join(branch_label_parts)}',
        '</svg></div>',
        f'{note_html}</div>',
    ])

def render_tob_journey_l1(props: dict) -> str:
    return _render_uml_journey(props)


def render_tob_journey_l2(props: dict) -> str:
    if props.get("focuses"):
        return _render_l2_uml_hybrid(props)
    return _render_uml_journey(props, density_mode="l2")
