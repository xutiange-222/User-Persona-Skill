from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.validate_paradigm_contract import validate_paradigm_contract


SOURCES = ["P11111111", "P22222222", "P33333333", "P44444444"]


def _write(path: Path, name: str, data: dict) -> None:
    (path / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _group(index: int, members: list[str]) -> dict:
    return {"id": f"persona-{index}", "name": f"画像{index}", "members": members}


def _mapping(groups: list[dict], variables: list[dict] | None = None) -> dict:
    variables = variables or []
    result = {}
    for group in groups:
        for source_id in group["members"]:
            result[source_id] = {
                "source_id": source_id,
                "group_id": group["id"],
                "variable_levels": {item["id"]: item["levels"][0]["id"] for item in variables},
                "evidence_quotes": [f'[来源:{source_id}]: "样例原话"'],
                "uncertainty": "无明显不确定性",
            }
    return result


def _variable(index: int) -> dict:
    return {
        "id": f"v{index}",
        "name": f"变量{index}",
        "definition": f"用于区分行为差异的变量{index}",
        "levels": [
            {"id": f"v{index}-low", "name": "低", "behavior_definition": "相关行为较少"},
            {"id": f"v{index}-high", "name": "高", "behavior_definition": "相关行为较多"},
        ],
    }


@pytest.mark.parametrize(
    ("choice", "paradigm", "group_count", "variable_count", "overview_layout"),
    [
        ("A", "R2", 1, 0, None),
        ("B", "R1", 2, 0, None),
        ("C", "R3", 2, 0, None),
        ("D", "R4", 2, 2, "layout-matrix-2d"),
        ("E", "R5", 2, 3, "layout-distribution-multi"),
    ],
)
@pytest.mark.parametrize("research_type", ["toB", "toC", "toD"])
def test_each_research_type_and_paradigm_has_one_consistent_machine_contract(
    research_type: str, choice: str, paradigm: str, group_count: int, variable_count: int, overview_layout: str | None
):
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        groups = [_group(i + 1, [SOURCES[i]]) for i in range(group_count)]
        variables = [_variable(i + 1) for i in range(variable_count)]
        paradigm_data = {
            "research_type": research_type,
            "paradigm": paradigm,
            "known_groups": groups if paradigm in {"R1", "R2"} else [],
        }
        if research_type == "toC":
            paradigm_data["choice_label"] = choice
        classification = {
            "status": "not_applicable" if paradigm in {"R1", "R2"} else "confirmed",
            "groups": [] if paradigm in {"R1", "R2"} else groups,
            "respondent_mapping": {} if paradigm in {"R1", "R2"} else _mapping(groups, variables),
            "value_variables": variables,
            "confirmed_value_sections": ["basis", "boundaries", "labels", "respondent_mapping", "groups", "uncertainties"],
        }
        if paradigm == "R4":
            classification["axes"] = {"x": "v1", "y": "v2"}
        _write(process, "01-paradigm.json", paradigm_data)
        _write(process, "02-classification.json", classification)
        _write(process, "04-personas.json", {"personas": groups})
        if overview_layout:
            _write(process, "05-report.json", {"personas": [{"layout": overview_layout}]})
        assert validate_paradigm_contract(process) == []


def test_r4_rejects_missing_respondent_level_mapping():
    with tempfile.TemporaryDirectory() as tmp:
        process = Path(tmp)
        groups = [_group(1, [SOURCES[0]])]
        variables = [_variable(1), _variable(2)]
        mapping = _mapping(groups, variables)
        mapping[SOURCES[0]]["variable_levels"].pop("v2")
        _write(process, "01-paradigm.json", {"research_type": "toC", "choice_label": "D", "paradigm": "R4", "known_groups": []})
        _write(process, "02-classification.json", {
            "status": "confirmed", "groups": groups, "respondent_mapping": mapping,
            "value_variables": variables, "axes": {"x": "v1", "y": "v2"},
            "confirmed_value_sections": ["basis", "boundaries", "labels", "respondent_mapping", "groups", "uncertainties"],
        })
        errors = validate_paradigm_contract(process)
        assert any(item["code"] == "PARADIGM_LEVEL_COVERAGE" for item in errors)
