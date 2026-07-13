from __future__ import annotations

from pathlib import Path

import scripts.workflow as workflow


def test_single_entrypoint_applies_safe_recovery(monkeypatch, tmp_path: Path) -> None:
    builder = tmp_path / "fix_report.py"
    builder.write_text("print('x')", encoding="utf-8")
    calls = {"count": 0}

    def fake_gate(_process_dir, _target, *, record_attempt=True):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "status": "recoverable", "blocking_error_code": "UNAUTHORIZED_PROCESS_BUILDER",
                "blocking_errors": [{"path": "过程稿/"}], "recovery": {"kind": "automatic"},
            }
        return {"status": "passed"}

    monkeypatch.setattr(workflow, "run_gate", fake_gate)
    result = workflow.check_with_recovery(tmp_path, "04-personas", auto_recover=True)
    assert result["recovery_applied"]["changed"] is True
    assert result["after"]["status"] == "passed"
    assert not builder.exists()
