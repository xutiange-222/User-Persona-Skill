from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.journey_alignment import (
    alignment_review_errors,
    expected_alignment_review,
    needs_guided_rounds,
    record_round,
)
from scripts.render_checkpoint_md import render_journeys_md


def _complex_data() -> dict:
    stages = [
        {"id": "s1", "name": "准备", "subStages": ["明确目标"]},
        {"id": "s2", "name": "执行", "subStages": ["完成任务"]},
    ]
    return {
        "checkpoint": "04-journeys",
        "status": "draft",
        "context_snapshot": {
            "research_question": "理解复杂协同旅程中的问题",
            "decision_use": "用于确定产品改进优先级",
            "research_type": "toD",
            "paradigm": "R5",
        },
        "scope": "overall-and-per-persona",
        "journeys": [
            {"persona_id": "journey-l1", "component_type": "tob_journey_l1", "props": {"banner_title": "端到端协同", "stages": stages, "lanes": [], "nodes": [], "edges": []}, "evidence_bindings": []},
            {"persona_id": "persona-1-journey", "component_type": "tob_journey_l2", "props": {"banner_title": "角色甲", "stages": stages, "lanes": [], "nodes": [], "edges": []}, "evidence_bindings": []},
        ],
        "quality_review": {"evidence_gaps": []},
    }


def test_complex_tod_uses_four_rounds_and_location_map() -> None:
    data = _complex_data()
    assert needs_guided_rounds(data)
    data["alignment_review"] = expected_alignment_review(data)
    md = render_journeys_md(data)
    assert "## 旅程总览地图" in md
    assert "## 分轮确认进度" in md
    assert "### 你现在在这里" in md
    assert "当前只核对：全局地图" in md


def test_rounds_are_resumable_and_ordered(tmp_path: Path) -> None:
    process = tmp_path / "过程稿"
    process.mkdir()
    data = _complex_data()
    data["alignment_review"] = expected_alignment_review(data)
    (process / "04-journeys.draft.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (process / "04-journeys.md").write_text(render_journeys_md(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="必须按顺序确认"):
        record_round(process, "role_responsibility", "确认角色责任")
    result = record_round(process, "global_map", "确认旅程全局，阶段链准确")
    assert result["next_round"] == "role_responsibility"
    saved = json.loads((process / "04-journeys.draft.json").read_text(encoding="utf-8"))
    assert saved["alignment_review"]["rounds"][0]["confirmed"] is True
    assert alignment_review_errors(saved)[0]["path"].endswith("role_responsibility")


def test_simple_toc_keeps_single_pass() -> None:
    data = _complex_data()
    data["context_snapshot"]["research_type"] = "toC"
    data["journeys"] = []
    assert not needs_guided_rounds(data)
    data["alignment_review"] = expected_alignment_review(data)
    assert alignment_review_errors(data) == []
