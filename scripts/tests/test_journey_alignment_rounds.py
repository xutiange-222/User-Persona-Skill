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
    lanes = [{"id": "lane-1", "name": "角色甲"}]
    nodes = [{"id": "n1", "stage": "s1", "lane": "lane-1", "label": "明确目标"}]
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
            {"persona_id": "journey-l1", "component_type": "tob_journey_l1", "props": {"banner_title": "端到端协同", "stages": stages, "lanes": lanes, "nodes": nodes, "edges": []}, "evidence_bindings": []},
            {"persona_id": "persona-1-journey", "component_type": "tob_journey_l2", "props": {"banner_title": "角色甲", "stages": stages, "lanes": lanes, "nodes": nodes, "edges": []}, "evidence_bindings": []},
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
    assert "本稿只展示第 1 轮：全局地图" in md
    assert "### 角色 × 阶段责任矩阵" not in md
    assert "### 关键衔接与分支" not in md


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
    assert saved["alignment_review"]["rounds"][0]["user_message"] == "确认旅程全局，阶段链准确"
    assert len(saved["alignment_review"]["rounds"][0]["content_sha256"]) == 64
    next_md = (process / "04-journeys.md").read_text(encoding="utf-8")
    assert "确认旅程全局，阶段链准确" in next_md
    assert "### 角色 × 阶段责任矩阵" in next_md
    assert "## 旅程总览地图" not in next_md
    assert alignment_review_errors(saved)[0]["path"].endswith("role_responsibility")


def test_all_rounds_persist_and_finish_without_fifth_user_confirmation(tmp_path: Path) -> None:
    process = tmp_path / "过程稿"
    process.mkdir()
    data = _complex_data()
    data["alignment_review"] = expected_alignment_review(data)
    (process / "04-journeys.draft.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    messages = {
        "global_map": "确认旅程全局，阶段关系准确",
        "role_responsibility": "确认角色责任，分工准确",
        "individual_journeys": "确认单角色旅程，局部流程准确",
        "branches_evidence": "确认旅程分支与证据，来源准确",
    }
    result = None
    for round_id, message in messages.items():
        result = record_round(process, round_id, message)
    assert result is not None
    assert result["next_action"] == "seal --stem 04-journeys"
    saved = json.loads((process / "04-journeys.draft.json").read_text(encoding="utf-8"))
    assert [item["user_message"] for item in saved["alignment_review"]["rounds"]] == list(messages.values())
    assert alignment_review_errors(saved) == []
    md = (process / "04-journeys.md").read_text(encoding="utf-8")
    for message in messages.values():
        assert message in md
    assert "无需再次确认旅程正文" in md
    assert "确认旅程内容”" not in md


def test_changing_confirmed_round_content_invalidates_that_round() -> None:
    data = _complex_data()
    data["alignment_review"] = expected_alignment_review(data)
    first = data["alignment_review"]["rounds"][0]
    first["confirmed"] = True
    first["user_message"] = "确认旅程全局，阶段关系准确"
    data["alignment_review"] = expected_alignment_review(data)
    assert data["alignment_review"]["rounds"][0]["confirmed"] is True
    data["journeys"][0]["props"]["stages"][0]["name"] = "新的准备阶段"
    refreshed = expected_alignment_review(data)
    assert refreshed["rounds"][0]["confirmed"] is False


def test_simple_toc_keeps_single_pass() -> None:
    data = _complex_data()
    data["context_snapshot"]["research_type"] = "toC"
    data["journeys"] = []
    assert not needs_guided_rounds(data)
    data["alignment_review"] = expected_alignment_review(data)
    assert alignment_review_errors(data) == []
