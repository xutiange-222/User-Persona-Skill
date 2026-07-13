#!/usr/bin/env python3
"""Regression tests for weak-model data preparation edge cases."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.extract_single import merge_chunked_results, split_long_document, stable_source_id
from scripts.preprocess import choose_output_path, is_generated_artifact, sanitize_group_name
from scripts.reduce_field import load_extractions


class PreprocessAndExtractionTests(unittest.TestCase):
    def test_group_name_cannot_escape_processed(self):
        self.assertEqual(sanitize_group_name("../../敏感目录"), "敏感目录")

    def test_duplicate_basenames_get_distinct_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a" / "访谈.txt"
            b = root / "b" / "访谈.txt"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("a", encoding="utf-8")
            b.write_text("b", encoding="utf-8")
            group = root / "processed" / "default"
            group.mkdir(parents=True)
            reserved: set[Path] = set()
            first = choose_output_path(group, a, reserved)
            second = choose_output_path(group, b, reserved)
            self.assertNotEqual(first.name, second.name)

    def test_dynamic_chunk_fields_are_not_silently_dropped(self):
        merged = merge_chunked_results([
            {"custom_list": ["前段"], "profile": {"role": "运维"}},
            {"custom_list": ["后段"], "profile": {"tool": "平台", "role": "管理员"}},
        ])
        self.assertEqual(merged["custom_list"], ["前段", "后段"])
        self.assertEqual(merged["profile"]["tool"], "平台")
        self.assertTrue(any(item["field"] == "profile.role" for item in merged["_chunk_conflicts"]))

    def test_source_id_is_anonymous_stable_and_content_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.txt"
            duplicate = root / "b.txt"
            different = root / "c.txt"
            first.write_text("同一份访谈", encoding="utf-8")
            duplicate.write_text("同一份访谈", encoding="utf-8")
            different.write_text("另一份访谈", encoding="utf-8")
            one = stable_source_id(first)
            self.assertEqual(one, stable_source_id(duplicate))
            self.assertNotEqual(one, stable_source_id(different))
            self.assertRegex(one, r"^P[0-9A-F]{8}$")

    def test_reduce_rejects_missing_input_instead_of_partial_merge(self):
        with self.assertRaises(FileNotFoundError):
            load_extractions(["missing.json"])

    def test_generated_checkpoint_cannot_reenter_as_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            process = project / "过程稿"
            process.mkdir()
            checkpoint = process / "04-personas.json"
            checkpoint.write_text("{}", encoding="utf-8")
            self.assertTrue(is_generated_artifact(checkpoint, process))

    def test_single_oversized_line_is_split(self):
        chunks = split_long_document("长" * 10000, max_tokens=1000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1600 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
