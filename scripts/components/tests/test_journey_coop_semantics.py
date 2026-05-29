"""协同语义门禁守门测试(2026-05-29)。

确保多角色全景 L1(lanes>=3 且 stages>=3)不能退化成「N 条互不相干的纵向流水线」:
必须有跨泳道交接边 + 判断节点 + 产物 doc + 异步 dashed。

- 退化 fixture(全 step / 单泳道边 / 0 decision/doc)→ 必须 reject。
- 真值 golden(电力调度员)→ 必须 pass,且各协同要素 >= 门禁阈值(回归基线)。
- 小流程 / 单泳道(< 3 lane 或 < 3 stage)→ 豁免,不误伤。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from components.registry import render_component
from components.renderers.tob_journey import (
    COOP_MIN_DECISION_NODES,
    COOP_MIN_DOC_NODES,
    COOP_MIN_DASHED_EDGES,
    COOP_MIN_CROSS_LANE_EDGE_RATIO,
)

GOLDEN_DIR = Path(__file__).parent / "golden_samples"
TRUTH = json.loads((GOLDEN_DIR / "tob_journey_l1_coop.json").read_text(encoding="utf-8"))


def _degenerate_props(n_lanes: int, n_stages: int, n_nodes: int) -> dict:
    """造一份「N 条平行流水线」退化 props:全 step、边只在同泳道内、0 decision/doc/dashed。

    节点数刻意拉到 >= 密度门禁阈值,好让流程走到协同门禁而不是先被密度门禁拦下。
    """
    lanes = [{"id": f"l{i}", "name": f"L{i}", "tag": ""} for i in range(1, n_lanes + 1)]
    stages = [
        {"id": f"s{i}", "name": f"S{i}", "subStages": [f"a{i}", f"b{i}", f"c{i}"]}
        for i in range(1, n_stages + 1)
    ]
    cells = [(lane, stage) for lane in lanes for stage in stages]
    nodes = []
    edges = []
    lane_prev: dict[str, str] = {}
    n = 1
    idx = 0
    while len(nodes) < n_nodes:
        lane, stage = cells[idx % len(cells)]
        slot = (idx // len(cells))  # 同 cell 第二轮用 slot 1,避免 slot 重复
        nid = f"n{n}"
        n += 1
        idx += 1
        nodes.append({
            "id": nid, "lane": lane["id"], "stage": stage["id"],
            "type": "step", "label": f"任务{n}", "slot": slot,
        })
        prev = lane_prev.get(lane["id"])
        if prev:
            edges.append({"from": prev, "to": nid})  # 同泳道内的边,跨泳道占比 = 0
        lane_prev[lane["id"]] = nid
    return {
        "banner_title": "退化测试",
        "banner_subtitle": "平行流水线,无协同",
        "stages": stages,
        "lanes": lanes,
        "nodes": nodes,
        "edges": edges,
    }


def test_degenerate_parallel_pipelines_rejected():
    """5×5 全 step / 单泳道边 / 0 decision-doc-dashed → 协同语义门禁 reject。"""
    props = _degenerate_props(n_lanes=5, n_stages=5, n_nodes=38)
    with pytest.raises(ValueError, match=r"协同语义不足"):
        render_component({"type": "tob_journey_l1", "props": props})


def test_truth_golden_passes():
    """真值(电力调度员)L1 必须正常渲染(不被门禁误杀)。"""
    html = render_component(TRUTH)
    assert "</svg>" in html


def test_truth_golden_meets_thresholds():
    """把真值各协同要素 >= 门禁阈值钉成回归基线。"""
    props = TRUTH["props"]
    nodes, edges = props["nodes"], props["edges"]
    node_lane = {x["id"]: x["lane"] for x in nodes}
    decision = sum(1 for x in nodes if x["type"] == "decision")
    doc = sum(1 for x in nodes if x["type"] == "doc")
    dashed = sum(1 for e in edges if e.get("style") == "dashed")
    cross = sum(1 for e in edges if node_lane.get(e["from"]) != node_lane.get(e["to"]))
    ratio = cross / len(edges)
    assert decision >= COOP_MIN_DECISION_NODES
    assert doc >= COOP_MIN_DOC_NODES
    assert dashed >= COOP_MIN_DASHED_EDGES
    assert ratio >= COOP_MIN_CROSS_LANE_EDGE_RATIO
    # 真值还应有 branch 标(写进 REGISTRY 清单,门禁不硬卡,但基线要保住)
    assert any(e.get("branch") in ("yes", "no") for e in edges)


def test_two_lane_journey_exempt():
    """单/双泳道(< 3 lane)即便退化也豁免,不误伤 L2 类小流程。"""
    props = _degenerate_props(n_lanes=2, n_stages=5, n_nodes=16)
    html = render_component({"type": "tob_journey_l1", "props": props})
    assert "</svg>" in html


def test_three_stage_too_few_stages_still_gated():
    """lanes>=3 且 stages>=3 才进门禁;这里 3×3 退化也应被 reject(确认 stage 边界)。"""
    props = _degenerate_props(n_lanes=3, n_stages=3, n_nodes=14)
    with pytest.raises(ValueError, match=r"协同语义不足"):
        render_component({"type": "tob_journey_l1", "props": props})
