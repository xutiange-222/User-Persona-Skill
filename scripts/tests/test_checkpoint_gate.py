from __future__ import annotations

from pathlib import Path

from scripts.run_checkpoint_gate import run_gate, select_blocking_group


def test_gate_returns_only_one_error_code_family() -> None:
    errors = [
        {"code": "CHECKPOINT_MD_MISSING", "path": "00.md", "message": "a"},
        {"code": "CHECKPOINT_MD_MISSING", "path": "01.md", "message": "b"},
        {"code": "CHECKPOINT_SCHEMA_INVALID", "path": "00.json", "message": "c"},
    ]
    group = select_blocking_group(errors)
    assert {item["code"] for item in group} == {"CHECKPOINT_SCHEMA_INVALID"}


def test_gate_stops_after_same_failure_three_times(tmp_path: Path) -> None:
    (tmp_path / "build_report.py").write_text("print('bypass')", encoding="utf-8")
    first = run_gate(tmp_path, "04-personas")
    second = run_gate(tmp_path, "04-personas")
    third = run_gate(tmp_path, "04-personas")
    assert first["status"] == "recoverable"
    assert second["consecutive_same_failure"] == 2
    assert third["status"] == "stopped_repeated_failure"
    assert third["blocking_error_code"] == "UNAUTHORIZED_PROCESS_BUILDER"


def test_decreasing_error_count_is_progress_not_a_stop(monkeypatch, tmp_path: Path) -> None:
    batches = iter([
        [{"code": "CHECKPOINT_SCHEMA_INVALID", "path": f"04-personas.json:{i}", "message": "x"} for i in range(5)],
        [{"code": "CHECKPOINT_SCHEMA_INVALID", "path": f"04-personas.json:{i}", "message": "x"} for i in range(4)],
        [{"code": "CHECKPOINT_VALUE_ALIGNMENT_INCOMPLETE", "path": f"04-personas.md:{i}", "message": "y"} for i in range(2)],
    ])
    monkeypatch.setattr("scripts.run_checkpoint_gate.validate_checkpoint_pairing", lambda *_args, **_kwargs: next(batches))
    first = run_gate(tmp_path, "04-personas")
    second = run_gate(tmp_path, "04-personas")
    third = run_gate(tmp_path, "04-personas")
    assert first["status"] != "stopped_repeated_failure"
    assert second["consecutive_no_progress"] == 0
    assert third["consecutive_no_progress"] == 0
