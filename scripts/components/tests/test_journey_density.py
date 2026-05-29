"""节点密度门禁守门测试(issue 1b 修复,2026-05-28)。

确保 tob_journey UML 路径强制 nodes >= lanes × substages_total × 0.5,
防止 LLM 偷懒只产稀疏主线节点。
"""
from __future__ import annotations

import copy
import pytest

from scripts.components.registry import render_component


def _make_props(n_lanes: int, n_stages: int, subs_per_stage: int, n_nodes: int) -> dict:
    lanes = [{"id": f"l{i}", "name": f"L{i}", "tag": ""} for i in range(1, n_lanes + 1)]
    stages = [
        {"id": f"s{i}", "name": f"S{i}", "subStages": [f"sub{i}_{j}" for j in range(subs_per_stage)]}
        for i in range(1, n_stages + 1)
    ]
    nodes = []
    used_slots: dict[tuple[str, str], set[int]] = {}
    for i in range(n_nodes):
        lane = lanes[i % n_lanes]["id"]
        stage = stages[i % n_stages]["id"]
        cell = (lane, stage)
        slots = used_slots.setdefault(cell, set())
        slot = 0
        while slot in slots:
            slot += 1
        slots.add(slot)
        nodes.append({
            "id": f"n{i}", "lane": lane, "stage": stage,
            "type": "action", "label": f"任务{i}", "slot": slot,
        })
    # 让 fixture 满足协同语义门禁(2026-05-29 新增),否则 4×3 这类 gated 场景会被
    # 协同门禁拦下,导致密度测试误失败。密度测试关心的是「节点数」,所以这里只补足
    # 协同要素的下限:几个 decision/doc 节点 + 跨泳道(连续 id 自然换泳道)+ 1 条 dashed。
    # 低于密度阈值时密度门禁会先抛,协同门禁根本走不到,不影响 below-threshold 用例。
    # 协同语义仅 L1 多角色需要;L2 密度测试勿造无 branch 的 decision
    if n_lanes >= 3:
        for k, ntype in ((1, "decision"), (2, "decision"), (3, "doc")):
            if k < len(nodes):
                nodes[k]["type"] = ntype
    edges = [{"from": nodes[i]["id"], "to": nodes[i + 1]["id"]} for i in range(len(nodes) - 1)]
    if edges:
        edges[0]["style"] = "dashed"
    return {
        "banner_title": "测试",
        "banner_subtitle": "密度门禁测试",
        "stages": stages,
        "lanes": lanes,
        "nodes": nodes,
        "edges": edges,
    }


def test_density_below_threshold_raises():
    """4 lanes × 9 substages × 0.5 = 18 阈值,17 个节点 → reject"""
    props = _make_props(n_lanes=4, n_stages=3, subs_per_stage=3, n_nodes=17)
    with pytest.raises(ValueError, match=r"信息密度不足"):
        render_component({"type": "tob_journey_l1", "props": props})


def test_density_at_threshold_passes():
    """4 lanes × 9 substages × 0.5 = 18 阈值,18 个节点 → OK"""
    props = _make_props(n_lanes=4, n_stages=3, subs_per_stage=3, n_nodes=18)
    html = render_component({"type": "tob_journey_l1", "props": props})
    assert "</svg>" in html


def test_density_threshold_uses_substages_total():
    """密度阈值用子阶段总数,不是阶段数。
    L2: 1 lane × 12 substages, ceil(12×1.2)=15 阈值;14 个节点 → reject
    """
    props = _make_props(n_lanes=1, n_stages=4, subs_per_stage=3, n_nodes=14)
    with pytest.raises(ValueError, match=r"信息密度不足"):
        render_component({"type": "tob_journey_l2", "props": props})


def test_l2_density_at_threshold_passes():
    """L2: ceil(12×1.2)=15 阈值,15 个节点 → OK"""
    props = _make_props(n_lanes=1, n_stages=4, subs_per_stage=3, n_nodes=15)
    html = render_component({"type": "tob_journey_l2", "props": props})
    assert "</svg>" in html
