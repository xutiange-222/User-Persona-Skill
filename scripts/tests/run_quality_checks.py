#!/usr/bin/env python3
"""Run no-model quality checks for user-persona-v8."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from quality_common import SCRIPT_DIR, emit_result, Issue


def run_checker(script: str, args: list[str]) -> dict:
    cmd = [sys.executable, str(SCRIPT_DIR / script), *args]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "success": False,
            "check": script,
            "errors": [{
                "code": "runner.invalid_json",
                "message": "检查器没有输出合法 JSON。",
                "path": script,
                "severity": "error",
            }],
            "warnings": [],
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    payload["exit_code"] = proc.returncode
    if proc.stderr.strip():
        payload.setdefault("warnings", []).append({
            "code": "runner.stderr",
            "message": proc.stderr.strip(),
            "path": script,
            "severity": "warning",
        })
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", help="项目运行目录或过程稿目录")
    parser.add_argument("--personas", help="04-personas.json 路径")
    parser.add_argument("--report", help="report.html 路径")
    parser.add_argument("--delivery-dir", help="最终交付件目录")
    parser.add_argument("--skip-skill", action="store_true", help="跳过 skill 静态扫描")
    args = parser.parse_args()

    results = []
    if not args.skip_skill:
        results.append(run_checker("check_skill_contracts.py", []))

    if args.personas:
        results.append(run_checker("check_personas_json.py", ["--input", args.personas]))
    elif args.workdir:
        results.append(run_checker("check_personas_json.py", ["--workdir", args.workdir]))

    if args.report:
        results.append(run_checker("check_report_html.py", ["--input", args.report]))
    elif args.delivery_dir:
        results.append(run_checker("check_report_html.py", ["--delivery-dir", args.delivery_dir]))
    elif args.workdir:
        results.append(run_checker("check_report_html.py", ["--workdir", args.workdir]))

    errors: list[Issue] = []
    warnings: list[Issue] = []
    for result in results:
        if not result.get("success"):
            for item in result.get("errors", []):
                errors.append(Issue(
                    item.get("code", "runner.child_failed"),
                    f"{result.get('check')}: {item.get('message')}",
                    item.get("path"),
                ))
        for item in result.get("warnings", []):
            warnings.append(Issue(
                item.get("code", "runner.child_warning"),
                f"{result.get('check')}: {item.get('message')}",
                item.get("path"),
                "warning",
            ))

    return emit_result(
        check_name="quality_checks",
        errors=errors,
        warnings=warnings,
        next_step="按子检查器 errors 修复后重跑 scripts/tests/run_quality_checks.py。",
        extra={"results": results},
    )


if __name__ == "__main__":
    raise SystemExit(main())
