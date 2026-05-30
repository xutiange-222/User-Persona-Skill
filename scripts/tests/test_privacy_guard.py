#!/usr/bin/env python3
"""Tests for privacy_guard."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from privacy_guard import (  # noqa: E402
    collect_forbidden_real_names,
    validate_privacy_in_report,
    _is_masked_display_name,
)


class PrivacyGuardTests(unittest.TestCase):
    def test_masked_names(self):
        self.assertTrue(_is_masked_display_name("刘*"))
        self.assertTrue(_is_masked_display_name("黄医生"))
        self.assertTrue(_is_masked_display_name("U1"))
        self.assertFalse(_is_masked_display_name("刘宇"))
        self.assertFalse(_is_masked_display_name("受访者1"))

    def test_leak_in_section_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "processed").mkdir()
            (proc / "processed" / "刘宇.txt").write_text("x", encoding="utf-8")
            (proc / "processed" / "刘军.txt").write_text("y", encoding="utf-8")

            report = {
                "personas": [{
                    "components": [{
                        "type": "section_blocks_grid",
                        "props": {
                            "blocks": [{
                                "title": "使用深度",
                                "summary": "场景常用",
                                "body": "刘宇旅游装修要方案；刘军偏好语音。",
                                "evidence_quotes": [
                                    {"quote": "原话", "source": "刘*"},
                                    {"quote": "原话2", "source": "刘*"},
                                ],
                            }] * 4,
                        },
                    }],
                }],
            }
            issues = validate_privacy_in_report(report, proc)
            codes = {i["code"] for i in issues}
            self.assertIn("P0-PRIVACY-REAL-NAME", codes)

    def test_collect_from_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed").mkdir(parents=True)
            (proc / "processed" / "刘宇.txt").write_text("", encoding="utf-8")
            names = collect_forbidden_real_names(proc)
            self.assertIn("刘宇", names)


if __name__ == "__main__":
    unittest.main()
