#!/usr/bin/env python3
"""Validate R1-R5 branch truth across 01, 02, 04 and 05."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.path_utils import resolve_process_dir
except ImportError:
    from path_utils import resolve_process_dir

CHOICE_TO_PARADIGM = {"A": "R2", "B": "R1", "C": "R3", "D": "R4", "E": "R5"}
OVERVIEW_LAYOUT = {"R4": "layout-matrix-2d", "R5": "layout-distribution-multi"}


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _group_map(groups: object) -> dict[str, tuple[str, set[str]]]:
    result: dict[str, tuple[str, set[str]]] = {}
    for item in groups if isinstance(groups, list) else []:
        if not isinstance(item, dict):
            continue
        gid = str(item.get("id") or "")
        if gid:
            result[gid] = (str(item.get("name") or ""), set(map(str, item.get("members") or [])))
    return result


def validate_paradigm_contract(workdir: Path) -> list[dict]:
    process_dir = resolve_process_dir(Path(workdir))
    paradigm_data = _load(process_dir / "01-paradigm.json")
    if not paradigm_data:
        return []
    classification = _load(process_dir / "02-classification.json")
    personas_data = _load(process_dir / "04-personas.json")
    report = _load(process_dir / "05-report.json")
    errors: list[dict] = []

    def add(code: str, path: str, message: str) -> None:
        errors.append({"code": code, "path": path, "message": message})

    paradigm = str(paradigm_data.get("paradigm") or "")
    research_type = str(paradigm_data.get("research_type") or "")
    if research_type == "toC":
        choice = str(paradigm_data.get("choice_label") or "")
        expected = CHOICE_TO_PARADIGM.get(choice)
        if expected != paradigm:
            add("PARADIGM_CHOICE_MISMATCH", "01-paradigm.json", f"toC 方式 {choice!r} 对应 {expected!r}，当前 paradigm={paradigm!r}。")

    if classification:
        status = classification.get("status")
        if paradigm in {"R1", "R2"} and status != "not_applicable":
            add("PARADIGM_CLASSIFICATION_STATUS", "02-classification.json", f"{paradigm} 必须记录 status=not_applicable。")
        if paradigm in {"R3", "R4", "R5"} and status not in {"confirmed", "validated"}:
            add("PARADIGM_CLASSIFICATION_STATUS", "02-classification.json", f"{paradigm} 必须有已确认的分类真值。")

        groups = classification.get("groups") or []
        mapping = classification.get("respondent_mapping") or {}
        variables = classification.get("value_variables") or []
        sections = set(classification.get("confirmed_value_sections") or [])
        if paradigm == "R3":
            if not 2 <= len(groups) <= 12:
                add("R3_GROUP_COUNT", "02-classification.json", "R3 必须固化 2 到 12 个类别。")
            if variables:
                add("R3_VARIABLES_FORBIDDEN", "02-classification.json", "R3 使用一个分类依据，不写 value_variables。")
            required = {"basis", "boundaries", "labels", "respondent_mapping", "groups", "uncertainties"}
            if not required.issubset(sections):
                add("R3_CONFIRMATION_SCOPE", "02-classification.json", f"R3 必须确认 {sorted(required)}。")
        elif paradigm == "R4":
            if len(variables) != 2:
                add("R4_VARIABLE_COUNT", "02-classification.json", "R4 必须恰好有两个 value_variables。")
            if not 1 <= len(groups) <= 4:
                add("R4_GROUP_COUNT", "02-classification.json", "R4 必须固化 1 到 4 个有样本画像，空象限写入 empty_groups。")
            axes = classification.get("axes") or {}
            variable_ids = {str(item.get("id")) for item in variables if isinstance(item, dict)}
            if set(axes.values()) != variable_ids:
                add("R4_AXES_MISMATCH", "02-classification.json", "axes.x/y 必须各引用一个已确认的 value_variable id。")
        elif paradigm == "R5":
            if not 3 <= len(variables) <= 5:
                add("R5_VARIABLE_COUNT", "02-classification.json", "R5 必须固化 3 到 5 个 value_variables。")
            if not 2 <= len(groups) <= 5:
                add("R5_GROUP_COUNT", "02-classification.json", "R5 必须固化 2 到 5 个画像。")
            if classification.get("axes"):
                add("R5_AXES_FORBIDDEN", "02-classification.json", "R5 多维分布不使用二维 axes。")

        if paradigm in {"R3", "R4", "R5"}:
            group_map = _group_map(groups)
            member_to_group: dict[str, str] = {}
            for gid, (_, members) in group_map.items():
                for source_id in members:
                    if source_id in member_to_group:
                        add("PARADIGM_MEMBER_DUPLICATE", "02-classification.json", f"{source_id} 同时属于 {member_to_group[source_id]} 和 {gid}。")
                    member_to_group[source_id] = gid
            if set(mapping) != set(member_to_group):
                add("PARADIGM_MAPPING_COVERAGE", "02-classification.json", "respondent_mapping 必须恰好覆盖 groups 中的全部成员。")
            variable_level_ids = {
                str(variable.get("id")): {str(level.get("id")) for level in variable.get("levels") or [] if isinstance(level, dict)}
                for variable in variables if isinstance(variable, dict)
            }
            for source_id, item in mapping.items():
                if not isinstance(item, dict):
                    continue
                if item.get("source_id") != source_id:
                    add("PARADIGM_MAPPING_SOURCE_ID", "02-classification.json", f"respondent_mapping.{source_id}.source_id 必须与 key 一致。")
                if item.get("group_id") != member_to_group.get(source_id):
                    add("PARADIGM_MAPPING_GROUP", "02-classification.json", f"{source_id} 的 group_id 与 groups.members 不一致。")
                levels = item.get("variable_levels") or {}
                if paradigm in {"R4", "R5"}:
                    if set(levels) != set(variable_level_ids):
                        add("PARADIGM_LEVEL_COVERAGE", "02-classification.json", f"{source_id} 缺少部分变量档位映射。")
                    for variable_id, level_id in levels.items():
                        if level_id not in variable_level_ids.get(variable_id, set()):
                            add("PARADIGM_LEVEL_UNKNOWN", "02-classification.json", f"{source_id} 使用未知档位 {variable_id}={level_id}。")

    personas = personas_data.get("personas") if isinstance(personas_data.get("personas"), list) else []
    if personas:
        confirmed_map = _group_map(personas)
        if paradigm in {"R1", "R2"}:
            branch_map = _group_map(paradigm_data.get("known_groups") or [])
        else:
            branch_map = _group_map(classification.get("groups") or [])
        if paradigm == "R2" and len(confirmed_map) != 1:
            add("R2_PERSONA_COUNT", "04-personas.json", "R2 必须恰好生成一个画像。")
        if branch_map and confirmed_map != branch_map:
            add("PARADIGM_PERSONA_DRIFT", "04-personas.json", "04 的画像 id、名称或成员与已确认的分组真值不一致；请回到 01/02 重新确认。")

    if report and paradigm in OVERVIEW_LAYOUT:
        layouts = [item.get("layout") for item in report.get("personas") or [] if isinstance(item, dict)]
        required_layout = OVERVIEW_LAYOUT[paradigm]
        if layouts.count(required_layout) != 1:
            add("PARADIGM_OVERVIEW_LAYOUT", "05-report.json", f"{paradigm} 必须恰好包含一个 {required_layout} 总览页。")
    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    errors = validate_paradigm_contract(Path(args.workdir))
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
