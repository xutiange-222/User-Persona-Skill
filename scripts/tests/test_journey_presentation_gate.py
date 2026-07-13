from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.validate_journey_checkpoint import (
    build_presentation_review,
    journey_presentation_errors,
    required_journey_md_values,
)
from scripts.render_checkpoint_md import render_journeys_md
from scripts.journey_alignment import expected_alignment_review


ROOT = Path(__file__).resolve().parents[2]


def _journey_data() -> dict:
    gallery = json.loads(
        (ROOT / "scripts/components/tests/gallery_data.json").read_text(encoding="utf-8")
    )
    props = None
    for group in gallery.values():
        for item in group["items"]:
            if item["type"] == "journey_2c":
                props = copy.deepcopy(item["props"])
                break
        if props is not None:
            break
    assert props is not None
    data = {
        "status": "confirmed",
        "confirmation_user_message": "确认旅程内容，以上阶段和每个单元格均已检查。",
        "journeys": [{
            "persona_id": "persona-1-journey",
            "component_type": "journey_2c",
            "props": props,
            "evidence_bindings": [],
        }],
    }
    data["presentation_review"] = build_presentation_review(data)
    data["alignment_review"] = expected_alignment_review(data)
    return data


def test_scope_choice_cannot_confirm_concrete_journey_content() -> None:
    data = _journey_data()
    data["confirmation_user_message"] = "需要多角色综合旅程，也需要单角色旅程。"
    errors = journey_presentation_errors(
        "用户确认需要 L1 综合旅程和 L2 单角色旅程。", data
    )
    codes = {item["code"] for item in errors}
    assert "JOURNEY_CONTENT_CONFIRMATION_MISSING" in codes
    assert "JOURNEY_MD_CONTENT_INCOMPLETE" in codes


def test_stage_names_without_cells_are_rejected() -> None:
    data = _journey_data()
    md = "\n".join(str(item) for item in data["journeys"][0]["props"]["stages"])
    errors = journey_presentation_errors(md, data)
    assert any(item["code"] == "JOURNEY_MD_CONTENT_INCOMPLETE" for item in errors)


def test_complete_md_inventory_passes_presentation_gate() -> None:
    data = _journey_data()
    md = render_journeys_md(data)
    assert journey_presentation_errors(md, data) == []


def test_presentation_counts_and_hash_cannot_be_faked() -> None:
    data = _journey_data()
    data["presentation_review"]["stage_count"] += 1
    md = render_journeys_md(data)
    errors = journey_presentation_errors(md, data)
    assert any(
        item["code"] == "JOURNEY_PRESENTATION_INVENTORY_MISMATCH"
        for item in errors
    )


def test_l1_only_scope_is_distinct_from_l1_and_l2() -> None:
    from scripts.validate_journey_checkpoint import _scope_errors

    overall = {
        "persona_id": "journey-l1",
        "component_type": "tob_journey_l1",
        "props": {},
    }
    data = {"scope": "overall-only", "journeys": [overall]}
    alignment = {
        "research_type": "toB",
        "add_on_pages": {"journey_scope": "L1_only"},
    }
    assert _scope_errors(data, alignment) == []


def test_rejection_cannot_be_converted_to_confirmation_by_appending_phrase() -> None:
    data = _journey_data()
    data["confirmation_user_message"] = "不确认了，你继续吧；确认旅程内容"
    errors = journey_presentation_errors(render_journeys_md(data), data)
    assert any(item["code"] == "JOURNEY_CONTENT_CONFIRMATION_MISSING" for item in errors)
