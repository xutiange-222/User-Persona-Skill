#!/usr/bin/env python3
"""Seal a value-alignment checkpoint after an explicit user confirmation.

It updates
the MD status marker, records the exact user reply, and binds JSON to the MD by
SHA-256 so rendering cannot accept a later or summary-only replacement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from path_utils import resolve_process_dir
try:
    from scripts.checkpoint_hash import md_sha256_text
except ImportError:
    from checkpoint_hash import md_sha256_text


GENERIC_REPLY_RE = re.compile(
    r"^(?:好|好的|可以|没问题|确认|继续|下一步|开始|开始生成|开始渲染|生成|渲染|"
    r"ok|okay)[。.!！]?$",
    re.IGNORECASE,
)
REJECTION_OR_SKIP_RE = re.compile(
    r"(?:不确认|先不确认|暂不确认|取消确认|别确认|不要确认|跳过确认|"
    r"不看了|看不懂|看得头晕|直接继续|你继续吧)",
    re.IGNORECASE,
)
DEFAULT_SECTIONS = {
    "00-research-goal": ["goals", "scope", "constraints", "workspace"],
    "01-paradigm": ["paradigm", "reason", "alternatives", "groups"],
    "02-classification": ["basis", "boundaries", "labels", "respondent_mapping", "groups", "uncertainties"],
    "03-field-alignment": ["fields", "modules", "journey", "visual_assets", "visual_spec"],
    "04-personas": ["names", "persona_values", "evidence", "risks", "information_loss"],
    "04-journeys": ["scope", "stages", "substages", "lanes", "nodes", "edges", "painpoints_or_gaps", "touchpoints", "emotions", "evidence"],
    "05-report": ["page_plan", "modules", "information_loss"],
}
CONFIRMATION_PHRASES = {
    "00-research-goal": "确认研究目标",
    "01-paradigm": "确认画像方式",
    "02-classification": "确认分类内容",
    "03-field-alignment": "确认字段与视觉范围",
    "04-personas": "确认画像内容",
    "04-journeys": "确认旅程内容",
    "05-report": "确认报告结构",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal any confirmed 00-05 workflow checkpoint.")
    parser.add_argument("--workdir", required=True, help="Run directory or process directory.")
    parser.add_argument("--stem", required=True, choices=sorted(DEFAULT_SECTIONS))
    parser.add_argument("--user-message", required=True, help="Exact user reply, copied verbatim.")
    args = parser.parse_args()

    exact_reply = args.user_message.strip()
    required_phrase = CONFIRMATION_PHRASES[args.stem]
    if (
        GENERIC_REPLY_RE.fullmatch(exact_reply)
        or required_phrase not in exact_reply
        or REJECTION_OR_SKIP_RE.search(exact_reply)
    ):
        raise SystemExit(
            "Refusing ambiguous, contradictory, skip-review, or correction-only confirmation. "
            "Keep this checkpoint pending, simplify or revise the MD, then "
            f"ask the user to include the exact phrase '{required_phrase}' in a new reply."
        )

    process_dir = resolve_process_dir(Path(args.workdir))
    md_path = process_dir / f"{args.stem}.md"
    json_path = process_dir / f"{args.stem}.json"
    draft_path = process_dir / f"{args.stem}.draft.json"
    if not md_path.is_file():
        raise SystemExit(f"{md_path.name} must exist before sealing.")
    source_json_path = draft_path if args.stem == "05-report" and draft_path.is_file() else (json_path if json_path.is_file() else draft_path)
    if not source_json_path.is_file():
        raise SystemExit(
            f"{json_path.name} or {draft_path.name} must contain the structured content shown in {md_path.name}."
        )

    md_text = md_path.read_text(encoding="utf-8")
    if args.stem == "03-field-alignment" and re.search(r"(?m)^\s*-\s*\[\s\]", md_text):
        raise SystemExit(
            "Refusing to seal 03-field-alignment: the MD still contains unchecked decisions. "
            "Resolve every field, journey, avatar, screenshot and palette item, regenerate the MD, then ask for confirmation."
        )
    if "确认状态：已确认" not in md_text:
        pending_re = re.compile(r"确认状态\s*[：:]\s*(?:待用户确认|待确认|草稿)", re.IGNORECASE)
        if pending_re.search(md_text):
            md_text = pending_re.sub("确认状态：已确认", md_text, count=1)
        else:
            md_text = md_text.rstrip() + "\n\n确认状态：已确认\n"
    data = json.loads(source_json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{json_path.name} must contain one JSON object.")
    if args.stem == "05-report":
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected_marker = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        marker = re.search(r"<!--\s*机器内容指纹：([0-9a-f]{64})\s*-->", md_text)
        if not marker or marker.group(1) != expected_marker:
            raise SystemExit(
                "Refusing to seal 05-report: 05-report.md was not generated from the current "
                "05-report.draft.json. Run workflow.py prepare-05 and let the user review it."
            )
        try:
            from scripts.preflight_render import run_preflight
        except ImportError:
            from preflight_render import run_preflight
        preflight = run_preflight(process_dir, data)
        if not preflight["valid"]:
            raise SystemExit(
                "Refusing to seal 05-report: render preflight changed or failed after MD generation.\n"
                + json.dumps(preflight, ensure_ascii=False, indent=2)
            )
    if args.stem in {"04-personas", "04-journeys"}:
        root_key = "personas" if args.stem == "04-personas" else "journeys"
        content = data.get(root_key) or []
        payload = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected_marker = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        marker = re.search(r"<!--\s*机器内容指纹：([0-9a-f]{64})\s*-->", md_text)
        if not marker or marker.group(1) != expected_marker:
            raise SystemExit(
                f"Refusing to seal {args.stem}: the visible MD was not generated from the current "
                f"structured draft. Run render_checkpoint_md.py again and let the user review it."
            )
    target = data.setdefault("metadata", {}) if args.stem == "05-report" else data
    if args.stem != "05-report":
        if target.get("status") != "not_applicable":
            target["status"] = "confirmed"
    target["user_confirmed"] = True
    target["confirmation_user_message"] = exact_reply
    target["confirmation_message_summary"] = f"用户已明确确认本检查点完整内容：{required_phrase}。"
    target["confirmed_value_sections"] = DEFAULT_SECTIONS[args.stem]
    if args.stem == "02-classification" and target.get("status") == "not_applicable":
        target["confirmed_value_sections"] = ["applicability", "uncertainties"]
    if args.stem == "04-journeys":
        try:
            from scripts.validate_evidence_traceability import validate_journey_data_evidence
        except ImportError:
            from validate_evidence_traceability import validate_journey_data_evidence
        evidence_errors = validate_journey_data_evidence(target, process_dir)
        if evidence_errors:
            raise SystemExit(
                "Refusing to seal 04-journeys: evidence must be repaired before asking for final journey confirmation.\n"
                + json.dumps({"errors": evidence_errors}, ensure_ascii=False, indent=2)
            )
        try:
            from scripts.validate_journey_checkpoint import (
                build_presentation_review,
                journey_presentation_errors,
            )
        except ImportError:
            from validate_journey_checkpoint import (  # type: ignore
                build_presentation_review,
                journey_presentation_errors,
            )
        target["presentation_review"] = build_presentation_review(target)
        try:
            from scripts.journey_alignment import alignment_review_errors, expected_alignment_review
        except ImportError:
            from journey_alignment import alignment_review_errors, expected_alignment_review  # type: ignore
        target["alignment_review"] = expected_alignment_review(target)
        review_errors = alignment_review_errors(target)
        if review_errors:
            details = "\n".join(f"[{item['code']}] {item['message']}" for item in review_errors)
            raise SystemExit(
                "Refusing to seal 04-journeys: guided review is incomplete.\n" + details
            )
        quality_review = target.setdefault("quality_review", {})
        quality_review["stage_names_confirmed"] = True
        quality_review["flow_order_confirmed"] = True
        quality_review.setdefault("evidence_gaps", [])
        quality_review["evidence_gaps_acknowledged"] = True
        presentation_errors = journey_presentation_errors(md_text, target)
        if presentation_errors:
            details = "\n".join(
                f"[{item['code']}] {item['message']}" for item in presentation_errors
            )
            raise SystemExit(
                "Refusing to seal 04-journeys: the user has not been shown every concrete "
                f"journey value.\n{details}"
            )
    if args.stem in {"04-personas", "04-journeys"}:
        try:
            from scripts.render_checkpoint_md import render_journeys_md, render_personas_md
        except ImportError:
            from render_checkpoint_md import render_journeys_md, render_personas_md  # type: ignore
        if args.stem == "04-personas":
            custom_labels: dict[str, str] = {}
            alignment_path = process_dir / "03-field-alignment.json"
            if alignment_path.is_file():
                custom_labels = json.loads(alignment_path.read_text(encoding="utf-8")).get("fields_display_names") or {}
            md_text = render_personas_md(target, custom_labels).rstrip() + "\n"
        else:
            md_text = render_journeys_md(target).rstrip() + "\n"
    target["alignment_md_sha256"] = md_sha256_text(md_text)
    try:
        from scripts.validate_checkpoint_pairing import _schema_errors
    except ImportError:
        from validate_checkpoint_pairing import _schema_errors  # type: ignore
    schema_errors = _schema_errors(args.stem, data)
    if schema_errors:
        details = "\n".join(f"- {item}" for item in schema_errors[:12])
        raise SystemExit(
            f"Refusing to seal {args.stem}: final JSON does not satisfy its schema. "
            f"No MD or JSON file was changed.\n{details}"
        )
    md_path.write_text(md_text, encoding="utf-8", newline="\n")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "sealed": True,
        "checkpoint": args.stem,
        "md": str(md_path),
        "json": str(json_path),
        "alignment_md_sha256": target["alignment_md_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
