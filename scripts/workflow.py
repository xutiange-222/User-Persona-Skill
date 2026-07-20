#!/usr/bin/env python3
"""Single public workflow entrypoint for weak models.

Other scripts remain internal building blocks.  Models below 100B should use
this command only, one subcommand at a time.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from scripts.path_utils import resolve_process_dir
    from scripts.recovery_check import check_recovery
    from scripts.recovery_policy import checkpoint_from_path
    from scripts.repair_workflow import archive_downstream, create_recovery_bundle, quarantine_builders, refresh_04_md, reopen_04_for_edit
    from scripts.run_checkpoint_gate import TARGETS, run_gate
except ImportError:
    from path_utils import resolve_process_dir
    from recovery_check import check_recovery
    from recovery_policy import checkpoint_from_path
    from repair_workflow import archive_downstream, create_recovery_bundle, quarantine_builders, refresh_04_md, reopen_04_for_edit
    from run_checkpoint_gate import TARGETS, run_gate


SCRIPT_DIR = Path(__file__).resolve().parent
UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}


def _automatic_repair(process_dir: Path, gate: dict[str, Any]) -> dict[str, Any] | None:
    recovery = gate.get("recovery") or {}
    if recovery.get("kind") != "automatic":
        return None
    code = gate.get("blocking_error_code")
    if code == "UNAUTHORIZED_PROCESS_BUILDER":
        return quarantine_builders(process_dir)
    if code in {
        "HUMAN_MD_RAW_FIELD_NAME", "HUMAN_MD_MACHINE_ID_VISIBLE", "HUMAN_MD_RAW_ENUM_VISIBLE",
        "JOURNEY_MD_GLOBAL_CONTEXT_MISSING",
        "JOURNEY_MD_ROLE_STAGE_MATRIX_MISSING", "JOURNEY_MD_LOCATION_MISSING",
        "CHECKPOINT_ALIGNMENT_HASH_MISMATCH",
        "CHECKPOINT_MD_STATUS_MISMATCH",
    }:
        path = str((gate.get("blocking_errors") or [{}])[0].get("path") or "")
        stem = checkpoint_from_path(path)
        if stem in {"04-personas", "04-journeys"}:
            return refresh_04_md(process_dir, stem)
    return None


def check_with_recovery(process_dir: Path, target: str, auto_recover: bool) -> dict[str, Any]:
    before = run_gate(process_dir, target, record_attempt=True)
    result: dict[str, Any] = {"before": before, "recovery_applied": None, "after": None}
    if auto_recover and before.get("status") == "recoverable":
        applied = _automatic_repair(process_dir, before)
        result["recovery_applied"] = applied
        if applied is not None:
            result["after"] = run_gate(process_dir, target, record_attempt=False)
    elif auto_recover and before.get("status") == "stopped_repeated_failure":
        try:
            result["recovery_applied"] = create_recovery_bundle(process_dir)
        except Exception as exc:
            result["recovery_applied"] = {"created": None, "error": str(exc)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="One public entrypoint for the User Persona workflow.")
    parser.add_argument("--workdir", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    prepare = sub.add_parser("prepare-04")
    prepare.add_argument("--stem", required=True, choices=["04-personas", "04-journeys"])
    sub.add_parser("prepare-05")
    seal = sub.add_parser("seal")
    seal.add_argument("--stem", required=True, choices=list(TARGETS[:-1]))
    seal.add_argument("--user-message", required=True)
    journey_review = sub.add_parser("journey-review")
    journey_review.add_argument("--round", required=True, choices=["global_map", "role_responsibility", "individual_journeys", "branches_evidence"])
    journey_review.add_argument("--user-message", required=True)
    check = sub.add_parser("check")
    check.add_argument("--target", required=True, choices=list(TARGETS))
    check.add_argument("--auto-recover", action="store_true")
    recover = sub.add_parser("recover")
    recover.add_argument("--action", required=True, choices=["quarantine-builders", "refresh-04-md", "archive-downstream", "reopen-04", "create-recovery-bundle"])
    recover.add_argument("--stem")
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))

    if args.command == "status":
        full = check_recovery(process_dir)
        output = {
            "status": full.get("status"),
            "process_dir": full.get("process_dir"),
            "completed_steps": full.get("completed_steps"),
            "next_step": full.get("next_step"),
            "blocking_errors": full.get("blocking_errors") or [],
            "processed_count": full.get("processed_count"),
            "extracted_count": full.get("extracted_count"),
            "checkpoint_complete": full.get("checkpoint_complete"),
            "downstream_valid": full.get("downstream_valid"),
        }
        code = 0
    elif args.command == "prepare-04":
        try:
            output = refresh_04_md(process_dir, args.stem)
            code = 0
        except ValueError as exc:
            message = str(exc)
            privacy_block = "隐私" in message or "P0-PRIVACY" in message
            output = {
                "rendered": False,
                "checkpoint": args.stem,
                "blocking_error_code": "P0-PRIVACY-04" if privacy_block else "CHECKPOINT_CONTENT_INVALID",
                "error": message,
                "files_changed": False,
                "next_action": (
                    "只修复 04-personas 草稿中被指出的证据来源或原话：来源改用 source-manifest 的 P 编号，原话姓名写成[姓名已脱敏]；随后重跑 prepare-04。"
                    if privacy_block else
                    "只修复当前 04 草稿中被指出的内容，再重跑 prepare-04。"
                ),
            }
            code = 1
    elif args.command == "prepare-05":
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "render_report_checkpoint_md.py"), "--workdir", str(process_dir)],
            text=True, capture_output=True, encoding="utf-8", errors="replace",
            env=UTF8_ENV,
        )
        if completed.returncode:
            output = {"rendered": False, "error": completed.stderr.strip() or completed.stdout.strip(), "files_changed": False}
            code = 1
        else:
            output = json.loads(completed.stdout)
            code = 0
    elif args.command == "seal":
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "seal_content_checkpoint.py"), "--workdir", str(process_dir), "--stem", args.stem, "--user-message", args.user_message],
            text=True, capture_output=True, encoding="utf-8", errors="replace",
            env=UTF8_ENV,
        )
        if completed.returncode:
            output = {"sealed": False, "error": completed.stderr.strip() or completed.stdout.strip(), "files_changed": False}
            code = 1
        else:
            output = json.loads(completed.stdout)
            code = 0
    elif args.command == "journey-review":
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "journey_alignment.py"), "--workdir", str(process_dir), "--round", args.round, "--user-message", args.user_message],
            text=True, capture_output=True, encoding="utf-8", errors="replace",
            env=UTF8_ENV,
        )
        if completed.returncode:
            output = {"recorded": False, "error": completed.stderr.strip() or completed.stdout.strip(), "files_changed": False}
            code = 1
        else:
            output = json.loads(completed.stdout)
            code = 0
    elif args.command == "check":
        output = check_with_recovery(process_dir, args.target, args.auto_recover)
        final = output.get("after") or output["before"]
        code = 0 if final.get("status") == "passed" else 1
    else:
        if args.action == "quarantine-builders":
            output = quarantine_builders(process_dir)
        elif args.action == "refresh-04-md":
            output = refresh_04_md(process_dir, str(args.stem or ""))
        elif args.action == "archive-downstream":
            output = archive_downstream(process_dir, str(args.stem or ""))
        elif args.action == "reopen-04":
            output = reopen_04_for_edit(process_dir, str(args.stem or ""))
        else:
            output = create_recovery_bundle(process_dir)
        code = 0
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
