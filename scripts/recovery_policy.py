"""Recovery routes for checkpoint gate errors.

Every blocking rule must point to a reachable next action.  A gate without a
recovery route is treated as a skill defect, not as a task the model should
keep retrying.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


HUMAN_MD_CODES = {
    "HUMAN_MD_RAW_FIELD_NAME", "HUMAN_MD_MACHINE_ID_VISIBLE",
    "HUMAN_MD_RAW_ENUM_VISIBLE", "HUMAN_MD_CONTENT_FINGERPRINT_MISMATCH",
    "JOURNEY_MD_GLOBAL_CONTEXT_MISSING", "JOURNEY_MD_ROLE_STAGE_MATRIX_MISSING",
    "JOURNEY_MD_LOCATION_MISSING",
}
CONFIRMATION_CODES = {
    "CHECKPOINT_CONFIRMATION_CONTRADICTORY", "CHECKPOINT_CONFIRMATION_MESSAGE_MISSING",
    "CHECKPOINT_CONFIRMATION_TOO_AMBIGUOUS", "CHECKPOINT_CONFIRMATION_PHRASE_MISSING",
    "JOURNEY_CONTENT_CONFIRMATION_MISSING", "JOURNEY_ALIGNMENT_REVIEW_INCOMPLETE",
    "CHECKPOINT_NOT_CONFIRMED",
}
PRIVACY_CODES = {"PRIVACY_LEAK", "PRIVACY_FORBIDDEN_NAME", "PRIVACY_VALIDATOR_ERROR"}
EVIDENCE_PREFIXES = ("EVIDENCE_", "JOURNEY_EVIDENCE_", "CONTENT_EXTRACTION_")


def checkpoint_from_path(path: str) -> str | None:
    for stem in (
        "00-research-goal", "01-paradigm", "02-classification", "03-field-alignment",
        "04-personas", "04-journeys", "05-report",
    ):
        if stem in path:
            return stem
    return None


def recovery_for(error: dict[str, Any], process_dir: Path) -> dict[str, Any]:
    code = str(error.get("code") or "")
    path = str(error.get("path") or "")
    stem = checkpoint_from_path(path)
    runner = f'python "{Path(__file__).resolve().parent / "repair_workflow.py"}"'
    quoted = f'"{process_dir}"'
    fallback = f'{runner} --workdir {quoted} --action create-recovery-bundle'

    if code == "UNAUTHORIZED_PROCESS_BUILDER":
        return {"kind": "automatic", "preserves_content": True, "command": f'{runner} --workdir {quoted} --action quarantine-builders', "fallback_command": fallback, "explanation": "把一次性脚本移入历史隔离目录，保留文件且恢复过程目录的数据纯度。"}
    if code == "HUMAN_MD_CONTENT_FINGERPRINT_MISMATCH":
        target = stem or "04-journeys"
        return {
            "kind": "official_rollback",
            "preserves_content": True,
            "command": f'{runner} --workdir {quoted} --action reopen-04 --stem {target}',
            "fallback_command": fallback,
            "explanation": "MD 与结构化内容已经分叉，可能包含用户手改。保留两版并重新对齐，禁止自动覆盖用户修改。",
        }
    if code in (HUMAN_MD_CODES - {"HUMAN_MD_CONTENT_FINGERPRINT_MISMATCH"}) or (code in {"CHECKPOINT_ALIGNMENT_HASH_MISMATCH", "CHECKPOINT_MD_STATUS_MISMATCH"} and stem in {"04-personas", "04-journeys"}):
        target = stem or "04-journeys"
        return {"kind": "automatic", "preserves_content": True, "command": f'{runner} --workdir {quoted} --action refresh-04-md --stem {target}', "fallback_command": fallback, "explanation": "从结构化真值重新生成中文 MD 并重绑哈希，不改画像或旅程正文。"}
    if code == "LANGUAGE_TITLE_TRUNCATED":
        target = "04-journeys" if "04-journeys" in path else "04-personas"
        return {
            "kind": "official_rollback",
            "preserves_content": True,
            "command": f'{runner} --workdir {quoted} --action reopen-04 --stem {target}',
            "fallback_command": fallback,
            "explanation": "归档已确认版本和下游产物，保留原内容生成可编辑 04 草稿。修复标题后重新生成中文 MD，并等待用户确认再封存。",
        }
    if code == "P8-JOURNEY-DUPLICATE-ID":
        return {
            "kind": "official_rollback",
            "preserves_content": True,
            "command": f'{runner} --workdir {quoted} --action reopen-04 --stem 04-journeys',
            "fallback_command": fallback,
            "explanation": "归档已确认旅程和 05，重新打开 04-journeys 草稿修复机器 ID；旅程文字保持不变，重新展示 MD 并等待确认。",
        }
    if code in CONFIRMATION_CODES:
        return {"kind": "user_review", "preserves_content": True, "command": None, "fallback_command": fallback, "explanation": "保持待确认，缩小信息范围重新展示。没有用户确认时可以交付恢复包，不能伪造确认。"}
    if code == "VALIDATOR_RUNTIME_ERROR":
        return {"kind": "skill_defect", "preserves_content": True, "command": None, "fallback_command": fallback, "explanation": "校验器自身或输入契约存在缺陷。停止重复尝试，交付恢复包并修复 Skill。"}
    if code in PRIVACY_CODES or code.startswith("PRIVACY_"):
        return {"kind": "manual_hard_block", "preserves_content": False, "command": None, "fallback_command": None, "explanation": "先完成脱敏。隐私错误未解决前禁止生成恢复包或最终交付。"}
    if code.startswith(EVIDENCE_PREFIXES):
        return {"kind": "content_repair", "preserves_content": False, "command": None, "fallback_command": fallback, "explanation": "回到当前结论和原始证据修复对应关系。保留已通过的上游文件，不修改其他检查点。"}
    if code in {"CHECKPOINT_MD_MISSING", "CHECKPOINT_JSON_MISSING", "CHECKPOINT_PAIR_MISSING", "CHECKPOINT_SCHEMA_INVALID", "CHECKPOINT_JSON_INVALID"}:
        return {"kind": "regenerate_current", "preserves_content": False, "command": None, "fallback_command": fallback, "explanation": "从最近一个已确认检查点重建当前文件；禁止修补下游产物。"}
    if code.startswith(("HTML_", "VISUAL_", "P7-", "P8-", "REPORT_")):
        return {"kind": "render_repair", "preserves_content": True, "command": None, "fallback_command": fallback, "explanation": "只修固定模板、组件参数或分页。内容 JSON 保持不变；三次失败后交付恢复包。"}
    return {"kind": "diagnose_once", "preserves_content": True, "command": None, "fallback_command": fallback, "explanation": "当前错误缺少自动恢复器。只允许诊断一次；再次出现时按 Skill 缺陷停止。"}
