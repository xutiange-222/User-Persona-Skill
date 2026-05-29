"""refresh_l2 边推断：避免自环并保留决策回边。"""
from __future__ import annotations

from scripts.tools.refresh_l2_uml_in_reports import _normalize_l2_edges


def test_decision_keeps_yes_forward_and_no_back():
    """双出口决策：保留「是」前向与「否」回边。"""
    nodes = [
        {"id": "n1", "type": "step", "label": "A"},
        {"id": "n2", "type": "decision", "label": "OK?"},
        {"id": "n3", "type": "action", "label": "C"},
        {"id": "n4", "type": "end", "label": "D"},
    ]
    centers = {
        "n1": (100.0, 60.0),
        "n2": (300.0, 60.0),
        "n3": (500.0, 60.0),
        "n4": (700.0, 60.0),
    }
    raw = [{"from": "n2", "to": "n1"}]
    edges = _normalize_l2_edges(nodes, centers, raw, ["是"])
    assert any(e["from"] == "n2" and e["to"] == "n3" for e in edges)
    assert any(e["from"] == "n2" and e["to"] == "n1" for e in edges)


def test_normalize_removes_self_loop_and_keeps_chain():
    nodes = [
        {"id": "n1", "type": "start", "label": "A"},
        {"id": "n2", "type": "step", "label": "B"},
        {"id": "n3", "type": "end", "label": "C"},
    ]
    centers = {"n1": (10.0, 60.0), "n2": (200.0, 60.0), "n3": (400.0, 60.0)}
    raw = [
        {"from": "n1", "to": "n2"},
        {"from": "n2", "to": "n2"},
        {"from": "n2", "to": "n3"},
    ]
    edges = _normalize_l2_edges(nodes, centers, raw, [])
    assert {"from": "n1", "to": "n2"} in edges
    assert {"from": "n2", "to": "n3"} in edges
    assert not any(e["from"] == e["to"] for e in edges)
