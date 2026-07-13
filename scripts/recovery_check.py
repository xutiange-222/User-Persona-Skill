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

from path_utils import OUTPUT_ROOT_NAME, artifact_keys, iter_artifacts, resolve_process_dir

CHECKPOINT_FILES = (
    ("00-research-goal", "research_goal", "Step 0/1: 写入研究目标 MD 和 JSON"),
    ("01-paradigm", "paradigm", "Step 2: 写入范式选择 MD 和 JSON"),
    ("02-classification", "classification", "分类/区分点: 写入 02-classification.md/json"),
    ("03-field-alignment", "field_alignment", "字段对齐: 写入并校验 03-field-alignment.md/json"),
    ("04-personas", "personas", "合并: 写入 04-personas.md/json"),
    ("04-journeys", "journeys", "旅程确认: 写入并校验 04-journeys.md/json"),
    ("05-report", "report_json", "渲染前: 写入 05-report.md/json"),
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


def _validate_checkpoint_pairing(process_dir: Path) -> list[dict]:
    try:
        try:
            from validate_checkpoint_pairing import validate_checkpoint_pairing
        except ImportError:
            from scripts.validate_checkpoint_pairing import validate_checkpoint_pairing

        return validate_checkpoint_pairing(
            process_dir,
            require_complete=(process_dir / "05-report.json").is_file(),
        )
    except Exception as exc:
        return [
            {
                "code": "CHECKPOINT_VALIDATOR_ERROR",
                "path": str(process_dir),
                "message": str(exc),
            }
        ]


def _validate_downstream_artifacts(process_dir: Path, delivery: Path | None) -> list[dict]:
    """Validate report components, journey equality and delivered HTML for recovery."""
    errors: list[dict] = []
    report_path = process_dir / "05-report.json"
    if report_path.is_file():
        report = _load_json(report_path)
        if report is not None:
            try:
                from scripts.components.validate import validate_report_json
                for item in validate_report_json(report, process_dir):
                    if item.get("level") == "ERROR":
                        errors.append({
                            "code": item.get("code", "REPORT_VALIDATION_ERROR"),
                            "path": item.get("path") or "05-report.json",
                            "message": item.get("message", "05-report.json 校验失败"),
                        })
            except Exception as exc:
                errors.append({"code": "REPORT_VALIDATOR_ERROR", "path": "05-report.json", "message": str(exc)})
            try:
                from scripts.validate_journey_checkpoint import validate_journey_checkpoint
                errors.extend(validate_journey_checkpoint(process_dir))
            except Exception as exc:
                errors.append({"code": "JOURNEY_VALIDATOR_ERROR", "path": "04-journeys.json", "message": str(exc)})

    if delivery is not None and delivery.is_file():
        for required_name in ("_design-tokens.css", "_components.css", "交付件说明.md"):
            required = delivery.parent / required_name
            if not required.is_file():
                errors.append({
                    "code": "DELIVERY_FILE_MISSING",
                    "path": str(required),
                    "message": f"最终交付目录缺少 {required_name}。",
                })
        try:
            from scripts.validate_html import run_validation
            html_report = run_validation(delivery, process_dir.parent)
            for item in html_report.errors:
                errors.append({
                    "code": item.code,
                    "path": str(delivery),
                    "message": item.message,
                })
        except Exception as exc:
            errors.append({"code": "HTML_VALIDATOR_ERROR", "path": str(delivery), "message": str(exc)})
    return errors


def audit_missing_artifacts(process_dir: Path, paradigm: str | None) -> list[dict]:
    """List checkpoint files/dirs that should exist but do not."""
    missing: list[dict] = []

    for stem, _step_id, hint in CHECKPOINT_FILES:
        md_path = process_dir / f"{stem}.md"
        json_path = process_dir / f"{stem}.json"
        if not md_path.is_file() and not json_path.is_file():
            missing.append(
                {
                    "kind": "checkpoint_pair",
                    "path": f"{stem}.json",
                    "hint": hint,
                }
            )
            continue
        if not md_path.is_file():
            missing.append(
                {
                    "kind": "checkpoint_md",
                    "path": md_path.name,
                    "hint": f"缺少用户对齐稿 {md_path.name},不得只保留 JSON",
                }
            )
        if not json_path.is_file():
            missing.append(
                {
                    "kind": "checkpoint_json",
                    "path": json_path.name,
                    "hint": f"缺少系统续跑稿 {json_path.name},不得只保留 MD",
                }
            )

    processed_dir = process_dir / "processed"
    extracted_dir = process_dir / "extracted"
    reduced_dir = process_dir / "reduced"
    processed_files = iter_artifacts(processed_dir, ".txt")
    extracted_files = iter_artifacts(extracted_dir, ".json")
    reduced_files = iter_artifacts(reduced_dir, ".json")

    if not processed_dir.is_dir() or not processed_files:
        missing.append(
            {
                "kind": "dir",
                "path": "processed/*.txt",
                "hint": "预处理: 每份访谈写入 processed/<名>.txt",
            }
        )
    elif len(extracted_files) != len(processed_files):
        missing.append(
            {
                "kind": "dir",
                "path": "extracted/*.json",
                "hint": (
                    f"单文档抽取数量必须一一对应: processed {len(processed_files)} 份,"
                    f"extracted {len(extracted_files)} 份"
                ),
                "extracted_count": len(extracted_files),
                "processed_count": len(processed_files),
            }
        )
    if processed_files or extracted_files:
        processed_stems = artifact_keys(processed_files, processed_dir)
        extracted_stems = artifact_keys(extracted_files, extracted_dir)
        if processed_stems != extracted_stems:
            missing.append(
                {
                    "kind": "artifact_mismatch",
                    "path": "processed/ extracted/",
                    "hint": "processed 与 extracted 文件名主干必须一一对应",
                    "missing_extracted": sorted(processed_stems - extracted_stems),
                    "orphan_extracted": sorted(extracted_stems - processed_stems),
                }
            )
    if (process_dir / "04-personas.json").is_file() and not reduced_files:
        missing.append(
            {
                "kind": "dir",
                "path": "reduced/*.json",
                "hint": "已有 04-personas.json，但缺少逐字段归并产物，无法审计画像如何形成",
            }
        )

    delivery = find_delivery_report(process_dir)
    report_json = process_dir / "05-report.json"
    if report_json.is_file():
        for prereq in (
            "00-research-goal.json",
            "01-paradigm.json",
            "02-classification.json",
            "03-field-alignment.json",
            "04-personas.json",
            "04-journeys.json",
        ):
            if not (process_dir / prereq).is_file():
                missing.append(
                    {
                        "kind": "warning",
                        "path": prereq,
                        "hint": f"已有 05-report.json 但缺少前序检查点 {prereq},疑似跳步输出",
                    }
                )
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

    pairing_errors = _validate_checkpoint_pairing(workdir)
    try:
        from scripts.run_checkpoint_gate import select_blocking_group
    except ImportError:
        from run_checkpoint_gate import select_blocking_group
    blocking_errors = select_blocking_group(pairing_errors)
    invalid_paths = {str(item.get("path") or "") for item in pairing_errors}

    def checkpoint_valid(stem: str) -> bool:
        filename = f"{stem}.json"
        return (workdir / filename).is_file() and filename not in invalid_paths

    # --- 00 research goal ---
    goal_file = workdir / "00-research-goal.json"
    if checkpoint_valid("00-research-goal"):
        result["completed_steps"].append("research_goal")
        goal = _load_json(goal_file) or {}
        result["research_type"] = goal.get("research_type")
        result["next_step"] = "Step 2: 确认范式并写入 01-paradigm.json"

    # --- 01 paradigm ---
    paradigm_file = workdir / "01-paradigm.json"
    if checkpoint_valid("01-paradigm"):
        result["completed_steps"].append("paradigm")
        paradigm_data = _load_json(paradigm_file) or {}
        result["paradigm"] = paradigm_data.get("paradigm")
        result["next_step"] = (
            "分类依据 / 不适用说明 → 02-classification.md 和 02-classification.json"
        )

    # --- 02 classification ---
    classification_file = workdir / "02-classification.json"
    if checkpoint_valid("02-classification"):
        result["completed_steps"].append("classification")
        result["next_step"] = "字段对齐 → 03-field-alignment.json"

    # --- 03 field alignment ---
    field_file = workdir / "03-field-alignment.json"
    if checkpoint_valid("03-field-alignment"):
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
    processed_files = iter_artifacts(processed_dir, ".txt")
    extracted_files = iter_artifacts(extracted_dir, ".json")
    result["processed_count"] = len(processed_files)
    result["extracted_count"] = len(extracted_files)

    if processed_files and extracted_files:
        processed_stems = artifact_keys(processed_files, processed_dir)
        extracted_stems = artifact_keys(extracted_files, extracted_dir)
        if len(extracted_files) == len(processed_files) and processed_stems == extracted_stems:
            result["completed_steps"].append("extracted")
            result["next_step"] = "合并 → 04-personas.json"
        else:
            result["completed_steps"].append("extracted_partial")
            result["next_step"] = (
                f"完成单文档抽取(已 {len(extracted_files)}/{len(processed_files)})"
            )

    # --- 04 personas ---
    personas_file = workdir / "04-personas.json"
    if checkpoint_valid("04-personas"):
        result["completed_steps"].append("personas")
        result["next_step"] = "旅程确认或不适用说明 → 04-journeys.md/json"

    # --- 04 journeys ---
    journeys_file = workdir / "04-journeys.json"
    if checkpoint_valid("04-journeys"):
        result["completed_steps"].append("journeys")
        result["next_step"] = "组装组件 JSON → 05-report.json"

    # --- 05 report json ---
    report_json_file = workdir / "05-report.json"
    if checkpoint_valid("05-report"):
        result["completed_steps"].append("report_json")
        result["next_step"] = "渲染 → render_report.py 输出最终交付件"

    # --- delivery html ---
    delivery_report = find_delivery_report(workdir)
    legacy_report = workdir / "report.html"
    has_delivery = bool(delivery_report or legacy_report.is_file())
    if has_delivery:
        result["completed_steps"].append("report")
        result["delivery_report"] = str(delivery_report or legacy_report)

    has_any_artifact = any(workdir.glob("*.md")) or any(workdir.glob("*.json"))
    if (result["completed_steps"] or has_any_artifact) and result["status"] != "completed":
        result["status"] = "in_progress"

    result["missing_artifacts"] = audit_missing_artifacts(workdir, result.get("paradigm"))
    result["checkpoint_pairing_errors"] = pairing_errors
    result["blocking_errors"] = blocking_errors
    result["checkpoint_pairing_valid"] = not result["checkpoint_pairing_errors"]
    result["checkpoint_complete"] = not any(
        item.get("kind") in {
            "checkpoint_pair",
            "checkpoint_md",
            "checkpoint_json",
            "artifact_mismatch",
            "dir",
            "warning",
        }
        for item in result["missing_artifacts"]
    )

    downstream_errors = _validate_downstream_artifacts(workdir, delivery_report or (legacy_report if legacy_report.is_file() else None))
    result["downstream_validation_errors"] = downstream_errors
    result["downstream_valid"] = not downstream_errors

    if (
        has_delivery
        and result["checkpoint_pairing_valid"]
        and result["checkpoint_complete"]
        and result["downstream_valid"]
    ):
        result["status"] = "completed"
        result["next_step"] = "流程完成;重做某步请删除该步及后续 MD/JSON 后重跑 recovery_check"
    elif has_delivery:
        result["status"] = "in_progress"
        result["next_step"] = "修复检查点、组件、旅程或 HTML 校验错误后重新渲染"
    elif blocking_errors:
        first = blocking_errors[0]
        result["next_step"] = (
            f"只修复 {first.get('code', '当前错误')} / {first.get('path', '最早异常检查点')}: "
            f"{first.get('message', first.get('code', '校验失败'))}"
        )

    return result


def format_status_for_user(status: dict) -> str:
    """给模型/用户用的友好展示。"""
    if status["status"] == "fresh":
        return (
            "全新启动,从 Step 0 开始。请先 init_run_dir 或创建 过程稿/，"
            "填写 00-research-goal.md 给用户确认，再写 00-research-goal.json。"
        )

    if status["status"] == "completed":
        lines = [
            "流程已完成。",
            f"交付报告: {status.get('delivery_report', '(未知)')}",
            "如需重做: 删除对应检查点的 MD 和 JSON，再重跑 recovery_check。",
        ]
        missing = status.get("missing_artifacts") or []
        warnings = [m for m in missing if m.get("kind") == "warning"]
        if warnings:
            lines.append("续跑风险:")
            for w in warnings:
                lines.append(f"  - {w['path']}: {w['hint']}")
        return "\n".join(lines)

    completed_labels = {
        "research_goal": "[完成] 研究目标 (00)",
        "paradigm": "[完成] 范式 (01)",
        "classification": "[完成] 分类 (02)",
        "field_alignment": "[完成] 字段对齐 (03)",
        "extracted": "[完成] 单文档抽取 (extracted/)",
        "extracted_partial": "[未完成] 单文档抽取",
        "personas": "[完成] 画像合并 (04)",
        "journeys": "[完成] 旅程确认 (04)",
        "report_json": "[完成] 组件 JSON (05)",
        "report": "[完成] HTML 已交付",
    }

    lines = ["当前进度:"]
    for step in status["completed_steps"]:
        lines.append(completed_labels.get(step, f"[完成] {step}"))
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

    pairing_errors = status.get("blocking_errors") or status.get("checkpoint_pairing_errors") or []
    if pairing_errors:
        lines.append("")
        lines.append("检查点配对未通过，当前只处理这一类门禁错误:")
        for item in pairing_errors[:5]:
            lines.append(
                f"  - {item.get('code', '?')}: {item.get('path', '?')} | {item.get('message', '')}"
            )
    elif status.get("checkpoint_pairing_valid") is False:
        lines.append("")
        lines.append("检查点配对未通过,请运行 validate_checkpoint_pairing.py 查看详情。")

    downstream_errors = status.get("downstream_validation_errors") or []
    if downstream_errors:
        lines.append("")
        lines.append("下游产物校验未通过:")
        for item in downstream_errors[:8]:
            lines.append(
                f"  - {item.get('code', '?')}: {item.get('path', '?')} | {item.get('message', '')}"
            )

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
