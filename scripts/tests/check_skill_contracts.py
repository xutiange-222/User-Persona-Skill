#!/usr/bin/env python3
"""Static contract checks for user-persona-v8 skill files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from quality_common import Issue, SKILL_ROOT, emit_result, read_text, rel

REQUIRED_REDUCE_CONTRACT = (
    "mentioned_by",
    "evidence_quotes",
    "mention_count",
)

REDUCE_EXCEPTIONS = {
    "reduce_basic_profile.txt",
    "reduce_one_sentence.txt",
    "reduce_quotes.txt",
}


def check_render_report_contract(errors: list[Issue], warnings: list[Issue]) -> None:
    path = SKILL_ROOT / "scripts" / "components" / "render_report.py"
    if not path.exists():
        errors.append(Issue(
            "render_report.missing",
            "P8 渲染入口 render_report.py 不存在。",
            rel(path),
        ))
        return
    text = read_text(path)
    if "assets" not in text or "_base.html" not in text:
        errors.append(Issue(
            "render_report.base_template",
            "render_report.py 必须引用 assets/templates/_base.html。",
            rel(path),
        ))
    if "{{persona_nav}}" not in text and "persona_nav" not in text:
        errors.append(Issue(
            "render_report.nav_slot",
            "render_report.py 必须填充 persona_nav slot。",
            rel(path),
        ))
    for legacy in ("render_html.py", "render_matrix.py", "render_multivariable.py"):
        if (SKILL_ROOT / "scripts" / legacy).exists():
            errors.append(Issue(
                "render.legacy_script",
                f"P7 旧脚本 {legacy} 应已删除,统一走 render_report.py。",
                rel(SKILL_ROOT / "scripts" / legacy),
            ))


def check_templates(errors: list[Issue], warnings: list[Issue]) -> None:
    base = SKILL_ROOT / "assets" / "templates" / "_base.html"
    components = SKILL_ROOT / "assets" / "templates" / "_components.css"
    tokens = SKILL_ROOT / "assets" / "templates" / "_design-tokens.css"
    for path in (base, components, tokens):
        if not path.exists():
            errors.append(Issue("template.missing", "缺少统一视觉系统模板或 CSS。", rel(path)))

    if base.exists():
        base_text = read_text(base)
        for slot in ("{{theme}}", "{{density}}", "{{persona_nav}}", "{{main_content}}"):
            if slot not in base_text:
                errors.append(Issue("base.slot_missing", f"_base.html 缺少 slot {slot}。", rel(base)))
        if ".nav-btn[data-target]" not in base_text:
            errors.append(Issue("base.nav_handler", "_base.html 缺少 data-target 导航委托。", rel(base)))

    legacy = SKILL_ROOT / "assets" / "templates" / "report.html"
    if legacy.exists():
        errors.append(Issue(
            "template.legacy_report",
            "report.html 旧独立模板应已删除,统一使用 _base.html。",
            rel(legacy),
        ))


def check_prompt_contracts(errors: list[Issue], warnings: list[Issue]) -> None:
    prompt_dir = SKILL_ROOT / "assets" / "prompts"
    for path in sorted(prompt_dir.glob("reduce_*.txt")):
        if path.name in REDUCE_EXCEPTIONS:
            continue
        text = read_text(path)
        missing = [token for token in REQUIRED_REDUCE_CONTRACT if token not in text]
        if missing:
            errors.append(Issue(
                "prompt.reduce_contract",
                f"{path.name} 缺少 reduce 证据契约: {', '.join(missing)}。",
                rel(path),
            ))
        if not re.search(r"mention_count\s*=\s*mentioned_by.*evidence_quotes|三者.*一致|三者必须严格相等", text):
            errors.append(Issue(
                "prompt.reduce_three_way",
                f"{path.name} 缺少 mention_count / mentioned_by / evidence_quotes 三向一致规则。",
                rel(path),
            ))


def check_path_contracts(errors: list[Issue], warnings: list[Issue]) -> None:
    scan_paths = [
        *SKILL_ROOT.glob("*.md"),
        *SKILL_ROOT.glob("steps/*.md"),
        *SKILL_ROOT.glob("paradigms/*.md"),
        *SKILL_ROOT.glob("scripts/*.py"),
    ]
    for path in scan_paths:
        text = read_text(path)
        if ".user-persona-work" in text:
            errors.append(Issue(
                "path.legacy_workdir",
                "用户执行路径中仍残留 .user-persona-work,应统一到 用户画像报告输出/<项目名>-<时间>/过程稿。",
                rel(path),
            ))


def check_user_language_leaks(errors: list[Issue], warnings: list[Issue]) -> None:
    user_facing = [
        SKILL_ROOT / "steps" / "research-goal.md",
        SKILL_ROOT / "steps" / "field-alignment.md",
    ]
    leak_patterns = [
        (r"蛇形图", "旧图名"),
        (r"矩阵聚类", "内部图名"),
    ]
    for path in user_facing:
        if not path.exists():
            continue
        text = read_text(path)
        for pattern, label in leak_patterns:
            if re.search(pattern, text):
                errors.append(Issue(
                    "language.internal_term",
                    f"用户话术文件出现 {label}: {pattern}。",
                    rel(path),
                ))
        if "价值变量" in text and "内部" not in text:
            warnings.append(Issue(
                "language.value_variable",
                "用户话术文件出现“价值变量”,请确认上下文是否明确标注为内部术语。",
                rel(path),
                "warning",
            ))


def check_toc_route_gate(errors: list[Issue], warnings: list[Issue]) -> None:
    path = SKILL_ROOT / "SKILL.md"
    text = read_text(path)
    required = [
        "路线选择等待态",
        "用户没有明确选择前,不能进入 Step 2",
        "禁止把研究目标中的",
        "你选 A/B/C/D/E 哪一种",
        "user_confirmed: true",
        "choice_label",
        "choice_reason",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        errors.append(Issue(
            "toc.route_gate_missing",
            f"toC 路线选择闸门缺少关键约束: {', '.join(missing)}。",
            rel(path),
        ))
    if "我会按多区分点方式跑测试" not in text or "禁止输出这类直接推进话术" not in text:
        errors.append(Issue(
            "toc.route_autopick_forbidden",
            "SKILL.md 必须明确禁止 toC 自动选择坐标图或多维分布图后直接推进。",
            rel(path),
        ))


def check_label_confirmation_gate(errors: list[Issue], warnings: list[Issue]) -> None:
    checks = {
        "SKILL.md": [
            "分类词显性确认硬规则",
            "label_confirmed: true",
            "不能进入画像合并和最终渲染",
        ],
        "paradigms/R3-classify-basis.md": [
            "类别命名必须显性确认",
            "label_confirmed",
            "类别名会进入最终报告",
        ],
        "paradigms/R4-2d-matrix.md": [
            "档位名确认闸门",
            "这些词会进入最终报告",
            "label_confirmed",
        ],
        "paradigms/R5-multi-variable.md": [
            "档位名确认闸门",
            "这些词会进入最终报告",
            "label_confirmed",
        ],
    }
    for rel_path, required in checks.items():
        path = SKILL_ROOT / rel_path
        text = read_text(path)
        missing = [token for token in required if token not in text]
        if missing:
            errors.append(Issue(
                "classification.label_gate_missing",
                f"{rel_path} 缺少分类词显性确认约束: {', '.join(missing)}。",
                rel(path),
            ))


def check_journey_dsl_contract(errors: list[Issue], warnings: list[Issue]) -> None:
    """tob_journey L1/L2 文档契约(2026-05-29)。

    1) 死模型不许复活:REGISTRY / steps 不得再以可用形式教 `cross_role_arrows` /
       `role-N/stage-N` 索引语法(schema 不收、渲染器不读,照写会被拦)。
    2) 协同语义指引不许悄悄消失:REGISTRY 必须保留协同门禁说明 + 真值范例指针,
       且渲染器必须真的实现 `_coop_semantics_gate`(文档与代码对齐)。
    """
    registry = SKILL_ROOT / "scripts" / "components" / "REGISTRY.md"
    render_step = SKILL_ROOT / "steps" / "render-persona-page.md"
    renderer = SKILL_ROOT / "scripts" / "components" / "renderers" / "tob_journey.py"

    dead_usage = [
        (r'"cross_role_arrows"', "死 prop cross_role_arrows(应改用 nodes/edges 里跨 lane 的 edge)"),
        (r"role-\d+/stage-\d+", "死的 role-N/stage-N 索引语法(应改用 node id 引用)"),
    ]
    for path in (registry, render_step):
        text = read_text(path)
        for pattern, label in dead_usage:
            if re.search(pattern, text):
                errors.append(Issue(
                    "journey.dead_dsl_resurfaced",
                    f"{rel(path)} 又出现已废弃的 L1 协同写法: {label}。",
                    rel(path),
                ))

    registry_text = read_text(registry)
    for token in ("协同语义门禁", "跨泳道边", "tob_journey_l1_coop.json"):
        if token not in registry_text:
            errors.append(Issue(
                "journey.coop_guidance_missing",
                f"REGISTRY.md 缺少 L1 协同语义指引关键内容: {token}。",
                rel(registry),
            ))

    if "_coop_semantics_gate" not in read_text(renderer):
        errors.append(Issue(
            "journey.coop_gate_missing",
            "tob_journey.py 缺少 _coop_semantics_gate —— 协同语义门禁未实现,文档与代码不一致。",
            rel(renderer),
        ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(SKILL_ROOT), help="skill 根目录,默认自动识别")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root != SKILL_ROOT:
        errors = [Issue("root.unsupported", "当前检查器固定跟随所在 skill 根目录运行。", str(root))]
        return emit_result(check_name="skill_contracts", errors=errors)

    errors: list[Issue] = []
    warnings: list[Issue] = []
    check_path_contracts(errors, warnings)
    check_templates(errors, warnings)
    check_render_report_contract(errors, warnings)
    check_prompt_contracts(errors, warnings)
    check_user_language_leaks(errors, warnings)
    check_toc_route_gate(errors, warnings)
    check_label_confirmation_gate(errors, warnings)
    check_journey_dsl_contract(errors, warnings)
    return emit_result(
        check_name="skill_contracts",
        errors=errors,
        warnings=warnings,
        next_step="先修复模板、路径、prompt 和导航契约问题,再运行数据与 HTML 检查。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
