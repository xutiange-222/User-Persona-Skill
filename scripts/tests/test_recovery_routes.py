from __future__ import annotations

import json
from pathlib import Path

import scripts.run_checkpoint_gate as gate_module
from scripts.checkpoint_hash import md_sha256_file
from scripts.recovery_policy import recovery_for
from scripts.repair_workflow import archive_downstream, create_recovery_bundle, quarantine_builders, refresh_04_md, reopen_04_for_edit


def test_every_common_block_has_a_recovery_route(tmp_path: Path) -> None:
    automatic = recovery_for({"code": "HUMAN_MD_MACHINE_ID_VISIBLE", "path": "04-journeys.md"}, tmp_path)
    confirmation = recovery_for({"code": "CHECKPOINT_CONFIRMATION_CONTRADICTORY", "path": "04-journeys.json"}, tmp_path)
    runtime = recovery_for({"code": "VALIDATOR_RUNTIME_ERROR", "path": "validate_x"}, tmp_path)
    title = recovery_for({"code": "LANGUAGE_TITLE_TRUNCATED", "path": "04-personas.json:x.title"}, tmp_path)
    duplicate_stage = recovery_for({"code": "P8-JOURNEY-DUPLICATE-ID", "path": "04-journeys.json"}, tmp_path)
    assert automatic["kind"] == "automatic" and automatic["command"]
    assert confirmation["kind"] == "user_review" and confirmation["fallback_command"]
    assert runtime["kind"] == "skill_defect" and runtime["fallback_command"]
    assert title["kind"] == "official_rollback" and "reopen-04" in title["command"]
    assert duplicate_stage["kind"] == "official_rollback" and "04-journeys" in duplicate_stage["command"]


def test_gate_ignores_future_checkpoint_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate_module, "validate_checkpoint_pairing", lambda *_args, **_kwargs: [
        {"code": "CHECKPOINT_SCHEMA_INVALID", "path": "04-personas.json", "message": "current"},
        {"code": "CHECKPOINT_SCHEMA_INVALID", "path": "05-report.json", "message": "future"},
    ])
    result = gate_module.run_gate(tmp_path, "04-personas", record_attempt=False)
    assert result["target_error_count"] == 1
    assert result["blocking_errors"][0]["path"] == "04-personas.json"


def test_quarantine_builder_preserves_file(tmp_path: Path) -> None:
    script = tmp_path / "fix_report.py"
    script.write_text("print('x')", encoding="utf-8")
    result = quarantine_builders(tmp_path)
    assert result["changed"] is True
    assert not script.exists()
    assert (Path(result["archive"]) / script.name).read_text(encoding="utf-8") == "print('x')"


def test_archive_downstream_is_non_destructive(tmp_path: Path) -> None:
    (tmp_path / "04-journeys.md").write_text("journey", encoding="utf-8")
    (tmp_path / "05-report.json").write_text("{}", encoding="utf-8")
    result = archive_downstream(tmp_path, "04-journeys")
    archive = Path(result["archive"])
    assert (archive / "04-journeys.md").read_text(encoding="utf-8") == "journey"
    assert (archive / "05-report.json").read_text(encoding="utf-8") == "{}"


def test_reopen_04_archives_confirmed_pair_and_creates_editable_draft(tmp_path: Path) -> None:
    data = {
        "status": "confirmed",
        "user_confirmed": True,
        "confirmation_message_summary": "confirmed",
        "confirmation_user_message": "ok",
        "confirmed_value_sections": ["personas"],
        "alignment_md_sha256": "0" * 64,
        "context_snapshot": {},
        "personas": [
            {
                "name": "开发者",
                "description": "负责模型开发与验证",
                "user_count": 1,
                "fields": {"responsibilities": ["开发模型"]},
                "field_decisions": [],
            }
        ],
    }
    (tmp_path / "04-personas.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "04-personas.md").write_text("old", encoding="utf-8")
    (tmp_path / "05-report.json").write_text("{}", encoding="utf-8")

    result = reopen_04_for_edit(tmp_path, "04-personas")

    draft = json.loads((tmp_path / "04-personas.draft.json").read_text(encoding="utf-8"))
    archive = Path(result["archive"])
    assert draft["status"] == "draft" and draft["user_confirmed"] is False
    assert "alignment_md_sha256" not in draft
    assert (tmp_path / "04-personas.md").is_file()
    assert (archive / "04-personas.json").is_file()
    assert (archive / "05-report.json").is_file()
    assert result["requires_user_confirmation"] is True


def test_refresh_confirmed_04_md_rebinds_hash(tmp_path: Path) -> None:
    data = {
        "status": "confirmed", "user_confirmed": True, "context_snapshot": {},
        "personas": [{"name": "开发者", "description": "负责模型开发", "user_count": 1, "fields": {"responsibilities": ["开发模型"]}, "field_decisions": []}],
    }
    path = tmp_path / "04-personas.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    result = refresh_04_md(tmp_path, "04-personas")
    updated = json.loads(path.read_text(encoding="utf-8"))
    md = tmp_path / "04-personas.md"
    assert result["hash_rebound"] is True
    assert updated["alignment_md_sha256"] == md_sha256_file(md)


def test_recovery_bundle_keeps_only_hash_consistent_pairs(tmp_path: Path) -> None:
    process_dir = tmp_path / "过程稿"
    process_dir.mkdir()
    md = process_dir / "00-research-goal.md"
    md.write_text("# 研究目标\n\n已确认研究范围。\n", encoding="utf-8", newline="\n")
    data = {"alignment_md_sha256": md_sha256_file(md)}
    (process_dir / "00-research-goal.json").write_text(json.dumps(data), encoding="utf-8")
    bad_md = process_dir / "01-paradigm.md"
    bad_md.write_text("# 方式\n", encoding="utf-8")
    (process_dir / "01-paradigm.json").write_text(json.dumps({"alignment_md_sha256": "0" * 64}), encoding="utf-8")
    result = create_recovery_bundle(process_dir)
    bundle = Path(result["created"])
    assert (bundle / "00-research-goal.md").is_file()
    assert not (bundle / "01-paradigm.md").exists()
    assert any("01-paradigm" in item for item in result["unresolved"])
