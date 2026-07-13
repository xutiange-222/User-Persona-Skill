from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.components.registry import render_component
from scripts.components.renderers.tob_journey import _assign_tracks_for_cell, _render_stage_board


GOLDEN_DIR = Path(__file__).parent / "golden_samples"
SAMPLE = json.loads((GOLDEN_DIR / "tob_journey_l1_uml.json").read_text(encoding="utf-8"))


def test_six_stage_header_uses_dynamic_grid_variable():
    stages = [
        {"id": f"s{i}", "name": f"阶段{i}", "subStages": [f"子阶段{i}"]}
        for i in range(6)
    ]
    html = _render_stage_board(stages)
    assert html.count("--l1-grid-columns:") == 2
    assert html.count('class="l1-stage-cell"') == 6


def test_dense_four_node_cell_can_expand_to_three_tracks():
    nodes = [
        {"id": f"n{i}", "type": "step", "slot": i, "label": "训练性能分析任务"}
        for i in range(4)
    ]
    tracks = _assign_tracks_for_cell(
        nodes,
        "s1",
        {"s1": (0.0, 182.0)},
        stages=[{"id": f"s{i}"} for i in range(6)],
        lanes=[{"id": f"l{i}"} for i in range(4)],
    )
    assert max(tracks.values()) + 1 >= 3


def test_sparse_slots_are_compacted_without_changing_order():
    nodes = [
        {"id": "n0", "type": "step", "slot": 0, "label": "开始"},
        {"id": "n1", "type": "step", "slot": 1, "label": "处理"},
        {"id": "n2", "type": "step", "slot": 2, "label": "检查"},
        {"id": "n4", "type": "step", "slot": 4, "label": "完成"},
    ]
    tracks_sparse = _assign_tracks_for_cell(
        nodes,
        "s1",
        {"s1": (0.0, 400.0)},
        stages=[{"id": "s1"}],
        lanes=[{"id": "l1"}],
    )
    compact = copy.deepcopy(nodes)
    compact[-1]["slot"] = 3
    tracks_compact = _assign_tracks_for_cell(
        compact,
        "s1",
        {"s1": (0.0, 400.0)},
        stages=[{"id": "s1"}],
        lanes=[{"id": "l1"}],
    )
    assert tracks_sparse == tracks_compact


def test_duplicate_stage_id_fails_before_coordinate_overwrite():
    bad = copy.deepcopy(SAMPLE)
    bad["props"]["stages"][1]["id"] = bad["props"]["stages"][0]["id"]
    with pytest.raises(ValueError, match=r"stages\[\]\.id 必须唯一"):
        render_component(bad)


def test_l2_css_has_no_fixed_svg_max_height():
    css = (
        Path(__file__).resolve().parents[3]
        / "assets"
        / "templates"
        / "_components.css"
    ).read_text(encoding="utf-8")
    assert "max-height: 170px" not in css
    assert "max-height: 158px" not in css
    assert "height: 100%" in css
