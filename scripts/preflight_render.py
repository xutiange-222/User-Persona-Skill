#!/usr/bin/env python3
"""Run every render-blocking check before asking the user to confirm 05."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _draft_cross_checks(process_dir: Path, report: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    try:
        from scripts.components.validate import validate_report_json
        for issue in validate_report_json(report, process_dir):
            if issue.get("level") == "ERROR":
                errors.append({"code": str(issue.get("code") or "REPORT_DRAFT_INVALID"), "path": str(issue.get("path") or "05-report.draft.json"), "message": str(issue.get("message") or "报告草稿无效")})
    except Exception as exc:
        errors.append({"code": "REPORT_DRAFT_VALIDATOR_ERROR", "path": "05-report.draft.json", "message": str(exc)})

    paradigm = _load(process_dir / "01-paradigm.json").get("paradigm")
    goal = _load(process_dir / "00-research-goal.json")
    paradigm_data = _load(process_dir / "01-paradigm.json")
    expected_context = {
        "research_question": goal.get("research_question"),
        "decision_use": goal.get("decision_use"),
        "research_type": paradigm_data.get("research_type"),
        "paradigm": paradigm_data.get("paradigm"),
    }
    actual_context = (report.get("metadata") or {}).get("context_snapshot") or {}
    if all(expected_context.values()) and actual_context != expected_context:
        errors.append({"code": "CHECKPOINT_CONTEXT_DRIFT", "path": "05-report.draft.json", "message": "报告草稿的研究问题、决策用途、业务类型和画像方式必须逐项继承 00/01，不得改写。"})
    required_layout = {"R4": "layout-matrix-2d", "R5": "layout-distribution-multi"}.get(paradigm)
    if required_layout:
        layouts = [page.get("layout") for page in report.get("personas") or [] if isinstance(page, dict)]
        if layouts.count(required_layout) != 1:
            errors.append({"code": "PARADIGM_OVERVIEW_LAYOUT", "path": "05-report.draft.json", "message": f"{paradigm} 必须恰好包含一个 {required_layout} 总览页。"})

    journeys_path = process_dir / "04-journeys.json"
    if journeys_path.is_file():
        try:
            from scripts.validate_journey_checkpoint import _canonical, _journeys_from_report
            confirmed_data = _load(journeys_path)
            if _canonical(confirmed_data.get("journeys") or []) != _canonical(_journeys_from_report(report)):
                errors.append({"code": "JOURNEY_REPORT_MISMATCH", "path": "05-report.draft.json", "message": "报告草稿中的旅程必须逐项复用 04 已确认旅程。"})
        except Exception as exc:
            errors.append({"code": "JOURNEY_DRAFT_VALIDATOR_ERROR", "path": "05-report.draft.json", "message": str(exc)})
    return errors


def _avatar_warnings(process_dir: Path, report: dict[str, Any]) -> list[dict[str, str]]:
    alignment = _load(process_dir / "03-field-alignment.json")
    visual = alignment.get("visual_assets") or {}
    if visual.get("avatar_use_default") is not True:
        return []
    try:
        from scripts.avatar_assets import preview_default_avatar_assignments
        assignments = preview_default_avatar_assignments(report, process_dir)
    except Exception as exc:
        return [{"code": "AVATAR_PREVIEW_FAILED", "path": "03-field-alignment.json", "message": str(exc)}]
    if not assignments:
        return [{"code": "AVATAR_DEFAULT_EMPTY", "path": "assets/default-avatars", "message": "用户选择默认头像，但没有可用默认头像；渲染将使用文字占位。"}]
    return [{"code": "AVATAR_DEFAULT_AUTO_ASSIGNED", "path": "05-report.draft.json", "message": "默认头像将由渲染器稳定分配：" + "；".join(f"{name}→{filename}" for name, filename in assignments.items())}]


def _upstream_semantic_checks(process_dir: Path) -> list[dict[str, str]]:
    """Run gates that the renderer would otherwise discover only after 05 seal."""
    errors: list[dict[str, str]] = []
    alignment_path = process_dir / "03-field-alignment.json"
    if alignment_path.is_file():
        try:
            from scripts.validate_field_alignment import validate_field_alignment
            alignment = _load(alignment_path)
            errors.extend({
                "code": "FIELD_ALIGNMENT_INVALID",
                "path": "03-field-alignment.json",
                "message": message,
            } for message in validate_field_alignment(alignment, require_assets_ready=True))
        except Exception as exc:
            errors.append({"code": "FIELD_ALIGNMENT_VALIDATOR_ERROR", "path": "03-field-alignment.json", "message": str(exc)})

    if (process_dir / "04-journeys.json").is_file():
        try:
            from scripts.validate_journey_checkpoint import validate_journey_checkpoint
            errors.extend(validate_journey_checkpoint(process_dir))
        except Exception as exc:
            errors.append({"code": "JOURNEY_VALIDATOR_ERROR", "path": "04-journeys.json", "message": str(exc)})
    return errors


def run_preflight(process_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    process_dir = resolve_process_dir(process_dir)
    try:
        from scripts.validate_checkpoint_pairing import validate_checkpoint_pairing
        upstream = validate_checkpoint_pairing(process_dir, require_complete=False)
    except Exception as exc:
        upstream = [{"code": "PREFLIGHT_VALIDATOR_ERROR", "path": str(process_dir), "message": str(exc)}]
    # 05 is being rebuilt now. Only upstream errors are relevant before its MD exists.
    blockers = [
        item for item in upstream
        if "05-report" not in str(item.get("path") or "")
        and item.get("code") != "HTML_WITHOUT_REPORT_JSON"
    ]
    blockers.extend(_upstream_semantic_checks(process_dir))
    blockers.extend(_draft_cross_checks(process_dir, report))
    # Several validators intentionally overlap. Show each cause once so a weak
    # model receives one bounded repair list rather than a noisy retry queue.
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in blockers:
        key = (str(item.get("code") or ""), str(item.get("path") or ""), str(item.get("message") or ""))
        unique[key] = item
    blockers = list(unique.values())
    warnings = _avatar_warnings(process_dir, report)
    return {
        "valid": not blockers,
        "phase": "before_05_user_confirmation",
        "blocking_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "next_action": (
            "允许生成 05-report.md" if not blockers
            else "一次性修复以上全部上游错误，重新生成受影响的 04 MD/JSON 并获得确认后，再运行 prepare-05"
        ),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--draft", help="Defaults to <process>/05-report.draft.json")
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    draft = Path(args.draft) if args.draft else process_dir / "05-report.draft.json"
    result = run_preflight(process_dir, _load(draft))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
