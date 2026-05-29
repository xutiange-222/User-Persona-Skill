#!/usr/bin/env python3
"""Audit generated user-persona artifacts.

This is optional. Use it only after a project has produced 04-personas.json or
report.html. For checking the skill source itself, use skill_audit.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from quality_common import SCRIPT_DIR

REPORT_DIR = SCRIPT_DIR / "_reports"
JSON_REPORT = REPORT_DIR / "artifact-audit-report.json"
MD_REPORT = REPORT_DIR / "artifact-audit-report.md"


def run_child(script: str, args: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script), *args],
        text=True,
        capture_output=True,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "success": False,
            "check": script,
            "errors": [{
                "code": "artifact_audit.invalid_output",
                "message": f"{script} 没有输出合法 JSON。",
                "path": script,
                "severity": "error",
            }],
            "warnings": [],
            "raw_stdout": proc.stdout,
            "raw_stderr": proc.stderr,
        }
    payload["exit_code"] = proc.returncode
    return payload


def collect_results(args) -> list[dict]:
    results = []
    if args.personas:
        results.append(run_child("check_personas_json.py", ["--input", args.personas]))
    if args.report:
        results.append(run_child("check_report_html.py", ["--input", args.report]))
    if args.workdir:
        results.append(run_child("check_personas_json.py", ["--workdir", args.workdir]))
        results.append(run_child("check_report_html.py", ["--workdir", args.workdir]))
    return results


def summarize(results: list[dict]) -> dict:
    errors = []
    warnings = []
    for result in results:
        for item in result.get("errors", []):
            errors.append({
                "check": result.get("check"),
                **item,
            })
        for item in result.get("warnings", []):
            warnings.append({
                "check": result.get("check"),
                **item,
            })
    return {
        "success": not errors,
        "audit_type": "artifact",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "results": results,
        "next_step": "可以进入人工浏览器验收。" if not errors else "先修复产物 JSON/HTML 问题,再重跑 artifact_audit.py。",
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# user-persona-v8 产物回归检查报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总结: {'通过' if payload.get('success') else '未通过'}",
        f"- 必须修复: {payload.get('error_count', 0)} 项",
        f"- 提醒项: {payload.get('warning_count', 0)} 项",
        "",
        "## 这份报告检查什么",
        "",
        "这份报告检查某一次画像项目生成后的产物,包括 `04-personas.json` 的证据契约、最终 HTML 的导航、矩阵、旅程和资源路径。它不检查 skill 源码本身。",
        "",
        "## 必须修复",
        "",
    ]
    errors = payload.get("errors", [])
    if not errors:
        lines.append("没有阻塞性问题。")
    else:
        for idx, item in enumerate(errors, 1):
            lines.extend([
                f"### P0-{idx}: {item.get('message', '')}",
                "",
                f"- 检查器: `{item.get('check', '')}`",
                f"- 代码: `{item.get('code', '')}`",
                f"- 位置: `{item.get('path', '')}`",
                "",
            ])

    lines.extend(["", "## 提醒项", ""])
    warnings = payload.get("warnings", [])
    if not warnings:
        lines.append("没有提醒项。")
    else:
        for idx, item in enumerate(warnings, 1):
            lines.extend([
                f"### W{idx}: {item.get('message', '')}",
                "",
                f"- 检查器: `{item.get('check', '')}`",
                f"- 代码: `{item.get('code', '')}`",
                f"- 位置: `{item.get('path', '')}`",
                "",
            ])

    lines.extend(["", "## 下一步", "", payload.get("next_step", "")])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", help="项目运行目录或过程稿目录")
    parser.add_argument("--personas", help="04-personas.json 路径")
    parser.add_argument("--report", help="report.html 路径")
    parser.add_argument("--json", default=str(JSON_REPORT), help="JSON 报告输出路径")
    parser.add_argument("--md", default=str(MD_REPORT), help="Markdown 报告输出路径")
    args = parser.parse_args()

    if not args.workdir and not args.personas and not args.report:
        payload = {
            "success": False,
            "audit_type": "artifact",
            "error_count": 1,
            "warning_count": 0,
            "errors": [{
                "code": "artifact_audit.no_input",
                "message": "请提供 --workdir、--personas 或 --report 中至少一个参数。",
                "path": None,
                "severity": "error",
            }],
            "warnings": [],
            "next_step": "如果想检查 skill 本身,请运行 skill_audit.py。若要检查产物,请传入某次画像项目目录。",
        }
    else:
        payload = summarize(collect_results(args))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.md).write_text(render_markdown(payload), encoding="utf-8-sig")

    summary = {
        "success": payload.get("success", False),
        "audit_type": "artifact",
        "errors": payload.get("error_count", 0),
        "warnings": payload.get("warning_count", 0),
        "json_report": str(Path(args.json)),
        "markdown_report": str(Path(args.md)),
        "next_step": payload.get("next_step"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if payload.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
