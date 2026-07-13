from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.render_report_checkpoint_md import render_report_checkpoint_md


ROOT = Path(__file__).resolve().parents[2]


def _report() -> dict:
    pages = [{"id": "matrix", "name": "画像矩阵", "layout": "layout-matrix-2d", "components": []}]
    for number, name in enumerate(("内行派", "朦胧派", "价敏派"), 1):
        pages.extend([
            {"id": f"persona-{number}", "name": name, "layout": "layout-2c-portrait", "components": []},
            {"id": f"persona-{number}-detail", "name": name, "layout": "layout-2c-detail", "components": []},
            {"id": f"persona-{number}-journey", "name": name, "layout": "layout-2c-journey", "components": []},
        ])
    return {
        "metadata": {
            "page_count": 10, "persona_count": 3,
            "context_snapshot": {"paradigm": "R4"},
            "field_coverage": [
                {"persona_id": f"persona-{i}", "included_fields": ["pain_points"], "omitted_fields": []}
                for i in range(1, 4)
            ],
        },
        "personas": pages,
    }


def _write_upstream(process: Path) -> None:
    (process / "03-field-alignment.json").write_text(json.dumps({
        "visual_spec": {"template_id": "2c-persona", "palette_id": "2c-yellow-orange"}
    }), encoding="utf-8")
    (process / "04-personas.json").write_text(json.dumps({
        "personas": [{"id": f"persona-{i}"} for i in range(1, 4)]
    }), encoding="utf-8")
    (process / "04-journeys.json").write_text(json.dumps({
        "journeys": [{"persona_id": f"persona-{i}-journey"} for i in range(1, 4)]
    }), encoding="utf-8")


def test_05_md_only_asks_for_page_plan_delta(tmp_path: Path) -> None:
    _write_upstream(tmp_path)
    md = render_report_checkpoint_md(tmp_path, _report())
    assert "上游确认可直接形成：**7 页**" in md
    assert "当前建议最终形成：**10 页**" in md
    assert "新增：**3 页**" in md
    assert "没有字段被删除" in md
    assert "## 本次新增决定" in md
    assert "## 最终页面清单" in md
    assert "请确认色板" not in md
    assert "是否生成旅程" not in md


def test_05_seal_rejects_md_from_stale_draft(tmp_path: Path) -> None:
    _write_upstream(tmp_path)
    report = _report()
    draft = tmp_path / "05-report.draft.json"
    draft.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "05-report.md").write_text(render_report_checkpoint_md(tmp_path, report), encoding="utf-8")
    report["metadata"]["page_count"] = 9
    draft.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seal_content_checkpoint.py"), "--workdir", str(tmp_path), "--stem", "05-report", "--user-message", "确认报告结构"],
        text=True, capture_output=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode != 0
    assert "not generated from the current" in result.stderr
    assert not (tmp_path / "05-report.json").exists()
