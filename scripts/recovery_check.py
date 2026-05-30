#!/usr/bin/env python3
"""
recovery_check.py

扫工作目录,返回当前进度信息。让模型知道从哪一步继续。

调用:
    python recovery_check.py [--workdir PATH] [--format json|human]

输出:JSON 格式的进度状态(含 missing_artifacts 清单)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from path_utils import OUTPUT_ROOT_NAME, resolve_process_dir

CLASSIFICATION_PARADIGMS = frozenset({"R3", "R4", "R5"})

CHECKPOINT_FILES = (
    ("00-research-goal.json", "research_goal", "Step 0/1: 写入研究目标"),
    ("01-paradigm.json", "paradigm", "Step 2: 写入范式选择"),
    ("02-classification.json", "classification", "分类/区分点: 写入 02-classification.json"),
    ("03-field-alignment.json", "field_alignment", "字段对齐: 写入并校验 03-field-alignment.json"),
    ("04-personas.json", "personas", "合并: 写入 04-personas.json"),
    ("05-report.json", "report_json", "渲染前: 写入 05-report.json"),
)


def find_delivery_report(process_dir: Path) -> Path | None:
    """Return the newest final delivery report near a process directory."""
    run_dir = process_dir.parent if process_dir.name == "过程稿" else process_dir
    if not run_dir.exists():
        return None
    candidates = []
    for child in run_dir.iterdir():
        if child.is_dir() and child.name.startswith("最终交付件-"):
            report = child / "report.html"
            if report.exists():
                candidates.append(report)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _validate_field_alignment(field_file: Path) -> list[str]:
    try:
        try:
            from validate_field_alignment import (
                load_field_alignment,
                validate_field_alignment,
            )
        except ImportError:
            from scripts.validate_field_alignment import (
                load_field_alignment,
                validate_field_alignment,
            )

        return validate_field_alignment(load_field_alignment(field_file))
    except Exception as exc:
        return [str(exc)]


def audit_missing_artifacts(process_dir: Path, paradigm: str | None) -> list[dict]:
    """List checkpoint files/dirs that should exist but do not."""
    missing: list[dict] = []
    needs_classification = paradigm in CLASSIFICATION_PARADIGMS

    for filename, _step_id, hint in CHECKPOINT_FILES:
        if filename == "02-classification.json" and not needs_classification:
            continue
        path = process_dir / filename
        if not path.is_file():
            missing.append(
                {
                    "kind": "file",
                    "path": filename,
                    "hint": hint,
                }
            )

    processed_dir = process_dir / "processed"
    extracted_dir = process_dir / "extracted"
    processed_files = list(processed_dir.glob("*.txt")) if processed_dir.is_dir() else []
    extracted_files = list(extracted_dir.glob("*.json")) if extracted_dir.is_dir() else []

    if not processed_dir.is_dir() or not processed_files:
        missing.append(
            {
                "kind": "dir",
                "path": "processed/*.txt",
                "hint": "预处理: 每份访谈写入 processed/<名>.txt",
            }
        )
    elif len(extracted_files) < len(processed_files):
        missing.append(
            {
                "kind": "dir",
                "path": "extracted/*.json",
                "hint": (
                    f"单文档抽取: 需 {len(processed_files)} 份,当前仅 {len(extracted_files)} 份"
                ),
                "extracted_count": len(extracted_files),
                "processed_count": len(processed_files),
            }
        )

    delivery = find_delivery_report(process_dir)
    report_json = process_dir / "05-report.json"
    if delivery and not report_json.is_file():
        missing.append(
            {
                "kind": "warning",
                "path": "05-report.json",
                "hint": "已有最终 report.html 但缺少 05-report.json,无法可靠重渲染/续跑",
            }
        )

    return missing


def check_recovery(workdir: Path) -> dict:
    """
    扫过程稿目录,返回进度状态。

    返回字段:
    - status: fresh / in_progress / completed
    - completed_steps, next_step, missing_artifacts, ...
    """
    result: dict = {
        "status": "fresh",
        "completed_steps": [],
        "next_step": "Step 0: 扫文件 + 形成初判",
        "paradigm": None,
        "research_type": None,
        "workdir": str(workdir),
        "process_dir": str(workdir),
        "missing_artifacts": [],
        "extracted_count": 0,
        "processed_count": 0,
    }

    if not workdir.exists():
        return result

    # --- 00 research goal ---
    goal_file = workdir / "00-research-goal.json"
    if goal_file.is_file():
        result["completed_steps"].append("research_goal")
        goal = _load_json(goal_file) or {}
        result["research_type"] = goal.get("research_type")
        result["next_step"] = "Step 2: 确认范式并写入 01-paradigm.json"

    # --- 01 paradigm ---
    paradigm_file = workdir / "01-paradigm.json"
    if paradigm_file.is_file():
        result["completed_steps"].append("paradigm")
        paradigm_data = _load_json(paradigm_file) or {}
        result["paradigm"] = paradigm_data.get("paradigm")
        if result["paradigm"] in CLASSIFICATION_PARADIGMS:
            result["next_step"] = (
                "分类依据" if result["paradigm"] == "R3" else "价值变量/区分点 → 02-classification.json"
            )
        else:
            result["next_step"] = "字段对齐 → 03-field-alignment.json"

    # --- 02 classification ---
    classification_file = workdir / "02-classification.json"
    if classification_file.is_file():
        result["completed_steps"].append("classification")
        result["next_step"] = "字段对齐 → 03-field-alignment.json"

    # --- 03 field alignment ---
    field_file = workdir / "03-field-alignment.json"
    if field_file.is_file():
        fa_errors = _validate_field_alignment(field_file)
        if fa_errors:
            result["field_alignment_incomplete"] = True
            result["field_alignment_errors"] = fa_errors
            result["next_step"] = "字段对齐(未完成:须展示字段池并获用户确认)"
        else:
            result["completed_steps"].append("field_alignment")
            result["next_step"] = "预处理 + 单文档抽取 → processed/ 与 extracted/"

    # --- processed / extracted ---
    processed_dir = workdir / "processed"
    extracted_dir = workdir / "extracted"
    processed_files = list(processed_dir.glob("*.txt")) if processed_dir.is_dir() else []
    extracted_files = list(extracted_dir.glob("*.json")) if extracted_dir.is_dir() else []
    result["processed_count"] = len(processed_files)
    result["extracted_count"] = len(extracted_files)

    if processed_files and extracted_files:
        if len(extracted_files) >= len(processed_files):
            result["completed_steps"].append("extracted")
            result["next_step"] = "合并 → 04-personas.json"
        else:
            result["completed_steps"].append("extracted_partial")
            result["next_step"] = (
                f"完成单文档抽取(已 {len(extracted_files)}/{len(processed_files)})"
            )

    # --- 04 personas ---
    personas_file = workdir / "04-personas.json"
    if personas_file.is_file():
        result["completed_steps"].append("personas")
        result["next_step"] = "组装组件 JSON → 05-report.json"

    # --- 05 report json ---
    report_json_file = workdir / "05-report.json"
    if report_json_file.is_file():
        result["completed_steps"].append("report_json")
        result["next_step"] = "渲染 → render_report.py 输出最终交付件"

    # --- delivery html ---
    delivery_report = find_delivery_report(workdir)
    legacy_report = workdir / "report.html"
    if delivery_report or legacy_report.is_file():
        result["completed_steps"].append("report")
        result["next_step"] = "流程完成;重做某步请删对应检查点文件后重跑 recovery_check"
        result["status"] = "completed"
        result["delivery_report"] = str(delivery_report or legacy_report)

    if result["completed_steps"] and result["status"] != "completed":
        result["status"] = "in_progress"

    result["missing_artifacts"] = audit_missing_artifacts(workdir, result.get("paradigm"))

    return result


def format_status_for_user(status: dict) -> str:
    """给模型/用户用的友好展示。"""
    if status["status"] == "fresh":
        return "全新启动,从 Step 0 开始。请先 init_run_dir 或创建 过程稿/ 并写入 00-research-goal.json。"

    if status["status"] == "completed":
        lines = [
            "流程已完成。",
            f"交付报告: {status.get('delivery_report', '(未知)')}",
            "如需重做: 删除对应检查点 JSON 后重跑 recovery_check。",
        ]
        missing = status.get("missing_artifacts") or []
        warnings = [m for m in missing if m.get("kind") == "warning"]
        if warnings:
            lines.append("⚠ 续跑风险:")
            for w in warnings:
                lines.append(f"  - {w['path']}: {w['hint']}")
        return "\n".join(lines)

    completed_labels = {
        "research_goal": "✓ 研究目标 (00)",
        "paradigm": "✓ 范式 (01)",
        "classification": "✓ 分类 (02)",
        "field_alignment": "✓ 字段对齐 (03)",
        "extracted": "✓ 单文档抽取 (extracted/)",
        "extracted_partial": "△ 抽取未完成",
        "personas": "✓ 合并 (04)",
        "report_json": "✓ 组件 JSON (05)",
        "report": "✓ HTML 已交付",
    }

    lines = ["当前进度:"]
    for step in status["completed_steps"]:
        lines.append(completed_labels.get(step, f"✓ {step}"))
    if status.get("processed_count") or status.get("extracted_count"):
        lines.append(
            f"访谈文件: processed {status.get('processed_count', 0)} · "
            f"extracted {status.get('extracted_count', 0)}"
        )
    lines.append(f"下一步: {status['next_step']}")

    missing = [m for m in (status.get("missing_artifacts") or []) if m.get("kind") != "warning"]
    if missing:
        lines.append("")
        lines.append("缺漏检查点(须补全才能可靠续跑):")
        for item in missing:
            lines.append(f"  - {item['path']}: {item['hint']}")

    if status.get("field_alignment_errors"):
        lines.append("")
        lines.append("03-field-alignment 校验未过:")
        for err in status["field_alignment_errors"][:5]:
            lines.append(f"  - {err}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workdir",
        default=OUTPUT_ROOT_NAME,
        help=f"项目运行目录或过程稿目录,默认 {OUTPUT_ROOT_NAME}/",
    )
    parser.add_argument(
        "--format",
        choices=["json", "human"],
        default="json",
        help="输出格式",
    )
    args = parser.parse_args()

    workdir = resolve_process_dir(Path(args.workdir))
    status = check_recovery(workdir)

    if args.format == "json":
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(format_status_for_user(status))


if __name__ == "__main__":
    main()
