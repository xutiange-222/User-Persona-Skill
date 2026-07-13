from __future__ import annotations

import json
from pathlib import Path

from scripts.preflight_render import run_preflight
from scripts.reduced_snapshots import persist_persona_snapshots
from scripts.validate_checkpoint_pairing import PENDING_MD_RE
from scripts.validate_content_completeness import validate_content_completeness


def test_pending_words_in_body_do_not_reopen_confirmed_checkpoint() -> None:
    md = "# 旅程\n\n确认状态：已确认\n\n用户说看不清时，当前内容保持待确认。"
    assert PENDING_MD_RE.search(md) is None
    assert PENDING_MD_RE.search("确认状态：待用户确认\n") is not None


def test_persona_aggregate_snapshot_replaces_many_manual_field_files(tmp_path: Path) -> None:
    data = {
        "personas": [{
            "id": "persona-1", "name": "用户甲", "members": [],
            "fields": {"pain_points": ["发现困难"], "motivation": ["追求品质"]},
            "field_decisions": [
                {"field": "pain_points", "presentation": "full"},
                {"field": "motivation", "presentation": "full"},
            ],
            "display_components": [{"source_fields": ["pain_points", "motivation"]}],
        }]
    }
    persist_persona_snapshots(data, tmp_path)
    (tmp_path / "03-field-alignment.json").write_text(json.dumps({
        "fields_per_persona": {"persona-1": ["pain_points", "motivation"]}
    }), encoding="utf-8")
    (tmp_path / "04-personas.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert validate_content_completeness(tmp_path) == []
    snapshot = json.loads((tmp_path / "reduced" / "persona-1.json").read_text(encoding="utf-8"))
    assert set(snapshot["fields"]) == {"pain_points", "motivation"}


def test_prepare_05_preflight_aggregates_blockers_before_user_confirmation(tmp_path: Path) -> None:
    report = {"metadata": {}, "personas": []}
    result = run_preflight(tmp_path, report)
    assert result["valid"] is False
    assert result["phase"] == "before_05_user_confirmation"
    assert result["blocking_count"] >= 1
    assert isinstance(result["blockers"], list)


def test_prepare_05_preflight_includes_03_semantic_errors(tmp_path: Path) -> None:
    (tmp_path / "03-field-alignment.json").write_text(json.dumps({
        "visual_assets": {
            "assets_asked": True,
            "avatar_use_default": True,
            "scenario_screenshots_enabled": False,
            "scenario_screenshots_deferred": True,
        }
    }), encoding="utf-8")
    result = run_preflight(tmp_path, {"metadata": {}, "personas": []})
    assert any(
        item["code"] == "FIELD_ALIGNMENT_INVALID" and "不能同时" in item["message"]
        for item in result["blockers"]
    )
