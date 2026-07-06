#!/usr/bin/env python3
"""Validate paired MD/JSON checkpoints for the persona workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir


CLASSIFICATION_PARADIGMS = {"R3", "R4", "R5"}

CHECKPOINTS = (
    ("00-research-goal", True),
    ("01-paradigm", True),
    ("02-classification", False),
    ("03-field-alignment", True),
    ("04-personas", True),
    ("05-report", True),
)


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _needs_02(process_dir: Path) -> bool:
    paradigm_data = _load_json(process_dir / "01-paradigm.json")
    return str(paradigm_data.get("paradigm") or "") in CLASSIFICATION_PARADIGMS


def _find_delivery_report(process_dir: Path) -> Path | None:
    run_dir = process_dir.parent if process_dir.name == "过程稿" else process_dir
    if not run_dir.exists():
        return None
    candidates: list[Path] = []
    for child in run_dir.iterdir():
        if child.is_dir() and child.name.startswith("最终交付件-"):
            report = child / "report.html"
            if report.exists():
                candidates.append(report)
    legacy = process_dir / "report.html"
    if legacy.exists():
        candidates.append(legacy)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def validate_checkpoint_pairing(process_dir: Path) -> list[dict]:
    errors: list[dict] = []
    needs_02 = _needs_02(process_dir)

    for stem, always_required in CHECKPOINTS:
        if stem == "02-classification" and not (always_required or needs_02):
            continue
        md_path = process_dir / f"{stem}.md"
        json_path = process_dir / f"{stem}.json"
        if md_path.exists() and not json_path.exists():
            errors.append(
                {
                    "code": "CHECKPOINT_JSON_MISSING",
                    "path": json_path.name,
                    "message": f"{md_path.name} exists but {json_path.name} is missing.",
                }
            )
        if json_path.exists() and not md_path.exists():
            errors.append(
                {
                    "code": "CHECKPOINT_MD_MISSING",
                    "path": md_path.name,
                    "message": f"{json_path.name} exists but {md_path.name} is missing.",
                }
            )
        if always_required and not md_path.exists() and not json_path.exists():
            errors.append(
                {
                    "code": "CHECKPOINT_PAIR_MISSING",
                    "path": stem,
                    "message": f"{stem}.md and {stem}.json are both missing.",
                }
            )

    report_json = process_dir / "05-report.json"
    prereq_stems = ["00-research-goal", "01-paradigm", "03-field-alignment", "04-personas"]
    if report_json.exists():
        for stem in prereq_stems:
            if not (process_dir / f"{stem}.json").exists():
                errors.append(
                    {
                        "code": "FINAL_WITHOUT_PREREQ",
                        "path": report_json.name,
                        "message": f"05-report.json exists before {stem}.json.",
                    }
                )

    delivery = _find_delivery_report(process_dir)
    if delivery and not report_json.exists():
        errors.append(
            {
                "code": "HTML_WITHOUT_REPORT_JSON",
                "path": str(delivery),
                "message": "Final report.html exists but 05-report.json is missing.",
            }
        )

    processed_dir = process_dir / "processed"
    extracted_dir = process_dir / "extracted"
    processed = list(processed_dir.glob("*.txt")) if processed_dir.is_dir() else []
    extracted = list(extracted_dir.glob("*.json")) if extracted_dir.is_dir() else []
    if processed and len(extracted) != len(processed):
        errors.append(
            {
                "code": "PROCESSED_EXTRACTED_COUNT_MISMATCH",
                "path": "processed/ extracted/",
                "message": f"processed has {len(processed)} txt files, extracted has {len(extracted)} json files.",
                "processed_count": len(processed),
                "extracted_count": len(extracted),
            }
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required MD/JSON checkpoint pairs.")
    parser.add_argument("--workdir", required=True, help="Run directory or process directory.")
    args = parser.parse_args()

    process_dir = resolve_process_dir(Path(args.workdir))
    errors = validate_checkpoint_pairing(process_dir)
    payload = {"valid": not errors, "process_dir": str(process_dir), "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
