#!/usr/bin/env python3
"""Tests for recovery_check checkpoint audit."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from recovery_check import audit_missing_artifacts, check_recovery  # noqa: E402


class RecoveryCheckTests(unittest.TestCase):
    def test_fresh_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = check_recovery(Path(tmp))
            self.assertEqual(status["status"], "fresh")
            self.assertIn("00-research-goal.json", [m["path"] for m in status["missing_artifacts"]])

    def test_missing_05_when_only_04(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "04-personas.json").write_text("{}", encoding="utf-8")
            missing = audit_missing_artifacts(proc, "R2")
            paths = [m["path"] for m in missing]
            self.assertIn("05-report.json", paths)

    def test_r4_needs_02(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "01-paradigm.json").write_text(
                json.dumps({"paradigm": "R4"}), encoding="utf-8"
            )
            missing = audit_missing_artifacts(proc, "R4")
            self.assertIn("02-classification.json", [m["path"] for m in missing])

    def test_r2_requires_02_not_applicable_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = audit_missing_artifacts(Path(tmp), "R2")
            self.assertIn("02-classification.json", [m["path"] for m in missing])

    def test_checkpoint_pairing_errors_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "05-report.json").write_text("{}", encoding="utf-8")
            status = check_recovery(proc)
            self.assertFalse(status["checkpoint_pairing_valid"])
            codes = [item["code"] for item in status["checkpoint_pairing_errors"]]
            self.assertIn("CHECKPOINT_PAIR_MISSING", codes)
            self.assertIn("FINAL_WITHOUT_PREREQ", codes)

    def test_human_format_shows_pairing_errors(self):
        from recovery_check import format_status_for_user

        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "05-report.json").write_text("{}", encoding="utf-8")
            status = check_recovery(proc)
            text = format_status_for_user(status)
            self.assertIn("检查点配对未通过", text)
            self.assertIn("CHECKPOINT_SCHEMA_INVALID", text)
            self.assertNotIn("  - CHECKPOINT_MD_MISSING", text)

    def test_extra_extracted_file_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed").mkdir()
            (proc / "extracted").mkdir()
            (proc / "processed" / "a.txt").write_text("a", encoding="utf-8")
            (proc / "extracted" / "a.json").write_text("{}", encoding="utf-8")
            (proc / "extracted" / "orphan.json").write_text("{}", encoding="utf-8")
            status = check_recovery(proc)
            self.assertNotIn("extracted", status["completed_steps"])
            codes = {item["code"] for item in status["checkpoint_pairing_errors"]}
            self.assertIn("PROCESSED_EXTRACTED_COUNT_MISMATCH", codes)

    def test_nested_group_counts_are_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed" / "role").mkdir(parents=True)
            (proc / "extracted" / "role").mkdir(parents=True)
            (proc / "processed" / "role" / "a.txt").write_text("a", encoding="utf-8")
            (proc / "extracted" / "role" / "a.json").write_text(
                json.dumps({"_source_file": "a.txt", "name": "画像"}), encoding="utf-8"
            )
            status = check_recovery(proc)
            self.assertEqual(status["processed_count"], 1)
            self.assertEqual(status["extracted_count"], 1)

    def test_invalid_checkpoint_is_not_marked_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "00-research-goal.md").write_text("# 研究目标\n\n已有内容但系统稿无效。", encoding="utf-8")
            (proc / "00-research-goal.json").write_text('{"status":"confirmed"}', encoding="utf-8")
            status = check_recovery(proc)
            self.assertNotIn("research_goal", status["completed_steps"])
            self.assertEqual(status["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
