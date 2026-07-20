from __future__ import annotations

import json
from pathlib import Path

from scripts.render_checkpoint_md import render_journeys_md, render_personas_md
from scripts.validate_human_checkpoint_md import validate_human_checkpoint_md


PARADIGM_ROUTES = """# 01 画像方式选择

## 五种画像方式

| 画像方式 | 适合什么资料 | 会得到什么 |
|---|---|---|
| A 合并为一个画像 | 同一类用户 | 一个综合画像 |
| B 沿用已有分组 | 已有分组 | 每组一个画像 |
| C 按一个关键差异分类 | 一个关键差异 | 多个画像 |
| D 用两个区分点形成矩阵 | 两个差异 | 二维矩阵 |
| E 用多个区分点形成分布 | 多个差异 | 多维对照图 |

## 我的推荐

推荐方式：A 合并为一个画像。
"""


def _journey_data() -> dict:
    return {
        "status": "draft",
        "context_snapshot": {"research_question": "验证复杂旅程是否容易理解", "decision_use": "用于改善产品规划", "research_type": "toD", "paradigm": "R1"},
        "scope": "overall-only",
        "journeys": [{
            "persona_id": "journey-l1", "component_type": "tob_journey_l1",
            "props": {
                "banner_title": "训练端到端旅程",
                "stages": [{"id": "s-prepare", "name": "需求准备", "subStages": ["澄清需求"]}, {"id": "s-ship", "name": "验收交付", "subStages": ["验收"]}],
                "lanes": [{"id": "lane-user", "name": "模型开发者", "tag": "开发"}],
                "nodes": [{"id": "n1", "lane": "lane-user", "stage": "s-prepare", "type": "start", "label": "提出需求"}, {"id": "n2", "lane": "lane-user", "stage": "s-ship", "type": "end", "label": "完成验收"}],
                "edges": [{"from": "n1", "to": "n2", "style": "solid"}],
            },
            "evidence_bindings": [{"target": "stage:s-prepare", "evidence_type": "synthesis", "source_ids": [], "quote_or_basis": "根据访谈归纳"}],
        }],
        "quality_review": {"stage_names_confirmed": False, "flow_order_confirmed": False, "evidence_gaps": [], "evidence_gaps_acknowledged": False},
    }


def test_generated_journey_md_uses_chinese_semantic_layer(tmp_path: Path) -> None:
    data = _journey_data()
    (tmp_path / "04-journeys.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    md = render_journeys_md(data)
    (tmp_path / "04-journeys.md").write_text(md, encoding="utf-8")
    assert "角色 × 阶段责任矩阵" in md
    assert "s-prepare" not in md
    assert "lane-user" not in md
    assert "tob_journey_l1" not in md
    assert validate_human_checkpoint_md(tmp_path) == []


def test_raw_machine_ids_and_english_fields_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "04-journeys.md").write_text("# 旅程\n\n| 阶段 ID | 泳道 |\n|---|---|\n| s-pilot | lane-user |\n", encoding="utf-8")
    (tmp_path / "04-personas.md").write_text("# 画像\n\n#### responsibilities\n", encoding="utf-8")
    errors = validate_human_checkpoint_md(tmp_path)
    codes = {item["code"] for item in errors}
    assert "HUMAN_MD_MACHINE_ID_VISIBLE" in codes
    assert "HUMAN_MD_RAW_FIELD_NAME" in codes


def test_persona_renderer_translates_common_field_names() -> None:
    data = {
        "status": "draft", "context_snapshot": {},
        "personas": [{"name": "开发者", "description": "负责模型开发", "user_count": 1, "fields": {"responsibilities": ["开发模型"], "pain_points": ["排障困难"]}, "field_decisions": []}],
    }
    md = render_personas_md(data)
    assert "### 工作职责" in md
    assert "### 核心痛点" in md
    assert "responsibilities" not in md


def test_persona_renderer_never_displays_a_non_anonymous_evidence_source() -> None:
    data = {
        "status": "draft", "context_snapshot": {},
        "personas": [{
            "name": "开发者", "description": "负责模型开发", "user_count": 1,
            "fields": {"pain_points": [{
                "title": "排查困难", "detail": "需要反复切换工具",
                "evidence_quotes": [{"quote": "排查很慢", "source": "张伟"}],
            }]},
        }],
    }
    md = render_personas_md(data)
    assert "张伟" not in md
    assert "匿名来源待修复" in md


def test_paradigm_md_with_five_user_facing_routes_passes(tmp_path: Path) -> None:
    (tmp_path / "01-paradigm.md").write_text(PARADIGM_ROUTES, encoding="utf-8")
    assert validate_human_checkpoint_md(tmp_path) == []


def test_paradigm_md_rejects_missing_routes_and_internal_codes(tmp_path: Path) -> None:
    (tmp_path / "01-paradigm.md").write_text(
        "# 01 画像方式选择\n\n推荐范式：R2 单角色。\n",
        encoding="utf-8",
    )
    errors = validate_human_checkpoint_md(tmp_path)
    codes = {item["code"] for item in errors}
    assert "PARADIGM_MD_ROUTES_MISSING" in codes
    assert "PARADIGM_MD_INTERNAL_CODE_VISIBLE" in codes
    assert "PARADIGM_MD_RECOMMENDATION_MISSING" in codes


def test_paradigm_md_rejects_route_table_without_a_specific_recommendation(tmp_path: Path) -> None:
    md = PARADIGM_ROUTES.replace("推荐方式：A 合并为一个画像。", "推荐方式：待选择。")
    (tmp_path / "01-paradigm.md").write_text(md, encoding="utf-8")
    errors = validate_human_checkpoint_md(tmp_path)
    assert {item["code"] for item in errors} == {"PARADIGM_MD_RECOMMENDATION_MISSING"}


def test_confirmed_legacy_paradigm_wording_does_not_block_later_stages(tmp_path: Path) -> None:
    (tmp_path / "01-paradigm.md").write_text(
        "# 01 范式选择\n\n确认状态：已确认\n\n推荐范式：R2 单角色。\n",
        encoding="utf-8",
    )
    assert validate_human_checkpoint_md(tmp_path) == []
