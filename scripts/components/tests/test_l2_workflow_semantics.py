"""L2/L1 共用工作流判断语义回归。"""
from __future__ import annotations

import copy

import pytest

from scripts.components.registry import render_component


def _load_golden_props() -> dict:
    import json
    from pathlib import Path

    path = Path(__file__).parent / "golden_samples" / "tob_journey_l2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["props"]


def test_l2_golden_sample_passes_semantics_gate():
    props = _load_golden_props()
    html = render_component({"type": "tob_journey_l2", "props": props})
    assert "l1-uml-svg" in html or "tob-l2-uml-hybrid" in html


def test_l2_rejects_pain_as_decision_label():
    props = _load_golden_props()
    props = copy.deepcopy(props)
    props["focuses"] = [
        {"title": "算力耗时", "body": "演算要一小时以上", "is_pain": True},
    ]
    for node in props["nodes"]:
        if node.get("type") == "decision":
            node["label"] = "算力耗时"
            break
    with pytest.raises(ValueError, match=r"工作流判断语义不足"):
        render_component({"type": "tob_journey_l2", "props": props})


def test_l2_accepts_yes_only_decision_without_no_branch():
    """无独立补救任务时,只保留「是」主线,不要求「否」分支。"""
    props = _load_golden_props()
    props = copy.deepcopy(props)
    props["edges"] = [e for e in props["edges"] if e.get("branch") != "no"]
    html = render_component({"type": "tob_journey_l2", "props": props})
    assert "l1-uml-svg" in html or "tob-l2-uml-hybrid" in html


def test_l2_strips_invalid_no_branch_back_to_mainline():
    """否回指主线前序节点时,渲染前自动剔除。"""
    from scripts.components.renderers.tob_journey import _sanitize_invalid_no_branches

    props = _load_golden_props()
    props = copy.deepcopy(props)
    props["edges"].append({"from": "n9", "to": "n8", "branch": "no"})
    removed = _sanitize_invalid_no_branches(props["edges"])
    assert removed == 1
    assert not any(e.get("from") == "n9" and e.get("to") == "n8" for e in props["edges"])
    render_component({"type": "tob_journey_l2", "props": props})


def test_l2_keeps_valid_no_branch_to_remediation_node():
    props = _load_golden_props()
    html = render_component({"type": "tob_journey_l2", "props": props})
    assert "补充立项" in html
    assert "l1-branch-label" in html
