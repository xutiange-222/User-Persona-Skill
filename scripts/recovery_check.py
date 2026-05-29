#!/usr/bin/env python3
"""
recovery_check.py

扫工作目录,返回当前进度信息。让模型知道从哪一步继续。

调用:
    python recovery_check.py [--workdir PATH]

输出:JSON 格式的进度状态
"""

import argparse
import json
from pathlib import Path

from path_utils import OUTPUT_ROOT_NAME, resolve_process_dir


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


def check_recovery(workdir: Path) -> dict:
    """
    扫工作目录,返回进度状态。

    返回字段:
    - status: "fresh" / "in_progress" / "completed"
    - completed_steps: 已完成的步骤列表
    - next_step: 下一步要做什么
    - paradigm: 范式(若已选)
    - research_type: 研究类型(若已选)
    """
    result = {
        "status": "fresh",
        "completed_steps": [],
        "next_step": "Step 0: 扫文件 + 形成初判",
        "paradigm": None,
        "research_type": None,
        "workdir": str(workdir),
    }

    if not workdir.exists():
        return result

    # Step 0/1: 研究目标
    goal_file = workdir / "00-research-goal.json"
    if goal_file.exists():
        result["completed_steps"].append("research_goal")
        with open(goal_file, "r", encoding="utf-8") as f:
            goal = json.load(f)
            result["research_type"] = goal.get("research_type")
        result["next_step"] = "Step 2: 确认范式"

    # Step 2: 范式选择
    paradigm_file = workdir / "01-paradigm.json"
    if paradigm_file.exists():
        result["completed_steps"].append("paradigm")
        with open(paradigm_file, "r", encoding="utf-8") as f:
            paradigm = json.load(f)
            result["paradigm"] = paradigm.get("paradigm")

        # R1/R2 直接到字段对齐
        if result["paradigm"] in ["R1", "R2"]:
            result["next_step"] = "字段对齐"
        # R3/R4/R5 需要分类阶段
        else:
            result["next_step"] = (
                "分类依据" if result["paradigm"] == "R3" else "价值变量推荐"
            )

    # R3/R4/R5: 分类
    classification_file = workdir / "02-classification.json"
    if classification_file.exists():
        result["completed_steps"].append("classification")
        result["next_step"] = "字段对齐"

    # 字段对齐(须通过硬门禁才算完成)
    field_candidates = [
        workdir / "03-field-alignment.json",
        workdir / "过程稿" / "03-field-alignment.json",
    ]
    if resolve_process_dir is not None:
        try:
            proc = resolve_process_dir(workdir)
            field_candidates.insert(0, proc / "03-field-alignment.json")
        except Exception:
            pass
    field_file = next((p for p in field_candidates if p.is_file()), None)
    if field_file is not None:
        try:
            from scripts.validate_field_alignment import (
                load_field_alignment,
                validate_field_alignment,
            )

            fa_errors = validate_field_alignment(load_field_alignment(field_file))
        except Exception as exc:
            fa_errors = [str(exc)]
        if fa_errors:
            result["field_alignment_incomplete"] = True
            result["field_alignment_errors"] = fa_errors
            result["next_step"] = "字段对齐(未完成:须展示字段池并获用户确认)"
        else:
            result["completed_steps"].append("field_alignment")
            result["next_step"] = "单文档抽取"

    # 抽取产物
    extracted_dir = workdir / "extracted"
    processed_dir = workdir / "processed"

    if extracted_dir.exists() and processed_dir.exists():
        extracted_files = list(extracted_dir.glob("*.json"))
        processed_files = list(processed_dir.glob("*.txt"))

        if len(extracted_files) >= len(processed_files) and len(extracted_files) > 0:
            result["completed_steps"].append("extracted")
            result["next_step"] = "多份合并"
        elif len(extracted_files) > 0:
            result["completed_steps"].append("extracted_partial")
            result["next_step"] = (
                f"完成单文档抽取(已 {len(extracted_files)}/{len(processed_files)})"
            )

    # 合并产物
    personas_file = workdir / "04-personas.json"
    if personas_file.exists():
        result["completed_steps"].append("personas")
        result["next_step"] = "渲染 HTML"

    # 渲染产物。兼容旧过程稿/report.html,优先识别最终交付件-*/report.html。
    report_file = workdir / "report.html"
    delivery_report = find_delivery_report(workdir)
    if delivery_report:
        result["completed_steps"].append("report")
        result["next_step"] = "流程完成"
        result["status"] = "completed"
        result["delivery_report"] = str(delivery_report)
    elif report_file.exists():
        result["completed_steps"].append("report")
        result["next_step"] = "流程完成"
        result["status"] = "completed"
        result["delivery_report"] = str(report_file)

    if result["completed_steps"] and result["status"] != "completed":
        result["status"] = "in_progress"

    return result


def format_status_for_user(status: dict) -> str:
    """
    给模型用的友好展示。
    """
    if status["status"] == "fresh":
        return "全新启动,从 Step 0 开始。"

    if status["status"] == "completed":
        return "流程已完成,report.html 在工作目录。如需重做某一步,删对应的 JSON 文件。"

    completed_labels = {
        "research_goal": "✓ 研究目标已确认",
        "paradigm": "✓ 范式已确认",
        "classification": "✓ 分类(分类依据/价值变量)已确认",
        "field_alignment": "✓ 字段对齐已完成",
        "extracted": "✓ 单文档抽取已完成",
        "extracted_partial": "△ 单文档抽取部分完成",
        "personas": "✓ 合并已完成",
        "report": "✓ 渲染已完成",
    }

    lines = ["当前进度:"]
    for step in status["completed_steps"]:
        lines.append(completed_labels.get(step, f"✓ {step}"))
    lines.append(f"下一步:{status['next_step']}")
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
