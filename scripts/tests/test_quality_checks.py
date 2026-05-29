#!/usr/bin/env python3
"""Minimal no-model regression tests for quality checkers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quality_common import SCRIPT_DIR, SKILL_ROOT

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from path_utils import create_run_dir, resolve_process_dir  # noqa: E402

FIXTURES = SCRIPT_DIR / "fixtures"


# Windows 下子进程默认 stdout 编码跟随系统(GBK),会和测试这边的 UTF-8 解码冲突。
# 给所有 subprocess 注入 PYTHONIOENCODING=utf-8,强制子进程也用 UTF-8 输出中文。
_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def run_json(script: str, *args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=_UTF8_ENV,
    )
    return proc.returncode, json.loads(proc.stdout)


class QualityCheckerTests(unittest.TestCase):
    def test_valid_personas_pass(self):
        code, payload = run_json("check_personas_json.py", "--input", str(FIXTURES / "2b_single_valid" / "04-personas.json"))
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["success"])

    def test_bad_evidence_fails(self):
        code, payload = run_json("check_personas_json.py", "--input", str(FIXTURES / "bad_evidence_contract" / "04-personas.json"))
        self.assertNotEqual(code, 0)
        self.assertFalse(payload["success"])
        self.assertTrue(any(e["code"] == "personas.evidence_count" for e in payload["errors"]))

    def test_valid_html_passes(self):
        code, payload = run_json("check_report_html.py", "--input", str(FIXTURES / "2c_r4_valid" / "report.html"))
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["success"])

    def test_duplicate_journey_fails(self):
        code, payload = run_json("check_report_html.py", "--input", str(FIXTURES / "bad_duplicate_journey" / "report.html"))
        self.assertNotEqual(code, 0)
        self.assertTrue(any(e["code"] == "html.journey_duplicate" for e in payload["errors"]))

    def test_2b_journey_contract_flags_bad_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.html"
            report.write_text(
                """<html data-theme="2b" data-density="high"><body>
                <nav class="persona-nav"><span class="nav-pair">
                  <button class="nav-btn nav-btn-persona" data-target="persona-0">角色</button>
                  <button class="nav-btn nav-btn-journey" data-target="persona-0-journey">› 旅程</button>
                </span></nav>
                <section class="persona-slide layout-2b-journey is-l2" id="persona-0-journey">
                  <div class="tob-rail-cell tob-rail-dim">关注点</div>
                  <span class="tob-flow-pill is-highlight" data-evidence="">建项目</span>
                  <div class="tob-pain-banner">痛点</div>
                </section>
                </body></html>""",
                encoding="utf-8",
            )
            code, payload = run_json("check_report_html.py", "--input", str(report))
            self.assertNotEqual(code, 0)
            codes = {e["code"] for e in payload["errors"]}
            self.assertIn("html.2b_journey_highlight", codes)
            self.assertIn("html.2b_journey_pain_row", codes)
            self.assertIn("html.2b_journey_focus_pain_label", codes)
            self.assertIn("html.2b_journey_flow_evidence", codes)

    def test_path_utils_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_run_dir(Path(tmp), "A/B 测试:画像")
            self.assertTrue((run_dir / "过程稿").exists())
            self.assertTrue((run_dir / "画像头像素材").exists())
            self.assertTrue((run_dir / "界面截图").exists())
            self.assertEqual(resolve_process_dir(run_dir), run_dir / "过程稿")
            self.assertEqual(resolve_process_dir(run_dir / "过程稿"), run_dir / "过程稿")

    def test_render_report_entry_exists(self):
        path = SKILL_ROOT / "scripts" / "components" / "render_report.py"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("_base.html", text)
        self.assertNotIn("render_html", text)

    def test_recovery_check_final_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_run_dir(Path(tmp), "恢复测试")
            process_dir = run_dir / "过程稿"
            (process_dir / "00-research-goal.json").write_text('{"research_type":"toC"}', encoding="utf-8")
            delivery = run_dir / "最终交付件-2C-恢复测试-1用户-单画像"
            delivery.mkdir()
            (delivery / "report.html").write_text("<html></html>", encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "recovery_check.py"),
                    "--workdir",
                    str(run_dir),
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=_UTF8_ENV,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or "")
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "completed")
            self.assertIn("delivery_report", payload)

    def test_cluster_personas_bad_r4_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_run_dir(Path(tmp), "聚类测试")
            process_dir = run_dir / "过程稿"
            bad = {
                "paradigm": "R4",
                "value_variables": [{"key": "x", "name": "X", "levels": [{"name": "左"}, {"name": "右"}]}],
                "respondent_mapping": {}
            }
            (process_dir / "02-classification.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "cluster_personas.py"),
                    "--workdir",
                    str(run_dir),
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=_UTF8_ENV,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("错误", proc.stdout)


if __name__ == "__main__":
    unittest.main()
