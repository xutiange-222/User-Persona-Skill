#!/usr/bin/env python3
"""Deterministic, resumable review rounds for complex 2B/2D journeys."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.path_utils import resolve_process_dir
    from scripts.render_checkpoint_md import render_journeys_md
except ImportError:
    from path_utils import resolve_process_dir
    from render_checkpoint_md import render_journeys_md


ROUND_DEFS = (
    ("global_map", "全局地图", "确认旅程全局"),
    ("role_responsibility", "角色责任", "确认角色责任"),
    ("individual_journeys", "单角色旅程", "确认单角色旅程"),
    ("branches_evidence", "分支与证据", "确认旅程分支与证据"),
)
REJECTION_RE = re.compile(r"不确认|先不确认|取消确认|看不懂|看得头晕|跳过|直接继续|你继续吧", re.I)


def needs_guided_rounds(data: dict[str, Any]) -> bool:
    """Use rounds only where a single review surface is predictably hard to parse."""
    journeys = data.get("journeys") or []
    research_type = str((data.get("context_snapshot") or {}).get("research_type") or "")
    if research_type not in {"toB", "toD"}:
        return False
    overall = any(item.get("component_type") == "tob_journey_l1" for item in journeys)
    individual_count = sum(item.get("component_type") == "tob_journey_l2" for item in journeys)
    stage_count = sum(len((item.get("props") or {}).get("stages") or []) for item in journeys)
    return (overall and individual_count > 0) or len(journeys) > 2 or stage_count > 8


def expected_alignment_review(data: dict[str, Any]) -> dict[str, Any]:
    if not needs_guided_rounds(data):
        return {"mode": "single_pass", "rounds": []}
    existing = data.get("alignment_review") or {}
    existing_by_id = {
        str(item.get("id")): item for item in existing.get("rounds") or [] if isinstance(item, dict)
    }
    rounds = []
    for round_id, label, phrase in ROUND_DEFS:
        old = existing_by_id.get(round_id) or {}
        message = str(old.get("user_message") or "").strip()
        confirmed = bool(old.get("confirmed")) and phrase in message and not REJECTION_RE.search(message)
        rounds.append({
            "id": round_id,
            "label": label,
            "required_phrase": phrase,
            "confirmed": confirmed,
            "user_message": message if confirmed else "",
        })
    return {"mode": "guided_rounds", "rounds": rounds}


def alignment_review_errors(data: dict[str, Any]) -> list[dict[str, str]]:
    expected = expected_alignment_review(data)
    actual = data.get("alignment_review")
    if actual != expected:
        return [{
            "code": "JOURNEY_ALIGNMENT_REVIEW_INCOMPLETE",
            "path": "alignment_review",
            "message": "复杂 2B/2D 旅程必须按全局地图、角色责任、单角色旅程、分支与证据分轮确认。",
        }]
    if expected["mode"] == "guided_rounds":
        pending = [item for item in expected["rounds"] if not item["confirmed"]]
        if pending:
            item = pending[0]
            return [{
                "code": "JOURNEY_ALIGNMENT_REVIEW_INCOMPLETE",
                "path": f"alignment_review.{item['id']}",
                "message": f"下一轮：{item['label']}。用户核对后需回复“{item['required_phrase']}”。",
            }]
    return []


def record_round(process_dir: Path, round_id: str, user_message: str) -> dict[str, Any]:
    process_dir = resolve_process_dir(process_dir)
    draft_path = process_dir / "04-journeys.draft.json"
    if not draft_path.is_file():
        raise SystemExit("04-journeys.draft.json 不存在，先运行 prepare-04。")
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    review = expected_alignment_review(data)
    if review["mode"] != "guided_rounds":
        raise SystemExit("当前旅程规模使用一次确认，无需记录分轮确认。")
    ids = [item[0] for item in ROUND_DEFS]
    if round_id not in ids:
        raise SystemExit(f"未知轮次：{round_id}")
    target_index = ids.index(round_id)
    first_pending = next((i for i, item in enumerate(review["rounds"]) if not item["confirmed"]), len(ids))
    if target_index != first_pending:
        expected = review["rounds"][first_pending] if first_pending < len(ids) else None
        hint = f"下一轮应为 {expected['id']}（{expected['label']}）。" if expected else "四轮均已确认。"
        raise SystemExit("必须按顺序确认。" + hint)
    target = review["rounds"][target_index]
    message = user_message.strip()
    if target["required_phrase"] not in message or REJECTION_RE.search(message):
        raise SystemExit(f"本轮未确认。用户新回复需明确包含“{target['required_phrase']}”，且不能含拒绝、困惑或跳过语义。")
    target["confirmed"] = True
    target["user_message"] = message
    data["alignment_review"] = review
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = process_dir / "04-journeys.md"
    md_path.write_text(render_journeys_md(data).rstrip() + "\n", encoding="utf-8")
    next_item = next((item for item in review["rounds"] if not item["confirmed"]), None)
    return {
        "recorded": round_id,
        "next_round": next_item["id"] if next_item else None,
        "next_label": next_item["label"] if next_item else "全部分轮已完成，可请求最终确认",
        "md": str(md_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record one explicit 2B/2D journey review round.")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--round", required=True, choices=[item[0] for item in ROUND_DEFS])
    parser.add_argument("--user-message", required=True)
    args = parser.parse_args()
    print(json.dumps(record_round(Path(args.workdir), args.round, args.user_message), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
