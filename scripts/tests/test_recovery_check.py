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

    def test_r2_skips_02_in_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = audit_missing_artifacts(Path(tmp), "R2")
            self.assertNotIn("02-classification.json", [m["path"] for m in missing])


if __name__ == "__main__":
    unittest.main()
