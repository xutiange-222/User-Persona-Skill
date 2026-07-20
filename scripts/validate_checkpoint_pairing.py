#!/usr/bin/env python3
"""Validate paired MD/JSON checkpoints for the persona workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None  # type: ignore

try:
    from scripts.path_utils import artifact_keys, iter_artifacts, resolve_process_dir
    from scripts.checkpoint_hash import md_sha256_text
except ImportError:
    from path_utils import artifact_keys, iter_artifacts, resolve_process_dir
    from checkpoint_hash import md_sha256_text


CHECKPOINTS = (
    "00-research-goal",
    "01-paradigm",
    "02-classification",
    "03-field-alignment",
    "04-personas",
    "04-journeys",
    "05-report",
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates" / "checkpoints"
CHECKPOINT_SCHEMA_PATHS = {
    "00-research-goal": ROOT / "scripts" / "schemas" / "00-research-goal.schema.json",
    "01-paradigm": ROOT / "scripts" / "schemas" / "01-paradigm.schema.json",
    "02-classification": ROOT / "scripts" / "schemas" / "02-classification.schema.json",
    "03-field-alignment": ROOT / "scripts" / "schemas" / "03-field-alignment.schema.json",
    "04-personas": ROOT / "scripts" / "schemas" / "04-personas.schema.json",
    "04-journeys": ROOT / "scripts" / "schemas" / "04-journeys.schema.json",
    "05-report": ROOT / "scripts" / "components" / "schemas" / "report.json",
}
GENERIC_CONFIRMATION_RE = re.compile(
    r"^(?:用户)?(?:已)?确认(?:以上|该|此|全部)?(?:内容|方案|结果)?(?:无误|并同意)?(?:继续|执行)?[。.]?$|^按推荐(?:来|执行)?[。.]?$"
)
CONTENT_STAGE_GENERIC_REPLY_RE = re.compile(
    r"^(?:好|好的|可以|没问题|确认|继续|下一步|开始|开始生成|开始渲染|生成|渲染|"
    r"ok|okay)[。.!！]?$",
    re.IGNORECASE,
)
REJECTION_OR_SKIP_RE = re.compile(
    r"(?:不确认|先不确认|暂不确认|取消确认|别确认|不要确认|跳过确认|"
    r"不看了|看不懂|看得头晕|直接继续|你继续吧)", re.I,
)
CONFIRMED_MD_MARKER = "确认状态：已确认"
PENDING_MD_RE = re.compile(r"(?m)^\s*确认状态\s*[：:]\s*(?:待用户确认|待确认|draft|草稿)\s*$", re.IGNORECASE)
ALIGNMENT_MIN_COVERAGE = 0.80
CONFIRMATION_SECTIONS = {
    "00-research-goal": {"goals", "scope", "constraints", "workspace"},
    "01-paradigm": {"paradigm", "reason", "alternatives", "groups"},
    "02-classification": {"basis", "boundaries", "labels", "respondent_mapping", "groups", "uncertainties"},
    "03-field-alignment": {"fields", "modules", "journey", "visual_assets", "visual_spec"},
    "04-personas": {"names", "persona_values", "evidence", "risks", "information_loss"},
    "04-journeys": {"scope", "stages", "substages", "lanes", "nodes", "edges", "painpoints_or_gaps", "touchpoints", "emotions", "evidence"},
    "05-report": {"page_plan", "modules", "information_loss"},
}
CONFIRMATION_PHRASES = {
    "00-research-goal": "确认研究目标",
    "01-paradigm": "确认画像方式",
    "02-classification": "确认分类内容",
    "03-field-alignment": "确认字段与视觉范围",
    "04-personas": "确认画像内容",
    "04-journeys": "确认旅程内容",
    "05-report": "确认报告结构",
}
_ALIGNMENT_SKIP_KEYS = {
    "id", "persona_id", "checkpoint", "status", "user_confirmed",
    "confirmation_message_summary", "confirmation_user_message",
    "confirmed_value_sections", "alignment_md_sha256", "members",
    "evidence", "evidence_map", "source", "sources", "source_id",
    "source_ids", "source_file", "avatar", "avatar_path", "screenshot",
    "marker_id", "_marker_id", "type", "component_type", "branch", "style",
}


def _normalized_visible_text(value: object) -> str:
    return re.sub(r"[\s`*_#>|：:，,。.!！?？（）()\[\]{}\-_/\\]+", "", str(value)).lower()


def _collect_user_visible_values(value: object, key: str = "") -> list[str]:
    if key.lower() in _ALIGNMENT_SKIP_KEYS or key.lower().endswith(("_id", "_ids", "_path")):
        return []
    if isinstance(value, dict):
        result: list[str] = []
        for child_key, child in value.items():
            result.extend(_collect_user_visible_values(child, str(child_key)))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(_collect_user_visible_values(child, key))
        return result
    if not isinstance(value, str):
        return []
    text = value.strip()
    normalized = _normalized_visible_text(text)
    if len(normalized) < 2 or len(normalized) > 240:
        return []
    if re.fullmatch(r"P[0-9A-F]{8}", text) or re.match(r"^[a-z]+://", text, re.I):
        return []
    return [text]


def _alignment_coverage(stem: str, data: dict, md_text: str) -> tuple[float, list[str], int]:
    if stem == "00-research-goal":
        root = {key: data.get(key) for key in (
            "audience", "research_question", "decision_use", "research_type",
            "source_count", "constraints", "workspace_notice",
        )}
    elif stem == "01-paradigm":
        root = {key: data.get(key) for key in (
            "context_snapshot", "paradigm", "reason", "alternatives_considered",
            "known_groups", "choice_label", "choice_reason",
        )}
    elif stem == "02-classification":
        root = {key: data.get(key) for key in (
            "context_snapshot", "not_applicable_reason", "classification_basis",
            "boundary_rules", "evidence_summary", "uncertainties", "groups",
            "respondent_mapping", "value_variables", "axes", "empty_groups",
        )}
    elif stem == "03-field-alignment":
        root = {key: data.get(key) for key in (
            "context_snapshot", "fields_display_names", "fields_per_persona",
            "custom_fields", "add_on_pages", "visual_assets", "visual_spec",
        )}
    elif stem == "04-personas":
        root = data.get("personas")
    elif stem == "04-journeys":
        root = data.get("journeys")
    else:
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        root = {
            "report_title": metadata.get("report_title"),
            "page_count": metadata.get("page_count"),
            "visual_spec": metadata.get("visual_spec"),
            "field_coverage": metadata.get("field_coverage"),
            "personas": data.get("personas"),
        }
    values = _collect_user_visible_values(root)
    unique: dict[str, str] = {}
    for value in values:
        normalized = _normalized_visible_text(value)
        if normalized:
            unique.setdefault(normalized, value)
    md_normalized = _normalized_visible_text(md_text)
    missing = [original for normalized, original in unique.items() if normalized not in md_normalized]
    total = len(unique)
    covered = total - len(missing)
    return (covered / total if total else 0.0), missing, total


def _load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _schema_errors(stem: str, data: dict) -> list[str]:
    path = CHECKPOINT_SCHEMA_PATHS[stem]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"checkpoint schema unavailable: {exc}"]
    if Draft202012Validator is None:
        try:
            from scripts._jsonschema_fallback import validate
            validate(instance=data, schema=schema)
            return []
        except Exception as exc:  # pragma: no cover
            return [str(exc)]
    return [
        f"{'.'.join(str(part) for part in err.absolute_path) or '$'}: {err.message}"
        for err in Draft202012Validator(schema).iter_errors(data)
    ]


def _cross_checkpoint_errors(parsed: dict[str, dict], processed_count: int, source_counts: dict | None = None) -> list[dict]:
    errors: list[dict] = []

    def add(code: str, path: str, message: str) -> None:
        errors.append({"code": code, "path": path, "message": message})

    goal = parsed.get("00-research-goal") or {}
    paradigm = parsed.get("01-paradigm") or {}
    classification = parsed.get("02-classification") or {}
    alignment = parsed.get("03-field-alignment") or {}
    personas = parsed.get("04-personas") or {}
    journeys = parsed.get("04-journeys") or {}
    report = parsed.get("05-report") or {}

    base_context = {
        "research_question": goal.get("research_question"),
        "decision_use": goal.get("decision_use"),
        "research_type": goal.get("research_type"),
    }
    paradigm_context = {**base_context, "paradigm": paradigm.get("paradigm")}
    for stem, data, expected in (
        ("01-paradigm", paradigm, base_context),
        ("02-classification", classification, paradigm_context),
        ("03-field-alignment", alignment, paradigm_context),
        ("04-personas", personas, paradigm_context),
        ("04-journeys", journeys, paradigm_context),
    ):
        if data and data.get("context_snapshot") != expected:
            add("CHECKPOINT_CONTEXT_DRIFT", f"{stem}.json", f"context_snapshot must exactly preserve {expected!r}.")

    research_type = goal.get("research_type")
    for stem, data in (("01-paradigm", paradigm), ("03-field-alignment", alignment)):
        other = data.get("research_type")
        if research_type and other and other != research_type:
            add("CHECKPOINT_RESEARCH_TYPE_MISMATCH", f"{stem}.json", f"research_type={other!r} differs from 00-research-goal.json {research_type!r}.")

    mode = paradigm.get("paradigm")
    class_status = classification.get("status")
    if mode in {"R1", "R2"} and class_status and class_status != "not_applicable":
        add("CHECKPOINT_CLASSIFICATION_STATUS_MISMATCH", "02-classification.json", f"{mode} requires status=not_applicable.")
    if mode in {"R3", "R4", "R5"}:
        if class_status not in {"confirmed", "validated"}:
            add("CHECKPOINT_CLASSIFICATION_STATUS_MISMATCH", "02-classification.json", f"{mode} requires confirmed classification data.")
        if classification.get("label_confirmed") is not True:
            add("CHECKPOINT_LABEL_NOT_CONFIRMED", "02-classification.json", f"{mode} requires label_confirmed=true.")

    persona_items = personas.get("personas")
    persona_count = personas.get("persona_count")
    if isinstance(persona_items, list) and isinstance(persona_count, int) and persona_count != len(persona_items):
        add("CHECKPOINT_PERSONA_COUNT_MISMATCH", "04-personas.json", f"persona_count={persona_count} but personas has {len(persona_items)} items.")
    aligned_count = alignment.get("persona_count")
    if isinstance(aligned_count, int) and isinstance(persona_count, int) and aligned_count != persona_count:
        add("CHECKPOINT_PERSONA_COUNT_MISMATCH", "03-field-alignment.json", f"persona_count={aligned_count} differs from 04-personas.json {persona_count}.")

    if isinstance(persona_items, list):
        persona_ids = [str(item.get("id") or "") for item in persona_items if isinstance(item, dict)]
        if len(persona_ids) != len(set(persona_ids)):
            add("CHECKPOINT_PERSONA_ID_DUPLICATE", "04-personas.json", "personas[].id must be unique.")
        report_items = report.get("personas") if isinstance(report.get("personas"), list) else []
        report_base: dict[str, str] = {}
        report_names: dict[str, set[str]] = {}
        for item in report_items:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or "")
            if pid in {"matrix", "distribution", "journey-l1"}:
                continue
            base_id = re.sub(r"-(?:detail(?:-\d+)?|journey|core)$", "", pid)
            if base_id.startswith("persona-"):
                name = str(item.get("name") or "")
                report_base.setdefault(base_id, name)
                report_names.setdefault(base_id, set()).add(name)
        for base_id, names in report_names.items():
            if len(names) > 1:
                add("CHECKPOINT_PERSONA_NAME_DRIFT", "05-report.json", f"{base_id} uses multiple names across portrait/detail/journey pages: {sorted(names)}.")
        confirmed_map = {
            str(item.get("id") or ""): str(item.get("name") or "")
            for item in persona_items if isinstance(item, dict)
        }
        if report and confirmed_map and report_base != confirmed_map:
            add(
                "CHECKPOINT_PERSONA_REPORT_MISMATCH",
                "05-report.json",
                f"05 base persona id/name map {report_base!r} differs from 04-personas.json {confirmed_map!r}.",
            )

    unique_primary = (source_counts or {}).get("unique_primary_interviews")
    expected_sources = unique_primary if isinstance(unique_primary, int) else processed_count
    goal_sources = goal.get("source_count")
    if expected_sources and isinstance(goal_sources, int) and goal_sources != expected_sources:
        add("CHECKPOINT_SOURCE_COUNT_MISMATCH", "00-research-goal.json", f"source_count={goal_sources} but unique primary interviews={expected_sources}.")
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    if report and metadata.get("context_snapshot") != paradigm_context:
        add("CHECKPOINT_CONTEXT_DRIFT", "05-report.json", "metadata.context_snapshot differs from confirmed 00/01 context.")
    report_sources = metadata.get("source_count")
    if expected_sources and isinstance(report_sources, int) and report_sources != expected_sources:
        add("CHECKPOINT_SOURCE_COUNT_MISMATCH", "05-report.json", f"metadata.source_count={report_sources} but unique primary interviews={expected_sources}.")
    if source_counts and metadata.get("source_summary") != source_counts:
        add("CHECKPOINT_SOURCE_SUMMARY_MISMATCH", "05-report.json", "metadata.source_summary must exactly match source-manifest.json counts.")
    report_personas = metadata.get("persona_count")
    if isinstance(report_personas, int) and isinstance(persona_count, int) and report_personas != persona_count:
        add("CHECKPOINT_PERSONA_COUNT_MISMATCH", "05-report.json", f"metadata.persona_count={report_personas} differs from 04-personas.json {persona_count}.")
    expected_theme = {"toB": "2b", "toC": "2c", "toD": "2d"}.get(str(research_type))
    if expected_theme and metadata.get("theme") and metadata.get("theme") != expected_theme:
        add("CHECKPOINT_THEME_MISMATCH", "05-report.json", f"metadata.theme={metadata.get('theme')!r} must be {expected_theme!r} for {research_type}.")
    return errors


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


def validate_checkpoint_pairing(
    process_dir: Path,
    *,
    require_complete: bool = False,
) -> list[dict]:
    errors: list[dict] = []
    source_counts: dict | None = None
    if require_complete:
        try:
            from scripts.validate_source_manifest import validate_source_manifest
        except ImportError:
            from validate_source_manifest import validate_source_manifest
        errors.extend(validate_source_manifest(process_dir))
        manifest = _load_json(process_dir / "source-manifest.json") or {}
        if isinstance(manifest.get("counts"), dict):
            source_counts = manifest["counts"]
    try:
        from scripts.validate_terminology import validate_terminology
        from scripts.validate_persona_checkpoint import validate_persona_checkpoint
        from scripts.validate_evidence_contract import validate_evidence_contract
        from scripts.validate_paradigm_contract import validate_paradigm_contract
        from scripts.validate_content_completeness import validate_content_completeness
        from scripts.validate_evidence_traceability import validate_evidence_traceability
        from scripts.validate_language_quality import validate_language_quality
        from scripts.validate_human_checkpoint_md import validate_human_checkpoint_md
    except ImportError:
        from validate_terminology import validate_terminology
        from validate_persona_checkpoint import validate_persona_checkpoint
        from validate_evidence_contract import validate_evidence_contract
        from validate_paradigm_contract import validate_paradigm_contract
        from validate_content_completeness import validate_content_completeness
        from validate_evidence_traceability import validate_evidence_traceability
        from validate_language_quality import validate_language_quality
        from validate_human_checkpoint_md import validate_human_checkpoint_md
    for validator in (
        validate_terminology,
        validate_persona_checkpoint,
        validate_evidence_contract,
        validate_paradigm_contract,
        validate_content_completeness,
        validate_evidence_traceability,
        validate_language_quality,
        validate_human_checkpoint_md,
    ):
        try:
            errors.extend(validator(process_dir))
        except Exception as exc:
            errors.append({
                "code": "VALIDATOR_RUNTIME_ERROR",
                "path": validator.__name__,
                "message": f"校验器运行失败：{exc}。先修复该校验器输入契约，禁止绕过或继续渲染。",
            })
    presence = [
        (process_dir / f"{stem}.md").exists()
        or (process_dir / f"{stem}.json").exists()
        for stem in CHECKPOINTS
    ]
    highest_present = max((idx for idx, value in enumerate(presence) if value), default=-1)

    parsed: dict[str, dict] = {}
    for idx, stem in enumerate(CHECKPOINTS):
        required = require_complete or idx <= highest_present
        md_path = process_dir / f"{stem}.md"
        json_path = process_dir / f"{stem}.json"
        md_text = ""
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
        if required and not md_path.exists() and not json_path.exists():
            errors.append(
                {
                    "code": "CHECKPOINT_PAIR_MISSING",
                    "path": stem,
                    "message": f"{stem}.md and {stem}.json are both missing.",
                }
            )
        if md_path.exists():
            try:
                md_text = md_path.read_text(encoding="utf-8").strip()
            except OSError:
                md_text = ""
            if len(md_text) < 20:
                errors.append(
                    {
                        "code": "CHECKPOINT_MD_EMPTY",
                        "path": md_path.name,
                        "message": f"{md_path.name} is empty or too short to support user alignment.",
                    }
                )
            template_path = TEMPLATE_DIR / md_path.name
            if template_path.is_file():
                template_text = template_path.read_text(encoding="utf-8").strip()
                if md_text == template_text:
                    errors.append(
                        {
                            "code": "CHECKPOINT_MD_UNFILLED_TEMPLATE",
                            "path": md_path.name,
                            "message": f"{md_path.name} is still the unfilled bundled template.",
                        }
                    )
        if json_path.exists():
            data = _load_json(json_path)
            if data is None:
                errors.append(
                    {
                        "code": "CHECKPOINT_JSON_INVALID",
                        "path": json_path.name,
                        "message": f"{json_path.name} is not a valid JSON object.",
                    }
                )
            else:
                parsed[stem] = data
                for message in _schema_errors(stem, data):
                    errors.append(
                        {
                            "code": "CHECKPOINT_SCHEMA_INVALID",
                            "path": json_path.name,
                            "message": message,
                        }
                    )

                summary = re.sub(r"\s+", "", str(data.get("confirmation_message_summary") or ""))
                if summary and GENERIC_CONFIRMATION_RE.fullmatch(summary):
                    errors.append(
                        {
                            "code": "CHECKPOINT_CONFIRMATION_GENERIC",
                            "path": json_path.name,
                            "message": "confirmation_message_summary must preserve concrete user decisions, not a generic confirmation phrase.",
                        }
                    )

                if stem == "00-research-goal":
                    notice = data.get("workspace_notice") if isinstance(data.get("workspace_notice"), dict) else {}
                    expected_run = process_dir.parent if process_dir.name == "过程稿" else process_dir
                    expected_process = process_dir
                    actual_run = Path(str(notice.get("run_dir") or "")).expanduser()
                    actual_process = Path(str(notice.get("process_dir") or "")).expanduser()
                    try:
                        paths_match = (
                            actual_run.resolve() == expected_run.resolve()
                            and actual_process.resolve() == expected_process.resolve()
                        )
                    except OSError:
                        paths_match = False
                    if not paths_match:
                        errors.append({
                            "code": "WORKSPACE_NOTICE_PATH_MISMATCH",
                            "path": json_path.name,
                            "message": "workspace_notice must contain the actual absolute run_dir and process_dir.",
                        })
                    md_normalized = _normalized_visible_text(md_text)
                    for label, path_value in (("run_dir", notice.get("run_dir")), ("process_dir", notice.get("process_dir"))):
                        if path_value and _normalized_visible_text(path_value) not in md_normalized:
                            errors.append({
                                "code": "WORKSPACE_NOTICE_MD_MISSING",
                                "path": md_path.name,
                                "message": f"{label} must be visible in 00-research-goal.md so the user can recover the workspace.",
                            })

                if stem == "05-report":
                    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
                    for heading in ("## 本次新增决定", "## 信息损失", "## 最终页面清单"):
                        if heading not in md_text:
                            errors.append({
                                "code": "REPORT_DELTA_REVIEW_MISSING",
                                "path": md_path.name,
                                "message": f"05-report.md 缺少增量确认章节 {heading!r}，不得让用户重复确认 03/04。",
                            })
                    page_count = metadata.get("page_count")
                    if not isinstance(page_count, int) or page_count < 1:
                        errors.append({
                            "code": "REPORT_PAGE_COUNT_MISSING",
                            "path": json_path.name,
                            "message": "05-report.json metadata.page_count must record the user-confirmed final page count.",
                        })
                    elif not re.search(rf"最终页数\s*[：:]\s*{page_count}(?:\D|$)", md_text):
                        errors.append({
                            "code": "REPORT_PAGE_COUNT_MD_MISMATCH",
                            "path": md_path.name,
                            "message": f"05-report.md must explicitly state '最终页数：{page_count}'.",
                        })
                    if PENDING_MD_RE.search(md_text) or CONFIRMED_MD_MARKER not in md_text:
                        errors.append({"code": "CHECKPOINT_MD_STATUS_MISMATCH", "path": md_path.name, "message": "05-report.json exists but 05-report.md is still pending/draft or lacks the confirmed marker."})
                    exact_reply = str(metadata.get("confirmation_user_message") or "").strip()
                    if not exact_reply:
                        errors.append({"code": "CHECKPOINT_CONFIRMATION_MESSAGE_MISSING", "path": json_path.name, "message": "05 must preserve the user's exact page/module confirmation reply."})
                    elif CONTENT_STAGE_GENERIC_REPLY_RE.fullmatch(exact_reply):
                        errors.append({"code": "CHECKPOINT_CONFIRMATION_TOO_AMBIGUOUS", "path": json_path.name, "message": "A generic progress reply cannot approve module deletion or the final page plan."})
                    elif CONFIRMATION_PHRASES[stem] not in exact_reply:
                        errors.append({"code": "CHECKPOINT_CONFIRMATION_PHRASE_MISSING", "path": json_path.name, "message": f"05 confirmation must include the exact phrase {CONFIRMATION_PHRASES[stem]!r} after all corrections are applied."})
                    if metadata.get("user_confirmed") is not True:
                        errors.append({"code": "CHECKPOINT_NOT_CONFIRMED", "path": json_path.name, "message": "05 metadata.user_confirmed must be true."})
                    if metadata.get("alignment_md_sha256") != md_sha256_text(md_text):
                        errors.append({"code": "CHECKPOINT_ALIGNMENT_HASH_MISMATCH", "path": json_path.name, "message": "05 alignment_md_sha256 does not match 05-report.md."})
                    required_sections = CONFIRMATION_SECTIONS[stem]
                    if not required_sections.issubset(set(metadata.get("confirmed_value_sections") or [])):
                        errors.append({"code": "CHECKPOINT_CONFIRMATION_SCOPE_INCOMPLETE", "path": json_path.name, "message": f"05 confirmed_value_sections must include {sorted(required_sections)}."})

                is_confirmed_checkpoint = (
                    stem == "05-report"
                    or data.get("status") in {"confirmed", "validated", "not_applicable"}
                    or data.get("user_confirmed") is True
                )
                if stem != "05-report" and is_confirmed_checkpoint:
                    guided_journey_confirmation = False
                    if stem == "04-journeys" and (data.get("alignment_review") or {}).get("mode") == "guided_rounds":
                        try:
                            from scripts.journey_alignment import alignment_review_errors
                        except ImportError:
                            from journey_alignment import alignment_review_errors  # type: ignore
                        guided_journey_confirmation = not alignment_review_errors(data)
                    if PENDING_MD_RE.search(md_text) or CONFIRMED_MD_MARKER not in md_text:
                        errors.append({
                            "code": "CHECKPOINT_MD_STATUS_MISMATCH",
                            "path": md_path.name,
                            "message": f"{json_path.name} is confirmed but {md_path.name} is still pending/draft or lacks '{CONFIRMED_MD_MARKER}'.",
                        })
                    exact_reply = str(data.get("confirmation_user_message") or "").strip()
                    if not exact_reply:
                        errors.append({
                            "code": "CHECKPOINT_CONFIRMATION_MESSAGE_MISSING",
                            "path": json_path.name,
                            "message": "Every checkpoint must preserve the user's exact confirmation reply.",
                        })
                    elif CONTENT_STAGE_GENERIC_REPLY_RE.fullmatch(exact_reply):
                        errors.append({
                            "code": "CHECKPOINT_CONFIRMATION_TOO_AMBIGUOUS",
                            "path": json_path.name,
                            "message": "A generic progress reply cannot confirm checkpoint values. Ask for an explicit checkpoint-specific reply.",
                        })
                    elif not guided_journey_confirmation and CONFIRMATION_PHRASES[stem] not in exact_reply:
                        errors.append({
                            "code": "CHECKPOINT_CONFIRMATION_PHRASE_MISSING",
                            "path": json_path.name,
                            "message": f"Confirmation must include the exact phrase {CONFIRMATION_PHRASES[stem]!r} after all corrections are applied.",
                        })
                    elif REJECTION_OR_SKIP_RE.search(exact_reply):
                        errors.append({
                            "code": "CHECKPOINT_CONFIRMATION_CONTRADICTORY",
                            "path": json_path.name,
                            "message": "The preserved user reply contains rejection, skip-review, or confusion language and cannot be recorded as confirmation.",
                        })
                    expected_hash = md_sha256_text(md_text)
                    if data.get("alignment_md_sha256") != expected_hash:
                        errors.append({
                            "code": "CHECKPOINT_ALIGNMENT_HASH_MISMATCH",
                            "path": json_path.name,
                            "message": f"alignment_md_sha256 does not match the current {md_path.name}.",
                        })
                    coverage, missing_values, total_values = _alignment_coverage(stem, data, md_text)
                    required_coverage = ALIGNMENT_MIN_COVERAGE
                    if stem not in {"04-personas", "04-journeys"} and (total_values < 3 or coverage < required_coverage):
                        errors.append({
                            "code": "CHECKPOINT_VALUE_ALIGNMENT_INCOMPLETE",
                            "path": md_path.name,
                            "message": (
                                f"MD covers {coverage:.0%} of {total_values} user-visible JSON values; "
                                f"at least {required_coverage:.0%} is required. "
                                f"Missing examples: {missing_values[:8]}"
                            ),
                        })

                    sections = set(data.get("confirmed_value_sections") or [])
                    required_sections = CONFIRMATION_SECTIONS[stem]
                    if not required_sections.issubset(sections):
                        errors.append({
                            "code": "CHECKPOINT_CONFIRMATION_SCOPE_INCOMPLETE",
                            "path": json_path.name,
                            "message": f"confirmed_value_sections must include {sorted(required_sections)}.",
                        })

    # File mtimes are deliberately not used as truth. Copying a run, rebinding a
    # hash, or updating the workspace path changes mtimes without changing user
    # decisions. Content fingerprints and explicit cross-checkpoint comparisons
    # below detect real drift without forcing a full downstream rebuild.

    for stem in ("00-research-goal", "01-paradigm", "04-personas"):
        data = parsed.get(stem)
        if data is not None and data.get("status") not in {"confirmed", "validated"}:
            errors.append(
                {
                    "code": "CHECKPOINT_NOT_CONFIRMED",
                    "path": f"{stem}.json",
                    "message": f"{stem}.json status must be confirmed or validated.",
                }
            )

    classification = parsed.get("02-classification")
    if classification is not None:
        status = classification.get("status")
        if status == "not_applicable":
            reason = str(classification.get("not_applicable_reason") or "").strip()
            if len(reason) < 8:
                errors.append(
                    {
                        "code": "CHECKPOINT_NA_REASON_MISSING",
                        "path": "02-classification.json",
                        "message": "02-classification.json marked not_applicable must include a concrete reason.",
                    }
                )
        elif status not in {"confirmed", "validated"}:
            errors.append(
                {
                    "code": "CHECKPOINT_NOT_CONFIRMED",
                    "path": "02-classification.json",
                    "message": "02-classification.json status must be confirmed, validated, or not_applicable.",
                }
            )

    field_alignment = parsed.get("03-field-alignment")
    if field_alignment is not None and field_alignment.get("user_confirmed") is not True:
        errors.append(
            {
                "code": "CHECKPOINT_NOT_CONFIRMED",
                "path": "03-field-alignment.json",
                "message": "03-field-alignment.json user_confirmed must be true.",
            }
        )

    journeys = parsed.get("04-journeys")
    if journeys is not None:
        status = journeys.get("status")
        if status == "not_applicable":
            reason = str(journeys.get("not_applicable_reason") or "").strip()
            if len(reason) < 8:
                errors.append(
                    {
                        "code": "CHECKPOINT_NA_REASON_MISSING",
                        "path": "04-journeys.json",
                        "message": "04-journeys.json marked not_applicable must include a concrete reason.",
                    }
                )
        elif status not in {"confirmed", "validated"}:
            errors.append(
                {
                    "code": "CHECKPOINT_NOT_CONFIRMED",
                    "path": "04-journeys.json",
                    "message": "04-journeys.json status must be confirmed, validated, or not_applicable.",
                }
            )
        if journeys.get("user_confirmed") is not True:
            errors.append(
                {
                    "code": "CHECKPOINT_NOT_CONFIRMED",
                    "path": "04-journeys.json",
                    "message": "04-journeys.json user_confirmed must be true.",
                }
            )

    report_json = process_dir / "05-report.json"
    prereq_stems = [
        "00-research-goal",
        "01-paradigm",
        "02-classification",
        "03-field-alignment",
        "04-personas",
        "04-journeys",
    ]
    if report_json.exists():
        if not any(presence[:-1]):
            errors.append(
                {
                    "code": "ONLY_FINAL_REPORT",
                    "path": report_json.name,
                    "message": "05-report.json exists without any earlier checkpoint artifact.",
                }
            )
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
    reduced_dir = process_dir / "reduced"
    processed = iter_artifacts(processed_dir, ".txt")
    extracted = iter_artifacts(extracted_dir, ".json")
    reduced = iter_artifacts(reduced_dir, ".json")
    executable_suffixes = {".py", ".js", ".mjs", ".cjs", ".ps1", ".bat", ".cmd", ".html"}
    unauthorized_builders = sorted(
        item.relative_to(process_dir).as_posix()
        for item in process_dir.rglob("*")
        if item.is_file()
        and item.suffix.lower() in executable_suffixes
        and item.relative_to(process_dir).parts[0] not in {"历史版本", "recovery-bundles"}
    )
    if unauthorized_builders:
        errors.append({
            "code": "UNAUTHORIZED_PROCESS_BUILDER",
            "path": "过程稿/",
            "message": (
                "Process artifacts must be data only. Custom Python/JavaScript/shell/HTML builders can "
                f"bypass schemas and silently truncate content: {unauthorized_builders[:12]}"
            ),
        })
    if require_complete and not processed:
        errors.append(
            {
                "code": "PROCESSED_ARTIFACTS_EMPTY",
                "path": "processed/",
                "message": "A complete workflow must contain at least one processed interview.",
            }
        )
    if require_complete and not extracted:
        errors.append(
            {
                "code": "EXTRACTED_ARTIFACTS_EMPTY",
                "path": "extracted/",
                "message": "A complete workflow must contain at least one extracted JSON artifact.",
            }
        )
    if parsed.get("04-personas") is not None and not reduced:
        errors.append(
            {
                "code": "REDUCED_ARTIFACTS_EMPTY",
                "path": "reduced/",
                "message": "04-personas.json exists but no per-field reduced JSON artifacts were persisted.",
            }
        )
    for item in reduced:
        data = _load_json(item)
        rel = item.relative_to(reduced_dir).as_posix()
        if data is None or not data:
            errors.append(
                {
                    "code": "REDUCED_JSON_INVALID",
                    "path": f"reduced/{rel}",
                    "message": "Reduced artifact must be a non-empty JSON object.",
                }
            )
    alignment_fields = (parsed.get("03-field-alignment") or {}).get("fields_per_persona")
    if parsed.get("04-personas") is not None and isinstance(alignment_fields, dict):
        expected_fields = {
            str(field)
            for fields in alignment_fields.values() if isinstance(fields, list)
            for field in fields
        }
        reduced_fields = {item.stem for item in reduced}
        missing_fields = sorted(expected_fields - reduced_fields)
        if missing_fields:
            errors.append(
                {
                    "code": "REDUCED_FIELD_MISSING",
                    "path": "reduced/",
                    "message": f"No reduced JSON exists for confirmed fields: {missing_fields[:12]}.",
                }
            )
    if len(extracted) != len(processed):
        errors.append(
            {
                "code": "PROCESSED_EXTRACTED_COUNT_MISMATCH",
                "path": "processed/ extracted/",
                "message": f"processed has {len(processed)} txt files, extracted has {len(extracted)} json files.",
                "processed_count": len(processed),
                "extracted_count": len(extracted),
            }
        )
    processed_by_hash: dict[str, list[str]] = {}
    for item in processed:
        try:
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
        except OSError:
            continue
        processed_by_hash.setdefault(digest, []).append(item.relative_to(processed_dir).as_posix())
    duplicate_groups = [paths for paths in processed_by_hash.values() if len(paths) > 1]
    if duplicate_groups:
        errors.append({
            "code": "PROCESSED_CONTENT_DUPLICATE",
            "path": "processed/",
            "message": (
                "Each interview must be stored and extracted once. Assign one source ID to multiple personas "
                "in 04-personas.json instead of copying the source; duplicate groups: "
                f"{duplicate_groups[:8]}"
            ),
            "file_count": len(processed),
            "unique_content_count": len(processed_by_hash),
        })
    if processed or extracted:
        processed_stems = artifact_keys(processed, processed_dir)
        extracted_stems = artifact_keys(extracted, extracted_dir)
        if processed_stems != extracted_stems:
            errors.append(
                {
                    "code": "PROCESSED_EXTRACTED_NAME_MISMATCH",
                    "path": "processed/ extracted/",
                    "message": "processed and extracted artifact basenames do not match.",
                    "missing_extracted": sorted(processed_stems - extracted_stems),
                    "orphan_extracted": sorted(extracted_stems - processed_stems),
                }
            )
    for item in extracted:
        data = _load_json(item)
        rel = item.relative_to(extracted_dir).as_posix()
        if data is None:
            errors.append(
                {
                    "code": "EXTRACTED_JSON_INVALID",
                    "path": f"extracted/{rel}",
                    "message": "Extracted artifact must be a valid JSON object.",
                }
            )
            continue
        if not data:
            errors.append(
                {
                    "code": "EXTRACTED_JSON_EMPTY",
                    "path": f"extracted/{rel}",
                    "message": "Extracted artifact is empty and cannot support persona evidence.",
                }
            )
        source_file = str(data.get("_source_file") or "").strip()
        source_id = str(data.get("_source_id") or "").strip()
        expected_name = (processed_dir / item.relative_to(extracted_dir)).with_suffix(".txt").name
        if not source_file:
            errors.append(
                {
                    "code": "EXTRACTED_SOURCE_MISSING",
                    "path": f"extracted/{rel}",
                    "message": "Extracted artifact must contain _source_file for evidence traceability.",
                }
            )
        elif source_file != expected_name:
            errors.append(
                {
                    "code": "EXTRACTED_SOURCE_MISMATCH",
                    "path": f"extracted/{rel}",
                    "message": f"_source_file={source_file!r} does not match {expected_name!r}.",
                }
            )
        if not re.fullmatch(r"P[0-9A-F]{8}", source_id):
            errors.append(
                {
                    "code": "EXTRACTED_SOURCE_ID_INVALID",
                    "path": f"extracted/{rel}",
                    "message": "Extracted artifact must contain stable anonymous _source_id matching P + 8 uppercase hex characters.",
                }
            )

    source_ids = [
        str((_load_json(item) or {}).get("_source_id") or "")
        for item in extracted
    ]
    valid_source_ids = [item for item in source_ids if item]
    if len(valid_source_ids) != len(set(valid_source_ids)):
        errors.append(
            {
                "code": "EXTRACTED_SOURCE_ID_DUPLICATE",
                "path": "extracted/",
                "message": "Each extracted artifact must have a unique _source_id.",
            }
        )

    errors.extend(_cross_checkpoint_errors(parsed, len(processed), source_counts))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required MD/JSON checkpoint pairs.")
    parser.add_argument("--workdir", required=True, help="Run directory or process directory.")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Require all workflow pairs, including 04-personas and 04-journeys. Rendering always enables this mode.",
    )
    args = parser.parse_args()

    process_dir = resolve_process_dir(Path(args.workdir))
    errors = validate_checkpoint_pairing(process_dir, require_complete=args.require_complete)
    payload = {"valid": not errors, "process_dir": str(process_dir), "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
