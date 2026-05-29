#!/usr/bin/env python3
"""Audit the user-persona-v8 skill itself.

This is the main entrypoint for checking the skill source, prompts, templates,
and script contracts. It does not require or inspect a generated report.
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
JSON_REPORT = REPORT_DIR / "skill-audit-report.json"
MD_REPORT = REPORT_DIR / "skill-audit-report.md"


def run_skill_contracts() -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "check_skill_contracts.py")],
        text=True,
        capture_output=True,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "success": False,
            "check": "skill_contracts",
            "errors": [{
                "code": "skill_audit.invalid_output",
                "message": "check_skill_contracts.py 没有输出合法 JSON。",
                "path": "scripts/tests/check_skill_contracts.py",
                "severity": "error",
            }],
            "warnings": [],
            "raw_stdout": proc.stdout,
            "raw_stderr": proc.stderr,
        }
    payload["exit_code"] = proc.returncode
    if proc.stderr.strip():
        payload.setdefault("warnings", []).append({
            "code": "skill_audit.stderr",
            "message": proc.stderr.strip(),
            "path": "scripts/tests/check_skill_contracts.py",
            "severity": "warning",
        })
    return payload


def status_label(success: bool) -> str:
    return "通过" if success else "未通过"


def render_markdown(payload: dict) -> str:
    errors = payload.get("errors", [])
    warnings = payload.get("warnings", [])
    success = bool(payload.get("success"))
    lines = [
        "# user-persona-v8 Skill 质检报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总结: {status_label(success)}",
        f"- 必须修复: {len(errors)} 项",
        f"- 提醒项: {len(warnings)} 项",
        "",
        "## 这份报告检查什么",
        "",
        "这份报告只检查 skill 本身,包括入口流程、硬约束、prompt 契约、路径体系、模板骨架、用户话术和脚本契约。不检查某一次生成出来的画像报告。",
        "",
        "## 检查结果",
        "",
    ]

    if not errors:
        lines.append("没有发现阻塞性问题。")
    else:
        for idx, item in enumerate(errors, 1):
            lines.extend([
                f"### P0-{idx}: {item.get('message', '')}",
                "",
                f"- 代码: `{item.get('code', '')}`",
                f"- 位置: `{item.get('path', '')}`",
                "",
            ])

    lines.extend(["", "## 提醒项", ""])
    if not warnings:
        lines.append("没有提醒项。")
    else:
        for idx, item in enumerate(warnings, 1):
            lines.extend([
                f"### W{idx}: {item.get('message', '')}",
                "",
                f"- 代码: `{item.get('code', '')}`",
                f"- 位置: `{item.get('path', '')}`",
                "",
            ])

    lines.extend([
        "",
        "## 下一步",
        "",
        payload.get("next_step") or ("可以进入产物回归检查。" if success else "先修复必须修复项,再重跑 skill_audit.py。"),
        "",
        "## 相关命令",
        "",
        "```powershell",
        'python "C:\\Users\\HUAWEI\\.claude\\skills\\user-persona-v8\\scripts\\tests\\skill_audit.py"',
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(JSON_REPORT), help="JSON 报告输出路径")
    parser.add_argument("--md", default=str(MD_REPORT), help="Markdown 报告输出路径")
    parser.add_argument("--print", action="store_true", help="同时把摘要打印到终端")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = run_skill_contracts()
    payload["audit_type"] = "skill"
    payload["report_json"] = str(Path(args.json))
    payload["report_md"] = str(Path(args.md))

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.md).write_text(render_markdown(payload), encoding="utf-8-sig")

    summary = {
        "success": payload.get("success", False),
        "audit_type": "skill",
        "errors": len(payload.get("errors", [])),
        "warnings": len(payload.get("warnings", [])),
        "json_report": str(Path(args.json)),
        "markdown_report": str(Path(args.md)),
        "next_step": payload.get("next_step"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if payload.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
