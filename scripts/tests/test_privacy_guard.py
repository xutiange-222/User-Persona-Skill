#!/usr/bin/env python3
"""Tests for privacy_guard."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from privacy_guard import (  # noqa: E402
    collect_forbidden_real_names,
    validate_privacy_in_html,
    validate_privacy_in_markdown,
    validate_privacy_in_report,
    _is_masked_display_name,
)
from repair_workflow import refresh_04_md  # noqa: E402


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

    def test_collect_from_nested_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed" / "运维组").mkdir(parents=True)
            (proc / "processed" / "运维组" / "张伟.txt").write_text("", encoding="utf-8")
            names = collect_forbidden_real_names(proc)
            self.assertIn("张伟", names)

    def test_collect_name_from_descriptive_filename_and_self_introduction(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            nested = proc / "processed" / "开发组"
            nested.mkdir(parents=True)
            (nested / "N01_张伟_语篇规整稿.txt").write_text("主持人：请介绍一下。受访者：我是张伟。", encoding="utf-8")
            names = collect_forbidden_real_names(proc)
            self.assertIn("张伟", names)

    def test_role_phrase_after_wo_shi_is_not_mistaken_for_a_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed").mkdir(parents=True)
            (proc / "processed" / "N01.txt").write_text("我是马达控制工程师，负责算法开发。", encoding="utf-8")
            self.assertNotIn("马达控制", collect_forbidden_real_names(proc))

    def test_persona_name_is_not_mistaken_for_real_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            (proc / "04-personas.json").write_text(
                json.dumps({"personas": [{"name": "内行场景派"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertNotIn("内行场景派", collect_forbidden_real_names(proc))

    def test_direct_identifiers_are_blocked(self):
        report = {
            "personas": [{
                "components": [{
                    "type": "generic_text",
                    "props": {"body": "联系邮箱 user@example.com，手机号 13800138000"},
                }],
            }],
        }
        codes = {item["code"] for item in validate_privacy_in_report(report, None)}
        self.assertIn("P0-PRIVACY-EMAIL", codes)
        self.assertIn("P0-PRIVACY-PHONE", codes)

    def test_non_anonymous_evidence_source_is_blocked_without_name_dictionary(self):
        report = {
            "personas": [{
                "fields": {
                    "pain_points": [{
                        "title": "排查困难",
                        "mention_count": 1,
                        "mentioned_by": ["张伟"],
                        "evidence_quotes": ['[来源:张伟]: "排查问题需要反复切换工具"'],
                    }],
                },
            }],
        }
        codes = {item["code"] for item in validate_privacy_in_report(report, None)}
        self.assertIn("P0-PRIVACY-EVIDENCE-SOURCE", codes)

    def test_markdown_real_name_and_source_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed").mkdir(parents=True)
            (proc / "processed" / "张伟.txt").write_text("访谈内容", encoding="utf-8")
            md = '- [来源:张伟]: "张伟表示排查问题需要反复切换工具"'
            codes = {item["code"] for item in validate_privacy_in_markdown(md, proc)}
            self.assertIn("P0-PRIVACY-EVIDENCE-SOURCE-MD", codes)
            self.assertIn("P0-PRIVACY-REAL-NAME-MD", codes)

    def test_prepare_04_refuses_privacy_leak_without_overwriting_existing_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed").mkdir(parents=True)
            (proc / "processed" / "张伟.txt").write_text("访谈内容", encoding="utf-8")
            draft = {
                "status": "draft",
                "context_snapshot": {},
                "personas": [{
                    "id": "persona-1",
                    "name": "开发者",
                    "description": "负责模型开发",
                    "user_count": 1,
                    "fields": {
                        "pain_points": [{
                            "title": "排查困难",
                            "detail": "需要反复切换工具",
                            "mention_count": 1,
                            "mentioned_by": ["张伟"],
                            "evidence_quotes": ['[来源:张伟]: "排查问题需要反复切换工具"'],
                        }],
                    },
                }],
            }
            (proc / "04-personas.draft.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
            md_path = proc / "04-personas.md"
            md_path.write_text("安全的旧版本\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "隐私问题"):
                refresh_04_md(proc, "04-personas")
            self.assertEqual(md_path.read_text(encoding="utf-8"), "安全的旧版本\n")

    def test_workflow_prepare_04_returns_bounded_privacy_repair_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "过程稿"
            (proc / "processed").mkdir(parents=True)
            (proc / "processed" / "张伟.txt").write_text("访谈内容", encoding="utf-8")
            draft = {
                "status": "draft", "context_snapshot": {},
                "personas": [{
                    "id": "persona-1", "name": "开发者", "description": "负责模型开发", "user_count": 1,
                    "fields": {"pain_points": [{
                        "title": "排查困难", "detail": "需要反复切换工具", "mention_count": 1,
                        "mentioned_by": ["张伟"],
                        "evidence_quotes": ['[来源:张伟]: "排查问题需要反复切换工具"'],
                    }]},
                }],
            }
            (proc / "04-personas.draft.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "workflow.py"), "--workdir", str(proc), "prepare-04", "--stem", "04-personas"],
                text=True, capture_output=True, encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 1)
            result = json.loads(completed.stdout)
            self.assertEqual(result["blocking_error_code"], "P0-PRIVACY-04")
            self.assertFalse(result["files_changed"])
            self.assertIn("P 编号", result["next_action"])


    def test_html_structure_words_are_not_bare_names(self):
        html = "<div>阶段</div><div>发现</div><div>试听</div><div>旅程</div>"
        issues = validate_privacy_in_html(html, None)
        codes = {i["code"] for i in issues}
        self.assertNotIn("P0-PRIVACY-BARE-NAME-HTML", codes)


if __name__ == "__main__":
    unittest.main()
