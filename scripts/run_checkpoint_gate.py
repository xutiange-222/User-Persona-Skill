#!/usr/bin/env python3
"""Run one bounded checkpoint gate and prevent weak-model repair loops."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.path_utils import resolve_process_dir
    from scripts.validate_checkpoint_pairing import validate_checkpoint_pairing
    from scripts.recovery_policy import recovery_for
except ImportError:
    from path_utils import resolve_process_dir
    from validate_checkpoint_pairing import validate_checkpoint_pairing
    from recovery_policy import recovery_for


TARGETS = (
    "00-research-goal", "01-paradigm", "02-classification", "03-field-alignment",
    "04-personas", "04-journeys", "05-report", "render",
)
STATE_FILE = ".checkpoint-gate-state.json"
STAGE_INDEX = {name: index for index, name in enumerate(TARGETS)}
PRIORITY_CODES = (
    "UNAUTHORIZED_PROCESS_BUILDER",
    "CHECKPOINT_JSON_INVALID", "CHECKPOINT_SCHEMA_INVALID",
    "VALIDATOR_RUNTIME_ERROR",
    "CHECKPOINT_MD_MISSING", "CHECKPOINT_JSON_MISSING", "CHECKPOINT_PAIR_MISSING",
    "CHECKPOINT_ALIGNMENT_HASH_MISMATCH",
    "PROCESSED_EXTRACTED_COUNT_MISMATCH", "PROCESSED_EXTRACTED_NAME_MISMATCH", "PROCESSED_CONTENT_DUPLICATE",
    "PARADIGM_MD_ROUTES_MISSING", "PARADIGM_MD_INTERNAL_CODE_VISIBLE", "PARADIGM_MD_RECOMMENDATION_MISSING",
    "HUMAN_MD_RAW_FIELD_NAME", "HUMAN_MD_MACHINE_ID_VISIBLE", "HUMAN_MD_RAW_ENUM_VISIBLE",
    "HUMAN_MD_CONTENT_FINGERPRINT_MISMATCH", "JOURNEY_MD_GLOBAL_CONTEXT_MISSING", "JOURNEY_MD_ROLE_STAGE_MATRIX_MISSING",
    "JOURNEY_MD_LOCATION_MISSING", "JOURNEY_ALIGNMENT_REVIEW_INCOMPLETE",
    "CHECKPOINT_CONFIRMATION_CONTRADICTORY", "JOURNEY_CONTENT_CONFIRMATION_MISSING",
)


def _priority(error: dict[str, Any]) -> tuple[int, str]:
    code = str(error.get("code") or "")
    try:
        rank = PRIORITY_CODES.index(code)
    except ValueError:
        rank = len(PRIORITY_CODES)
    return rank, code


def select_blocking_group(errors: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Return one error-code family so the model fixes one cause per turn."""
    if not errors:
        return []
    first = sorted(errors, key=_priority)[0]
    code = first.get("code")
    return [item for item in errors if item.get("code") == code][:limit]


def _signature(group: list[dict[str, Any]]) -> str:
    payload = [(item.get("code"), item.get("path"), item.get("message")) for item in group]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _error_stage(error: dict[str, Any]) -> int | None:
    path = str(error.get("path") or "").lower()
    code = str(error.get("code") or "")
    for stem in TARGETS[:-1]:
        if stem in path:
            return STAGE_INDEX[stem]
    if any(token in path for token in ("processed", "extracted", "reduced", "source-manifest", "terminology-glossary")):
        return STAGE_INDEX["04-personas"]
    if code.startswith(("HTML_", "VISUAL_", "DELIVERY_")) or "report.html" in path:
        return STAGE_INDEX["render"]
    if code in {"ONLY_FINAL_REPORT", "FINAL_WITHOUT_PREREQ", "REPORT_VALIDATOR_ERROR"}:
        return STAGE_INDEX["05-report"]
    return None


def _target_scoped(errors: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    if target == "render":
        return errors
    limit = STAGE_INDEX[target]
    return [error for error in errors if _error_stage(error) is None or _error_stage(error) <= limit]


def run_gate(process_dir: Path, target: str, *, record_attempt: bool = True) -> dict[str, Any]:
    all_errors = validate_checkpoint_pairing(process_dir, require_complete=(target == "render"))
    errors = _target_scoped(all_errors, target)
    group = select_blocking_group(errors)
    state_path = process_dir / STATE_FILE
    previous: dict[str, Any] = {}
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    signature = _signature(group) if group else ""
    repeated = int(previous.get("consecutive_same_failure") or 0)
    no_progress = int(previous.get("consecutive_no_progress") or 0)
    if record_attempt:
        repeated = repeated + 1 if signature and signature == previous.get("signature") else (1 if signature else 0)
        previous_count = previous.get("target_error_count")
        made_progress = bool(
            group
            and previous.get("target") == target
            and isinstance(previous_count, int)
            and len(errors) < previous_count
        )
        if not group or made_progress:
            no_progress = 0
        elif previous.get("target") == target and isinstance(previous_count, int):
            no_progress += 1
        else:
            no_progress = 0
        state = {"target": target, "signature": signature, "consecutive_same_failure": repeated, "consecutive_no_progress": no_progress, "target_error_count": len(errors), "last_error_code": group[0].get("code") if group else None}
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stopped = bool(group and (repeated >= 3 or no_progress >= 3))
    recovery = recovery_for(group[0], process_dir) if group else None
    if not group:
        status = "passed"
        next_action = "进入下一检查点" if target != "render" else "允许渲染"
    elif stopped:
        status = "stopped_repeated_failure"
        next_action = recovery.get("fallback_command") or "停止自动修补，保留产物并请求用户处理当前硬阻断"
    elif recovery and recovery.get("kind") == "automatic":
        status = "recoverable"
        next_action = recovery["command"]
    else:
        status = "fix_one_error_class"
        next_action = recovery.get("command") or recovery.get("explanation") or f"只修复 {group[0].get('code')}，随后重跑本命令"
    return {
        "status": status,
        "target": target,
        "next_action": next_action,
        "blocking_error_code": group[0].get("code") if group else None,
        "blocking_errors": group,
        "recovery": recovery,
        "consecutive_same_failure": repeated,
        "consecutive_no_progress": no_progress,
        "stop_threshold": 3,
        "target_error_count": len(errors),
        "total_error_count": len(all_errors),
        "forbidden_actions": [] if not group else ["创建过程目录临时脚本", "修改下游检查点", "尝试渲染"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded gate; show only the first repairable error class.")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--target", required=True, choices=TARGETS)
    parser.add_argument("--no-record", action="store_true", help="Inspect without incrementing the repeated-failure counter.")
    args = parser.parse_args()
    result = run_gate(resolve_process_dir(Path(args.workdir)), args.target, record_attempt=not args.no_record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
