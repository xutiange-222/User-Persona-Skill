#!/usr/bin/env python3
"""Regression tests for the user-confirmed journey checkpoint."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_journey_checkpoint import (  # noqa: E402
    build_presentation_review,
    validate_journey_checkpoint,
)
from scripts.journey_alignment import expected_alignment_review  # noqa: E402


def _journey_props() -> dict:
    gallery = json.loads(
        (ROOT / "scripts/components/tests/gallery_data.json").read_text(encoding="utf-8")
    )
    for group in gallery.values():
        for item in group["items"]:
            if item["type"] == "journey_2c":
                return copy.deepcopy(item["props"])
    raise AssertionError("gallery_data lacks journey_2c")


def _quality_review() -> dict:
    return {
        "stage_names_confirmed": True,
        "flow_order_confirmed": True,
        "evidence_gaps": [],
        "evidence_gaps_acknowledged": True,
        "notes": "",
    }


class JourneyCheckpointTests(unittest.TestCase):
    def test_not_applicable_pair_allows_report_without_journey(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Path(tmp)
            (process / "03-field-alignment.json").write_text(
                json.dumps({"add_on_pages": {"journey": False}}), encoding="utf-8"
            )
            checkpoint = {
                "checkpoint": "04-journeys",
                "status": "not_applicable",
                "context_snapshot": {
                    "research_question": "确认哪些画像差异支持产品设计决策",
                    "decision_use": "用于确定画像差异和产品需求优先级",
                    "research_type": "toB",
                    "paradigm": "R1",
                },
                "user_confirmed": True,
                "confirmation_message_summary": "用户确认本次报告不需要用户旅程页面。",
                "confirmation_user_message": "确认旅程内容：本次不生成旅程",
                "confirmed_value_sections": ["scope"],
                "alignment_md_sha256": "0" * 64,
                "not_applicable_reason": "本次决策只需要画像差异，不需要过程视角。",
                "scope": "none",
                "journeys": [],
                "quality_review": _quality_review(),
            }
            checkpoint["presentation_review"] = build_presentation_review(checkpoint)
            checkpoint["alignment_review"] = expected_alignment_review(checkpoint)
            (process / "04-journeys.md").write_text(
                "确认状态：已确认\n\n本次决策只需要画像差异，不需要过程视角。",
                encoding="utf-8",
            )
            (process / "04-journeys.json").write_text(
                json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8"
            )
            (process / "05-report.json").write_text(
                json.dumps({"metadata": {}, "personas": []}), encoding="utf-8"
            )
            self.assertEqual(validate_journey_checkpoint(process), [])

    def test_report_must_reuse_confirmed_journey_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Path(tmp)
            props = _journey_props()
            (process / "03-field-alignment.json").write_text(
                json.dumps({"add_on_pages": {"journey": True}}), encoding="utf-8"
            )
            checkpoint = {
                "checkpoint": "04-journeys",
                "status": "confirmed",
                "user_confirmed": True,
                "confirmation_message_summary": "用户确认阶段名称、顺序、痛点和触点内容。",
                "not_applicable_reason": "",
                "scope": "single-persona",
                "journeys": [{
                    "persona_id": "persona-1-journey",
                    "component_type": "journey_2c",
                    "props": props,
                }],
                "quality_review": _quality_review(),
            }
            (process / "04-journeys.json").write_text(
                json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8"
            )
            changed = copy.deepcopy(props)
            changed["subtitle"] += "已改写"
            report = {
                "metadata": {},
                "personas": [{
                    "id": "persona-1-journey",
                    "components": [{"type": "journey_2c", "props": changed}],
                }],
            }
            (process / "05-report.json").write_text(
                json.dumps(report, ensure_ascii=False), encoding="utf-8"
            )
            errors = validate_journey_checkpoint(process)
            self.assertTrue(any(item["code"] == "JOURNEY_REPORT_MISMATCH" for item in errors))

    def test_confirmed_journey_requires_explicit_quality_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Path(tmp)
            checkpoint = {
                "checkpoint": "04-journeys",
                "status": "confirmed",
                "user_confirmed": False,
                "confirmation_message_summary": "模型自动生成旅程，尚未获得用户明确确认。",
                "not_applicable_reason": "",
                "scope": "single-persona",
                "journeys": [],
                "quality_review": {
                    "stage_names_confirmed": False,
                    "flow_order_confirmed": False,
                    "evidence_gaps": [],
                    "evidence_gaps_acknowledged": False,
                    "notes": "",
                },
            }
            (process / "04-journeys.json").write_text(
                json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8"
            )
            errors = validate_journey_checkpoint(process)
            self.assertTrue(any(item["code"] == "JOURNEY_CHECKPOINT_SCHEMA" for item in errors))

    def test_scope_cannot_claim_overall_without_l1_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Path(tmp)
            props = _journey_props()
            checkpoint = {
                "checkpoint": "04-journeys",
                "status": "confirmed",
                "user_confirmed": True,
                "confirmation_message_summary": "用户确认总体旅程和单画像旅程范围。",
                "scope": "overall-and-per-persona",
                "journeys": [{"persona_id": "persona-1", "component_type": "journey_2c", "props": props}],
                "quality_review": _quality_review(),
            }
            (process / "04-journeys.json").write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")
            errors = validate_journey_checkpoint(process)
            self.assertTrue(any(item["code"] == "JOURNEY_SCOPE_SHAPE" for item in errors))


if __name__ == "__main__":
    unittest.main()
