"""L2 单泳道 UML 与 L1 多泳道共用 track 错行规则。"""
from __future__ import annotations

import re

from unittest.mock import patch

from scripts.components.renderers import tob_journey
from scripts.components.renderers.tob_journey import (
    _assign_tracks_for_cell,
    _render_uml_journey,
)


def _all_node_top_ys(html: str) -> list[float]:
    return [
        float(m.group(1))
        for m in re.finditer(
            r'<g class="l1-node l1-\w+" transform="translate\([\d.]+ ([\d.]+)\)"',
            html,
        )
    ]


def test_l2_cell_track_matches_l1_same_cell():
    """L2 与 L1 在同一 (lane,stage) cell 上应得到相同 track 分配。"""
    nodes = [
        {"id": "n1", "type": "step", "slot": 0, "label": "协调发布"},
        {"id": "n2", "type": "doc", "slot": 1, "label": "发布清单"},
        {"id": "n3", "type": "action", "slot": 2, "label": "生产上线"},
        {"id": "n4", "type": "end", "slot": 3, "label": "交付完成"},
    ]
    stages = [
        {"id": "s1", "name": "1", "subStages": ["a"]},
        {"id": "s2", "name": "2", "subStages": ["b"]},
        {"id": "s3", "name": "3", "subStages": ["c"]},
        {"id": "s4", "name": "4", "subStages": ["c1", "c2", "c3", "c4"]},
    ]
    lanes_l1 = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
    lanes_l2 = [{"id": "solo", "name": "SM"}]
    node_x_ranges = {"s4": (885.0, 1140.0)}
    sorted_nodes = sorted(nodes, key=lambda n: int(n["slot"]))
    l1_tracks = _assign_tracks_for_cell(
        sorted_nodes, "s4", node_x_ranges, stages=stages, lanes=lanes_l1
    )
    l2_tracks = _assign_tracks_for_cell(
        sorted_nodes, "s4", node_x_ranges, stages=stages, lanes=lanes_l2
    )
    assert l1_tracks == l2_tracks
    assert any(t % 2 == 1 for t in l2_tracks.values())


def test_single_lane_overlapping_nodes_stagger_to_two_rows():
    """同阶段多节点 slot 密集时,单泳道 L2 也应上下错行(与 L1 多泳道一致)。"""
    props = {
        "banner_title": "发布阶段密集节点",
        "banner_subtitle": "单泳道错行回归",
        "stages": [
            {"id": "s1", "name": "准入", "subStages": ["a"]},
            {"id": "s2", "name": "宣讲", "subStages": ["b"]},
            {"id": "s3", "name": "迭代", "subStages": ["c"]},
            {"id": "s4", "name": "发布", "subStages": ["c1", "c2", "c3", "c4"]},
        ],
        "lanes": [{"id": "role", "name": "SM", "tag": ""}],
        "nodes": [
            {"id": "n4", "lane": "role", "stage": "s4", "type": "step", "slot": 0, "label": "协调发布"},
            {"id": "n5", "lane": "role", "stage": "s4", "type": "doc", "slot": 1, "label": "发布清单"},
            {"id": "n6", "lane": "role", "stage": "s4", "type": "action", "slot": 2, "label": "生产上线"},
            {"id": "n7", "lane": "role", "stage": "s4", "type": "end", "slot": 3, "label": "交付完成"},
        ],
        "edges": [
            {"from": "n4", "to": "n5"},
            {"from": "n5", "to": "n6"},
            {"from": "n6", "to": "n7"},
        ],
    }
    with patch.object(tob_journey, "_density_threshold_l2", return_value=1):
        html = _render_uml_journey(props, show_lane_rail=False, density_mode="l2")
    ys = _all_node_top_ys(html)
    assert len(ys) == 4
    assert max(ys) - min(ys) > 20, f"发布阶段节点应分两行,实际 y={ys}"
