#!/usr/bin/env python3
"""
Codex 产 schema 后,用户跑这个脚本看 PASS/FAIL,不需要懂 JSON Schema。

用法:
    python scripts/tools/review_codex_schemas.py

输出示例:
    [PASS] schemas/identity_card.json
    [FAIL] schemas/section_block.json
         - properties.body 没有 maxLength (LLM 可能写超长)
         - required 缺少 evidence_quotes
    [PASS] schemas/persona_quote_pull.json
    ...
    总计: 24 PASS / 1 FAIL.  请把 FAIL 的反馈给 Codex 修复后重跑.

退出码:
    0 = 全部 PASS
    1 = 有 FAIL
    2 = 找不到 schema 目录 / 缺文件

A.3 阶段使用流程:
  1. Codex 按 A.3 交接 prompt 批量产 25 个 schema 文件,放 scripts/components/schemas/
  2. 用户运行本脚本
  3. 看输出有没有 FAIL
  4. 有 FAIL 把脚本输出复制给 Codex,要求修复,然后重跑
  5. 全 PASS 后告诉主对话进 B 阶段
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Windows GBK 默认输出兼容:强制 utf-8,防中文 / emoji 输出炸
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Python 3.7+
    except (AttributeError, OSError):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = SKILL_ROOT / "scripts" / "components" / "schemas"
SAMPLES_DIR = SKILL_ROOT / "scripts" / "components" / "tests" / "golden_samples"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

# ============================================================
# 25 个 LLM 顶层 type 的契约清单
# 数据来自 REGISTRY.md(组件清单 + 各 layout props 契约段)
# ============================================================

TYPE_CONTRACTS: dict[str, dict] = {
    # ---- layout-2b-grid / 2b-grid-detail body 组件 (12 个) ----
    "identity_panel": {
        "required": ["persona_avatar", "identity_name", "identity_desc",
                     "identity_meta_rows", "one_sentence_need"],
    },
    "resp_rings": {
        "required": ["rings"],
        "notes": "rings 是数组,每项 {label, percentage}",
    },
    "collab_flow": {
        "required": ["demand_source", "deliverables", "downstream_flow", "kpi"],
        "notes": "上下游协同 + KPI 块(字段名与 validate_html LEGAL_COLLAB_KEYS 严格一致)",
    },
    "scenario_grid": {
        "required": ["scenes"],
        "notes": "scenes: [{caption, tools[], screenshot?}],screenshot 可选",
    },
    "ai_scenario_grid": {
        "required": ["scenes"],
        "notes": "与 scenario_grid 同形,渲染时加 .is-ai 修饰类",
    },
    "painpoint_list": {
        "required": ["items"],
        "notes": "items: [{title, detail, mention_badge?, evidence_quotes?}]",
    },
    "titled_list": {
        "required": ["items"],
        "notes": "items: [{title, detail}]",
    },
    "generic_text": {
        "required": ["text"],
    },
    "generic_bullet": {
        "required": ["items"],
        "notes": "items: [string]",
    },
    "generic_kv": {
        "required": ["rows"],
        "notes": "rows: [{key, value}]",
    },

    # ---- layout-2b-journey 组件 (2 个) ----
    "tob_journey_l1": {
        "required": ["banner_title", "banner_subtitle", "stages",
                     "lanes", "nodes", "edges"],
        "notes": "L1 全景:stages + lanes + nodes + edges UML DSL;Python 负责 deterministic 几何计算",
    },
    "tob_journey_l2": {
        "required": ["banner_title", "banner_subtitle", "stages",
                     "lanes", "nodes", "edges"],
        "notes": "L2 单角色:stages + lanes + nodes + edges UML DSL;lanes 通常 1-2 个",
    },

    # ---- layout-2c-portrait 组件 (4 个) ----
    # ---- golden sample composite components (3) ----
    "layout_2b_grid_detail": {
        "required": ["banner", "cells"],
        "notes": "golden sample composite: 2B detail page",
    },
    "layout_2c_detail": {
        "required": ["headline", "corner", "mockups", "sections"],
        "notes": "golden sample composite: 2C detail page",
    },
    "nav_trio": {
        "required": ["groups"],
        "notes": "golden sample navigation",
    },

    "identity_card": {
        "required": ["name", "subtitle", "meta_tags"],
        "notes": "meta_tags 2-5 个 {label, value};label/value 完全自由文本",
    },
    "persona_quote_pull": {
        "required": ["quote", "source"],
        "notes": "quote ≤ 50 字",
    },
    "section_blocks_grid": {
        "required": ["blocks"],
        "notes": "blocks 数量必须是 2 / 4 / 6;full_width_index 可选",
    },
    "section_block": {
        "required": ["title", "summary", "body", "evidence_quotes"],
        "notes": "title 3-6 字,summary 8-25 字,body **30-100 字 minLength: 30**,evidence_quotes 至少 2 条",
    },

    # ---- layout-2c-detail 组件 (4 个) ----
    "detail_headline": {
        "required": ["headline"],
        "notes": "headline ≤ 30 字",
    },
    "mockup_list": {
        "required": ["mockups"],
        "notes": "mockups: [{caption, screenshot?}]",
    },
    "detail_analysis": {
        "required": ["sections"],
        "notes": "sections 2-3 个 {title, body};body 50-150 字",
    },
    "detail_illust_corner": {
        "required": [],
        "notes": "完全可选;Python 三级 fallback 渲染",
    },

    # ---- layout-2c-journey 容器 (1 个) ----
    "journey_2c": {
        "required": ["title", "subtitle", "stages", "dimensions", "cells", "emotion"],
        "notes": "stages 4-6;dimensions 至少含 [思考,行为,痛点];cells[dim][stage];emotion 每项 {stage_label, level: high/middle/low, emoji}",
    },

    # ---- layout-matrix-2d (2 个) ----
    "matrix_guidance_strip": {
        "required": ["items"],
        "notes": "items: [{question, points[]}]",
    },
    "matrix_2d": {
        "required": ["axis_labels", "quadrants", "respondents"],
        "notes": "axis_labels {top,bottom,left,right} 各 ≤ 8 字;quadrants 必填 4 个(可标 is_empty);respondents {x, y, display_name, quadrant_persona, evidence};display_name pattern 拦截「受访者\\d+」",
    },

    # ---- layout-distribution-multi (1 个) ----
    "distribution_multi": {
        "required": ["title", "subtitle", "value_variables", "personas"],
        "notes": "value_variables 3-5 个;每个 levels 必须 3 档(high/middle/low);personas 2-5 个",
    },
}

# 33 个 emoji 枚举,journey_2c.json 内 emotion.emoji 字段必须用这个枚举
EMOJI_ENUM = {
    # 笑脸/愉悦 (8)
    "smile", "smile_blush", "grin", "laughing", "content",
    "relaxed", "proud", "star_struck",
    # 困惑/思考 (5)
    "thinking", "confused", "raised_eyebrow", "neutral", "hmm",
    # 消极/负面 (7)
    "frowning", "disappointed", "frustrated", "persevere",
    "tired", "sad", "crying",
    # 惊讶/强反应 (3)
    "surprised", "shocked", "exclamation",
    # 兴奋/积极 (4)
    "excited", "celebrate", "fire", "heart_eyes",
    # 物品/隐喻 (6)
    "headphone", "light_bulb", "target", "thumbs_up", "thumbs_down", "question",
}

# 8 个允许的 layout
LAYOUT_ENUM = {
    "layout-2b-grid", "layout-2b-grid-detail", "layout-2b-journey",
    "layout-2c-portrait", "layout-2c-detail", "layout-2c-journey",
    "layout-matrix-2d", "layout-distribution-multi",
}


def review_single_schema(schema_path: Path) -> list[str]:
    """检查一个 schema 文件。返回错误列表,空 list = 通过。"""
    errors: list[str] = []

    try:
        with open(schema_path, encoding="utf-8") as f:
            s = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: {e}"]
    except OSError as e:
        return [f"读文件失败: {e}"]

    # 1. 必备顶层字段
    if "$schema" not in s:
        errors.append("缺 $schema 字段(应为 https://json-schema.org/draft/2020-12/schema)")
    elif "draft/2020-12" not in s["$schema"]:
        errors.append(f"$schema 不是 draft/2020-12: {s['$schema']}")

    if "$id" not in s:
        errors.append("缺 $id 字段")
    if "title" not in s:
        errors.append("缺 title 字段(中文人类可读名)")
    if s.get("type") != "object":
        errors.append(f"type 必须是 object,实际: {s.get('type')}")
    if s.get("additionalProperties") is not False:
        errors.append("additionalProperties 必须是 false(防 LLM 自由发挥)")
    if "properties" not in s:
        errors.append("缺 properties 字段")
    if "required" not in s:
        errors.append("缺 required 数组")

    # 2. 文件名 == $id
    expected_id = schema_path.stem
    if s.get("$id") and s["$id"] != expected_id:
        errors.append(f"$id={s['$id']!r} 不等于文件名 {expected_id!r}")

    # 3. $id 在 25 个 type 之一(或 report 顶层)
    if expected_id != "report" and expected_id not in TYPE_CONTRACTS:
        errors.append(f"$id={expected_id!r} 不在 25 个允许的 type 列表里")

    # 4. required 必须含 REGISTRY 列的必填字段
    if expected_id in TYPE_CONTRACTS:
        contract = TYPE_CONTRACTS[expected_id]
        expected_required = set(contract["required"])
        actual_required = set(s.get("required", []))
        missing = expected_required - actual_required
        if missing:
            errors.append(
                f"required 缺少 REGISTRY 规定的必填字段: {sorted(missing)}"
            )
        # 不强查 extra 多出来的字段（schema 自由添加可选字段是允许的）

    # 5. 所有 string 类型字段必须有 maxLength(防 LLM 写超长)
    props = s.get("properties", {})
    for fname, fschema in props.items():
        if isinstance(fschema, dict) and fschema.get("type") == "string":
            if "maxLength" not in fschema:
                errors.append(
                    f"properties.{fname} (string 类型) 没有 maxLength,LLM 可能写超长"
                )
        if isinstance(fschema, dict) and fschema.get("type") == "array":
            if "maxItems" not in fschema:
                errors.append(
                    f"properties.{fname} (array 类型) 没有 maxItems,LLM 可能塞太多"
                )

    # 6. 特殊字段的硬约束
    if expected_id == "section_block":
        body_schema = props.get("body", {})
        if body_schema.get("minLength", 0) < 30:
            errors.append(
                "section_block.body.minLength 必须 ≥ 30(防敷衍内容,REGISTRY §4.2)"
            )
        ev = props.get("evidence_quotes", {})
        if ev.get("minItems", 0) < 2:
            errors.append(
                "section_block.evidence_quotes.minItems 必须 ≥ 2(每段卡至少 2 条证据,REGISTRY §4.2)"
            )

    if expected_id == "matrix_2d":
        respondents = props.get("respondents", {}).get("items", {})
        display_name = respondents.get("properties", {}).get("display_name", {})
        if "pattern" not in display_name or "受访者" not in display_name.get("pattern", ""):
            errors.append(
                "matrix_2d.respondents[].display_name 必须有 pattern 拦截「受访者\\d+」(REGISTRY §7.5)"
            )

    if expected_id == "section_blocks_grid":
        blocks = props.get("blocks", {})
        # blocks 是 array,数量必须 2/4/6
        # 因为 JSON Schema 不能直接表达 {2,4,6} 离散值,这里只检查存在 minItems 和 maxItems
        if blocks.get("minItems") != 2 or blocks.get("maxItems") != 6:
            errors.append(
                "section_blocks_grid.blocks 必须 minItems:2, maxItems:6,且 description 说明只允许 2/4/6"
            )

    if expected_id == "journey_2c":
        emotion = props.get("emotion", {}).get("items", {})
        emoji_field = emotion.get("properties", {}).get("emoji", {})
        if "enum" not in emoji_field:
            errors.append(
                "journey_2c.emotion[].emoji 必须有 enum (33 个语义名,REGISTRY §6.3)"
            )
        else:
            actual_set = set(emoji_field["enum"])
            if actual_set != EMOJI_ENUM:
                missing = EMOJI_ENUM - actual_set
                extra = actual_set - EMOJI_ENUM
                if missing:
                    errors.append(f"emoji enum 缺少: {sorted(missing)}")
                if extra:
                    errors.append(f"emoji enum 多了非法值: {sorted(extra)}")

    if expected_id == "report":
        # 顶层 report.json 单独检查
        meta = props.get("metadata", {}).get("properties", {})
        if meta.get("layout"):
            errors.append("metadata 不应该有 layout 字段(layout 在 personas[].layout)")

        personas = props.get("personas", {}).get("items", {})
        persona_props = personas.get("properties", {})
        layout_field = persona_props.get("layout", {})
        if "enum" not in layout_field:
            errors.append("personas[].layout 必须有 enum(8 个 layout)")
        elif set(layout_field["enum"]) != LAYOUT_ENUM:
            missing = LAYOUT_ENUM - set(layout_field["enum"])
            extra = set(layout_field["enum"]) - LAYOUT_ENUM
            if missing:
                errors.append(f"layout enum 缺少: {sorted(missing)}")
            if extra:
                errors.append(f"layout enum 多了非法值: {sorted(extra)}")

    # 7. 用 jsonschema 库验证 schema 本身是合法的 JSON Schema (可选,如果库装了)
    try:
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(s)
    except ImportError:
        pass  # 没装 jsonschema 库,跳过这一步
    except Exception as e:
        errors.append(f"Schema 本身不是合法的 JSON Schema: {e}")

    return errors



def review_golden_samples() -> tuple[int, int]:
    """校验 golden_samples/*.json 是否符合对应组件 schema。"""
    if not SAMPLES_DIR.exists():
        print(f"[FAIL] golden samples 目录不存在: {SAMPLES_DIR}")
        return 0, 1

    try:
        from jsonschema import validate
    except ImportError as e:
        print(f"[FAIL] 未安装 jsonschema 库: {e}")
        return 0, 1

    pass_count = 0
    fail_count = 0
    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    print("=" * 70)
    print("Golden samples schema validation")
    print(f"目录: {SAMPLES_DIR}")
    print(f"找到 {len(sample_files)} 个 golden JSON")
    print("=" * 70)

    for sample_path in sample_files:
        try:
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
            component_type = sample["type"]
            schema_path = SCHEMAS_DIR / f"{component_type}.json"
            if not schema_path.exists():
                raise ValueError(f"找不到对应 schema: {schema_path.name}")
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            validate(instance=sample["props"], schema=schema)
        except Exception as e:
            print(f"[FAIL] {sample_path.name}")
            print(f"     - {e}")
            fail_count += 1
        else:
            print(f"[PASS] {sample_path.name}")
            pass_count += 1
    print("=" * 70)
    print(f"Golden samples 汇总: {pass_count} PASS / {fail_count} FAIL")
    return pass_count, fail_count

def main() -> int:
    if not SCHEMAS_DIR.exists():
        print(f"找不到 schemas 目录: {SCHEMAS_DIR}", file=sys.stderr)
        print(
            "请确认 Codex 已经把 schema 文件产到 scripts/components/schemas/",
            file=sys.stderr,
        )
        return 2

    schema_files = sorted(SCHEMAS_DIR.glob("*.json"))
    if not schema_files:
        print(f"schemas 目录是空的: {SCHEMAS_DIR}", file=sys.stderr)
        return 2

    pass_count = 0
    fail_count = 0
    missing_types = set(TYPE_CONTRACTS.keys()) | {"report"}

    print("=" * 70)
    print("Schema review report")
    print(f"目录: {SCHEMAS_DIR}")
    print(f"找到 {len(schema_files)} 个 schema 文件")
    print("=" * 70)

    for path in schema_files:
        errors = review_single_schema(path)
        status = "PASS" if not errors else "FAIL"
        print(f"[{status}] {path.name}")
        for e in errors:
            print(f"     - {e}")
        if errors:
            fail_count += 1
        else:
            pass_count += 1
        missing_types.discard(path.stem)

    print("=" * 70)
    print(f"总计: {pass_count} PASS / {fail_count} FAIL")
    if missing_types:
        print(f"[!] 还缺这些 schema 文件: {sorted(missing_types)}")
        fail_count += len(missing_types)

    _, golden_fail_count = review_golden_samples()
    fail_count += golden_fail_count

    if fail_count == 0 and not missing_types:
        print("[OK] 所有 schema 和 golden samples 校验通过")
        return 0
    else:
        print(f"[X] 共 {fail_count} 处问题,请修复后重跑(直到 0 FAIL)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
