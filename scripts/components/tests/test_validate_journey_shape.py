"""journey_2c cells 轴向与 theme/layout 一致性校验回归。"""

from __future__ import annotations

from scripts.components.validate import validate_report_json


def _cell(keyword: str = "关键词") -> dict:
    return {"keyword": keyword, "summary": "摘要内容至少五个字"}


def _journey_props(n_dims: int, n_stages: int) -> dict:
    dims = ["思考", "行为", "痛点", "触点", "情绪"][:n_dims]
    stages = [f"阶段{i + 1}" for i in range(n_stages)]
    cells = [[_cell(f"{d}{s}") for s in range(n_stages)] for d in range(n_dims)]
    emotion = [
        {"stage_label": stages[i], "level": "middle", "emoji": "thinking"}
        for i in range(n_stages)
    ]
    return {
        "title": "测试旅程",
        "subtitle": "副标题用于校验",
        "stages": stages,
        "dimensions": dims,
        "cells": cells,
        "emotion": emotion,
    }


def _report_with_journey(props: dict, theme: str = "2c") -> dict:
    return {
        "metadata": {"theme": theme, "density": "low", "title": "测试"},
        "personas": [
            {
                "id": "persona-1-journey",
                "name": "测试",
                "layout": "layout-2c-journey",
                "components": [{"type": "journey_2c", "props": props}],
            }
        ],
    }


def test_journey_3x4_passes():
    issues = validate_report_json(_report_with_journey(_journey_props(3, 4)))
    codes = {i["code"] for i in issues if i["level"] == "ERROR"}
    assert "P8-JOURNEY-CELLS-SHAPE" not in codes


def test_journey_4x5_passes():
    issues = validate_report_json(_report_with_journey(_journey_props(4, 5)))
    codes = {i["code"] for i in issues if i["level"] == "ERROR"}
    assert "P8-JOURNEY-CELLS-SHAPE" not in codes


def test_journey_5x4_fails_shape():
    props = _journey_props(4, 5)
    # 故意按阶段分行:5 行 × 4 列
    props["cells"] = [
        [_cell(f"s{r}c{c}") for c in range(4)]
        for r in range(5)
    ]
    issues = validate_report_json(_report_with_journey(props))
    shape_errors = [
        i for i in issues
        if i["code"] == "P8-JOURNEY-CELLS-SHAPE" and "cells" in i["path"]
    ]
    assert len(shape_errors) == 1
    assert "4×5" in shape_errors[0]["message"]
    assert "5×" in shape_errors[0]["message"]


def test_theme_2b_rejects_journey_2c():
    report = _report_with_journey(_journey_props(3, 4), theme="2b")
    issues = validate_report_json(report)
    mismatch = [i for i in issues if i["code"] == "P8-THEME-LAYOUT-MISMATCH"]
    assert any("journey_2c" in i["message"] for i in mismatch)
    assert any("layout-2c-journey" in i["message"] for i in mismatch)


def test_r4_2b_matrix_plus_subpage_passes_theme_check():
    report = {
        "metadata": {"theme": "2b", "density": "high", "title": "测试"},
        "personas": [
            {
                "id": "matrix",
                "name": "矩阵",
                "layout": "layout-matrix-2d",
                "components": [
                    {
                        "type": "matrix_2d",
                        "props": {
                            "axis_labels": {
                                "top": "上",
                                "bottom": "下",
                                "left": "左",
                                "right": "右",
                            },
                            "quadrants": [
                                {"id": "persona-1", "label": "象限一", "position": "q1"},
                                {"id": "persona-2", "label": "象限二", "position": "q2"},
                                {"id": "persona-3", "label": "象限三", "position": "q3"},
                                {"id": "persona-4", "label": "象限四", "position": "q4"},
                            ],
                            "respondents": [],
                        },
                    }
                ],
            },
            {
                "id": "persona-1",
                "name": "象限一",
                "layout": "layout-2b-grid",
                "components": [
                    {
                        "type": "identity_panel",
                        "props": {
                            "persona_avatar": {"alt": "测试"},
                            "identity_name": {"name": "测试画像"},
                            "identity_desc": "用于校验的 toB 子页画像描述",
                            "identity_meta_rows": [
                                {"key": "岗位", "value": "调度员"},
                                {"key": "组织", "value": "电网中心"},
                            ],
                            "one_sentence_need": {
                                "text": "辅助演算须可解释",
                                "source": "测试",
                            },
                        },
                    }
                ],
            },
        ],
    }
    issues = validate_report_json(report)
    codes = {i["code"] for i in issues if i["level"] == "ERROR"}
    assert "P8-THEME-LAYOUT-MISMATCH" not in codes
    assert "P8-OVERVIEW-FORBIDDEN-COMPONENT" not in codes


def test_overview_rejects_identity_card():
    report = {
        "metadata": {"theme": "2c", "density": "low", "title": "测试"},
        "personas": [
            {
                "id": "matrix",
                "layout": "layout-matrix-2d",
                "components": [
                    {
                        "type": "identity_card",
                        "props": {
                            "name": "错放",
                            "subtitle": "不应在总览",
                            "illust_path": "x.png",
                            "meta_tags": [],
                        },
                    }
                ],
            }
        ],
    }
    issues = validate_report_json(report)
    forbidden = [i for i in issues if i["code"] == "P8-OVERVIEW-FORBIDDEN-COMPONENT"]
    assert len(forbidden) == 1
    assert "identity_card" in forbidden[0]["message"]
