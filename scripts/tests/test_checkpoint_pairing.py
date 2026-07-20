#!/usr/bin/env python3
"""Tests for checkpoint pairing gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_checkpoint_pairing import validate_checkpoint_pairing  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from scripts.components.render_report import _resolve_dirs, render_report  # noqa: E402


class CheckpointPairingTests(unittest.TestCase):
    def test_only_final_report_json_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "05-report.json").write_text("{}", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            codes = {item["code"] for item in errors}
            self.assertIn("CHECKPOINT_MD_MISSING", codes)
            self.assertIn("FINAL_WITHOUT_PREREQ", codes)

    def test_md_without_json_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "00-research-goal.md").write_text("# goal", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "CHECKPOINT_JSON_MISSING" for item in errors))

    def test_processed_extracted_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            processed = proc / "processed"
            extracted = proc / "extracted"
            processed.mkdir()
            extracted.mkdir()
            (processed / "a.txt").write_text("a", encoding="utf-8")
            (processed / "b.txt").write_text("b", encoding="utf-8")
            (extracted / "a.json").write_text("{}", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(
                any(item["code"] == "PROCESSED_EXTRACTED_COUNT_MISMATCH" for item in errors)
            )

    def test_html_without_report_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            proc = run / "过程稿"
            delivery = run / "最终交付件-test"
            proc.mkdir()
            delivery.mkdir()
            (delivery / "report.html").write_text("<html></html>", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "HTML_WITHOUT_REPORT_JSON" for item in errors))

    def test_complete_workflow_always_requires_02_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "01-paradigm.json").write_text(
                json.dumps({"paradigm": "R4"}), encoding="utf-8"
            )
            errors = validate_checkpoint_pairing(proc, require_complete=True)
            self.assertTrue(
                any(item["code"] == "CHECKPOINT_PAIR_MISSING" and item["path"] == "02-classification"
                    for item in errors)
            )

    def test_r2_still_requires_02_pair_in_complete_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "01-paradigm.json").write_text(
                json.dumps({"paradigm": "R2"}), encoding="utf-8"
            )
            errors = validate_checkpoint_pairing(proc, require_complete=True)
            self.assertTrue(any(item.get("path") == "02-classification" for item in errors))

    def test_invalid_json_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "00-research-goal.md").write_text("# 研究目标\n\n用户确认了报告读者和决策用途。", encoding="utf-8")
            (proc / "00-research-goal.json").write_text("{broken", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "CHECKPOINT_JSON_INVALID" for item in errors))

    def test_same_count_wrong_names_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed").mkdir()
            (proc / "extracted").mkdir()
            (proc / "processed" / "a.txt").write_text("a", encoding="utf-8")
            (proc / "extracted" / "b.json").write_text("{}", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "PROCESSED_EXTRACTED_NAME_MISMATCH" for item in errors))

    def test_render_gate_cannot_be_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            input_path = proc / "05-report.json"
            input_path.write_text("{}", encoding="utf-8")
            out_dir = proc / "delivery"
            with self.assertRaises(RuntimeError):
                render_report({}, out_dir, validate=False, input_path=input_path)
            self.assertFalse((out_dir / "report.html").exists())

    def test_direct_render_without_workflow_path_resolves_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            process_dir, project_dir = _resolve_dirs(None, Path(tmp))
            self.assertIsNone(process_dir)
            self.assertIsNone(project_dir)

    def test_complete_mode_rejects_zero_processed_and_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_checkpoint_pairing(Path(tmp), require_complete=True)
            codes = {item["code"] for item in errors}
            self.assertIn("PROCESSED_ARTIFACTS_EMPTY", codes)
            self.assertIn("EXTRACTED_ARTIFACTS_EMPTY", codes)

    def test_nested_group_artifacts_pair_by_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed" / "group-a").mkdir(parents=True)
            (proc / "extracted" / "group-a").mkdir(parents=True)
            (proc / "processed" / "group-a" / "a.txt").write_text("访谈内容", encoding="utf-8")
            (proc / "extracted" / "group-a" / "a.json").write_text(
                json.dumps({"_source_file": "a.txt", "name": "画像"}), encoding="utf-8"
            )
            errors = validate_checkpoint_pairing(proc)
            codes = {item["code"] for item in errors}
            self.assertNotIn("PROCESSED_EXTRACTED_COUNT_MISMATCH", codes)
            self.assertNotIn("PROCESSED_EXTRACTED_NAME_MISMATCH", codes)

    def test_same_filename_in_different_groups_is_not_collapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            for group in ("a", "b"):
                (proc / "processed" / group).mkdir(parents=True)
                (proc / "extracted" / group).mkdir(parents=True)
                (proc / "processed" / group / "same.txt").write_text(group, encoding="utf-8")
                (proc / "extracted" / group / "same.json").write_text(
                    json.dumps({"_source_file": "same.txt", "name": group}), encoding="utf-8"
                )
            errors = validate_checkpoint_pairing(proc)
            self.assertFalse(any(item["code"].endswith("MISMATCH") for item in errors))

    def test_extracted_json_requires_source_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed").mkdir()
            (proc / "extracted").mkdir()
            (proc / "processed" / "a.txt").write_text("a", encoding="utf-8")
            (proc / "extracted" / "a.json").write_text('{"name":"画像"}', encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "EXTRACTED_SOURCE_MISSING" for item in errors))

    def test_minimal_status_only_checkpoint_fails_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "00-research-goal.md").write_text("# 研究目标\n\n用户确认研究目标和决策用途。", encoding="utf-8")
            (proc / "00-research-goal.json").write_text('{"status":"confirmed"}', encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "CHECKPOINT_SCHEMA_INVALID" for item in errors))

    def test_unfilled_md_template_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            template = REPO_ROOT / "templates" / "checkpoints" / "00-research-goal.md"
            (proc / "00-research-goal.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "CHECKPOINT_MD_UNFILLED_TEMPLATE" for item in errors))

    def test_mtime_only_does_not_invalidate_content_bound_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            md = proc / "00-research-goal.md"
            js = proc / "00-research-goal.json"
            md.write_text("# 研究目标\n\n用户后来修改了决策用途和范围。", encoding="utf-8")
            js.write_text('{"status":"confirmed"}', encoding="utf-8")
            os.utime(js, ns=(1_000_000_000, 1_000_000_000))
            os.utime(md, ns=(2_000_000_000, 2_000_000_000))
            errors = validate_checkpoint_pairing(proc)
            self.assertFalse(any(item["code"] in {"CHECKPOINT_JSON_STALE", "CHECKPOINT_DOWNSTREAM_STALE"} for item in errors))

    def test_custom_builder_inside_process_dir_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "build_final_delivery.py").write_text("print('skip gates')", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertTrue(any(item["code"] == "UNAUTHORIZED_PROCESS_BUILDER" for item in errors))

    def test_archived_builder_does_not_reenter_gate_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            archive = proc / "历史版本" / "临时脚本隔离"
            archive.mkdir(parents=True)
            (archive / "old_fix.py").write_text("print('archived')", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            self.assertFalse(any(item["code"] == "UNAUTHORIZED_PROCESS_BUILDER" for item in errors))

    def test_duplicate_interview_content_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed" / "a").mkdir(parents=True)
            (proc / "processed" / "b").mkdir(parents=True)
            (proc / "processed" / "a" / "one.txt").write_text("same interview", encoding="utf-8")
            (proc / "processed" / "b" / "two.txt").write_text("same interview", encoding="utf-8")
            errors = validate_checkpoint_pairing(proc)
            issue = next(item for item in errors if item["code"] == "PROCESSED_CONTENT_DUPLICATE")
            self.assertEqual(issue["file_count"], 2)
            self.assertEqual(issue["unique_content_count"], 1)

    def test_correction_plus_continue_cannot_seal_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "04-personas.md").write_text("# 画像\n\n确认状态：待用户确认\n\n完整画像内容。", encoding="utf-8")
            (proc / "04-personas.json").write_text("{}", encoding="utf-8")
            script = REPO_ROOT / "scripts" / "seal_content_checkpoint.py"
            result = subprocess.run(
                [sys.executable, str(script), "--workdir", str(proc), "--stem", "04-personas", "--user-message", "画像名称改成训练 Infra 工程师，继续"],
                text=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads((proc / "04-personas.json").read_text(encoding="utf-8")), {})

    def test_checkpoint_specific_phrase_can_seal_after_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            draft = {
                "checkpoint": "04-personas", "status": "draft",
                "context_snapshot": {"research_question": "测试研究问题足够完整", "decision_use": "用于验证画像流程是否稳定", "research_type": "toB", "paradigm": "R2"},
                "user_confirmed": False, "persona_count": 1,
                "personas": [{"id": "persona-1", "name": "运维工程师", "description": "负责保障系统稳定运行和故障恢复", "user_count": 1, "members": ["P12345678"], "fields": {"responsibilities": ["监控告警"]}, "field_decisions": [{"field": "responsibilities", "presentation": "full", "reason": "", "information_loss": ""}], "display_components": [{"type": "list", "props": {"title": "工作职责", "items": ["监控告警"]}, "source_fields": ["responsibilities"]}]}],
                "merge_rules": ["单角色不合并"], "evidence_map": {"persona-1": ["P12345678"]}, "risks": ["样本较少"]
            }
            (proc / "04-personas.draft.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
            # A stale sealed JSON may remain after reopening 04.  The current
            # draft must win so newly recorded review data is not discarded.
            (proc / "04-personas.json").write_text("{}", encoding="utf-8")
            from scripts.render_checkpoint_md import render_personas_md
            (proc / "04-personas.md").write_text(render_personas_md(draft), encoding="utf-8")
            script = REPO_ROOT / "scripts" / "seal_content_checkpoint.py"
            result = subprocess.run(
                [sys.executable, str(script), "--workdir", str(proc), "--stem", "04-personas", "--user-message", "确认画像内容"],
                text=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((proc / "04-personas.json").read_text(encoding="utf-8"))
            self.assertTrue(data["user_confirmed"])
            self.assertEqual(data["personas"][0]["name"], "运维工程师")
            self.assertIn("确认状态：已确认", (proc / "04-personas.md").read_text(encoding="utf-8"))

    def test_contradictory_confirmation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "04-journeys.md").write_text("# 旅程\n\n确认状态：待用户确认", encoding="utf-8")
            (proc / "04-journeys.json").write_text("{}", encoding="utf-8")
            script = REPO_ROOT / "scripts" / "seal_content_checkpoint.py"
            result = subprocess.run(
                [sys.executable, str(script), "--workdir", str(proc), "--stem", "04-journeys", "--user-message", "不确认了，你继续吧；确认旅程内容"],
                text=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contradictory", result.stderr)

    def test_sealer_preserves_not_applicable_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "02-classification.md").write_text("# 分类\n\n确认状态：待用户确认\n\nR2 单角色无需分类。", encoding="utf-8")
            (proc / "02-classification.json").write_text(json.dumps({
                "checkpoint": "02-classification", "status": "not_applicable",
                "context_snapshot": {"research_question": "研究单一角色的工作体验与核心问题", "decision_use": "用于产品功能和体验优化决策", "research_type": "toB", "paradigm": "R2"},
                "not_applicable_reason": "R2 单角色无需再次分类", "classification_basis": "",
                "boundary_rules": [], "evidence_summary": [], "uncertainties": [],
                "groups": [], "respondent_mapping": {}, "value_variables": [],
                "user_confirmed": True, "confirmation_message_summary": "等待封存",
                "confirmed_value_sections": ["applicability"]
            }, ensure_ascii=False), encoding="utf-8")
            script = REPO_ROOT / "scripts" / "seal_content_checkpoint.py"
            result = subprocess.run(
                [sys.executable, str(script), "--workdir", str(proc), "--stem", "02-classification", "--user-message", "确认分类内容"],
                text=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((proc / "02-classification.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
