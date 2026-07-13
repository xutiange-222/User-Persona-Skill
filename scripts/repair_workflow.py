#!/usr/bin/env python3
"""Official, non-destructive recovery actions for the persona workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from scripts.path_utils import resolve_process_dir
    from scripts.render_checkpoint_md import render_journeys_md, render_personas_md
    from scripts.checkpoint_hash import md_sha256_file
    from scripts.reduced_snapshots import persist_persona_snapshots
except ImportError:
    from path_utils import resolve_process_dir
    from render_checkpoint_md import render_journeys_md, render_personas_md
    from checkpoint_hash import md_sha256_file
    from reduced_snapshots import persist_persona_snapshots


CHECKPOINTS = (
    "00-research-goal", "01-paradigm", "02-classification", "03-field-alignment",
    "04-personas", "04-journeys", "05-report",
)
BUILDER_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ps1", ".bat", ".cmd", ".sh", ".html"}


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _archive_dir(process_dir: Path, label: str) -> Path:
    target = process_dir / "历史版本" / f"{_timestamp()}-{label}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def quarantine_builders(process_dir: Path) -> dict:
    files = [p for p in process_dir.iterdir() if p.is_file() and p.suffix.lower() in BUILDER_SUFFIXES]
    if not files:
        return {"changed": False, "message": "没有需要隔离的一次性脚本。"}
    target = _archive_dir(process_dir, "临时脚本隔离")
    for path in files:
        shutil.move(str(path), str(target / path.name))
    return {"changed": True, "moved": [p.name for p in files], "archive": str(target)}


def refresh_04_md(process_dir: Path, stem: str) -> dict:
    if stem not in {"04-personas", "04-journeys"}:
        raise ValueError("refresh-04-md only supports 04-personas or 04-journeys")
    final_path = process_dir / f"{stem}.json"
    draft_path = process_dir / f"{stem}.draft.json"
    source = final_path if final_path.is_file() else draft_path
    if not source.is_file():
        raise FileNotFoundError(f"Missing {final_path.name} and {draft_path.name}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if stem == "04-personas":
        custom = {}
        alignment = process_dir / "03-field-alignment.json"
        if alignment.is_file():
            custom = json.loads(alignment.read_text(encoding="utf-8")).get("fields_display_names") or {}
        md = render_personas_md(data, custom).rstrip() + "\n"
        reduced_written = persist_persona_snapshots(data, process_dir)
    else:
        try:
            from scripts.validate_evidence_traceability import validate_journey_data_evidence
        except ImportError:
            from validate_evidence_traceability import validate_journey_data_evidence
        evidence_errors = validate_journey_data_evidence(data, process_dir)
        if evidence_errors:
            raise ValueError(
                "04-journeys 草稿含无法回到 processed 原文的证据。先修复全部证据，再生成用户确认稿："
                + json.dumps(evidence_errors, ensure_ascii=False)
            )
        if source == final_path and data.get("user_confirmed") is True:
            try:
                from scripts.validate_journey_checkpoint import build_presentation_review
                from scripts.journey_alignment import expected_alignment_review
            except ImportError:
                from validate_journey_checkpoint import build_presentation_review
                from journey_alignment import expected_alignment_review
            data["presentation_review"] = build_presentation_review(data)
            data["alignment_review"] = expected_alignment_review(data)
        md = render_journeys_md(data).rstrip() + "\n"
        reduced_written = []
    md_path = process_dir / f"{stem}.md"
    md_path.write_text(md, encoding="utf-8", newline="\n")
    if source == final_path and data.get("user_confirmed") is True:
        data["alignment_md_sha256"] = md_sha256_file(md_path)
        final_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"changed": True, "source": str(source), "md": str(md_path), "reduced_written": reduced_written, "hash_rebound": source == final_path and data.get("user_confirmed") is True}


def archive_downstream(process_dir: Path, stem: str) -> dict:
    if stem not in CHECKPOINTS:
        raise ValueError(f"Unknown checkpoint {stem!r}")
    start = CHECKPOINTS.index(stem)
    target = _archive_dir(process_dir, f"从-{stem}-回退")
    moved: list[str] = []
    for downstream in CHECKPOINTS[start:]:
        for suffix in (".md", ".json", ".draft.json"):
            path = process_dir / f"{downstream}{suffix}"
            if path.is_file():
                shutil.move(str(path), str(target / path.name))
                moved.append(path.name)
    return {"changed": bool(moved), "moved": moved, "archive": str(target), "resume_from": stem}


def reopen_04_for_edit(process_dir: Path, stem: str) -> dict:
    """Reopen a sealed 04 checkpoint without losing its confirmed version."""
    if stem not in {"04-personas", "04-journeys"}:
        raise ValueError("reopen-04 only supports 04-personas or 04-journeys")
    final_path = process_dir / f"{stem}.json"
    if not final_path.is_file():
        raise FileNotFoundError(final_path)
    data = json.loads(final_path.read_text(encoding="utf-8"))
    target = _archive_dir(process_dir, f"{stem}-重新编辑")
    start = CHECKPOINTS.index(stem)
    moved: list[str] = []
    for checkpoint in CHECKPOINTS[start:]:
        for suffix in (".md", ".json", ".draft.json"):
            path = process_dir / f"{checkpoint}{suffix}"
            if path.is_file():
                shutil.move(str(path), str(target / path.name))
                moved.append(path.name)

    data["status"] = "draft"
    data["user_confirmed"] = False
    data["confirmation_message_summary"] = ""
    data["confirmation_user_message"] = ""
    data["confirmed_value_sections"] = []
    data.pop("alignment_md_sha256", None)
    draft_path = process_dir / f"{stem}.draft.json"
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_result = refresh_04_md(process_dir, stem)
    return {
        "changed": True,
        "archive": str(target),
        "moved": moved,
        "draft": str(draft_path),
        "md": md_result["md"],
        "resume_from": stem,
        "requires_user_confirmation": True,
    }


def _privacy_error_exists(process_dir: Path) -> bool:
    try:
        from scripts.privacy_guard import validate_privacy_in_html
    except ImportError:
        try:
            from privacy_guard import validate_privacy_in_html
        except ImportError:
            return True
    for path in process_dir.glob("*.md"):
        try:
            if validate_privacy_in_html(path.read_text(encoding="utf-8"), process_dir):
                return True
        except Exception:
            return True
    return False


def create_recovery_bundle(process_dir: Path) -> dict:
    if _privacy_error_exists(process_dir):
        raise RuntimeError("Privacy scan did not pass; recovery bundle was not created.")
    run_dir = process_dir.parent if process_dir.name == "过程稿" else process_dir
    target = run_dir / f"恢复交付件-{_timestamp()}"
    target.mkdir(parents=True, exist_ok=False)
    copied: list[str] = []
    unresolved: list[str] = []
    for stem in CHECKPOINTS:
        md_path = process_dir / f"{stem}.md"
        json_path = process_dir / f"{stem}.json"
        if not md_path.is_file() or not json_path.is_file():
            unresolved.append(f"{stem} 缺少 MD/JSON 配对")
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            unresolved.append(f"{stem}.json 无法解析")
            continue
        target_data = data.get("metadata") if stem == "05-report" else data
        target_data = target_data if isinstance(target_data, dict) else {}
        expected = target_data.get("alignment_md_sha256")
        actual = md_sha256_file(md_path)
        if expected and expected != actual:
            unresolved.append(f"{stem} 的 MD 与 JSON 哈希不一致")
            continue
        shutil.copy2(md_path, target / md_path.name)
        shutil.copy2(json_path, target / json_path.name)
        copied.extend([md_path.name, json_path.name])
    notice = [
        "# 恢复交付说明", "",
        "本目录保存已经配对且可独立交接的过程稿。它不表示最终 HTML 已完成。", "",
        "## 已保存文件", "",
    ] + [f"- {name}" for name in copied] + ["", "## 尚未解决", ""] + ([f"- {item}" for item in unresolved] or ["- 无"])
    (target / "恢复说明.md").write_text("\n".join(notice) + "\n", encoding="utf-8")
    return {"created": str(target), "copied": copied, "unresolved": unresolved}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an official, non-destructive workflow recovery action.")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--action", required=True, choices=["quarantine-builders", "refresh-04-md", "archive-downstream", "reopen-04", "create-recovery-bundle"])
    parser.add_argument("--stem")
    args = parser.parse_args()
    process_dir = resolve_process_dir(Path(args.workdir))
    if args.action == "quarantine-builders":
        result = quarantine_builders(process_dir)
    elif args.action == "refresh-04-md":
        result = refresh_04_md(process_dir, str(args.stem or ""))
    elif args.action == "archive-downstream":
        result = archive_downstream(process_dir, str(args.stem or ""))
    elif args.action == "reopen-04":
        result = reopen_04_for_edit(process_dir, str(args.stem or ""))
    else:
        result = create_recovery_bundle(process_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
