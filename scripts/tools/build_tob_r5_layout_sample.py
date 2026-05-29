# -*- coding: utf-8 -*-
"""toB R5 最小构建样板 — 多维分布总览 + layout-2b-grid + tob_journey_l2。

勿照抄 HiRes toC R5 脚本。
参考：scripts/tools/build_tob_r4_layout_sample.py

用法（在 skill 根目录）:
    python scripts/tools/build_tob_r5_layout_sample.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = SKILL_ROOT / "docs" / "reference" / "layouts" / "_build" / "r5-minimal"
LAYOUTS = SKILL_ROOT / "docs" / "reference" / "layouts"
PROC = OUT_DIR / "过程稿"

_LEVELS = [
    {"level": "high", "name": "高档表现"},
    {"level": "middle", "name": "中档表现"},
    {"level": "low", "name": "低档表现"},
]


def _journey_l2(name: str) -> dict:
    return {
        "type": "tob_journey_l2",
        "props": {
            "banner_title": f"{name} · 工作流程",
            "banner_subtitle": "toB R5 样板旅程（最小数据）",
            "stages": [
                {"id": "s1", "name": "发现", "subStages": ["发现"]},
                {"id": "s2", "name": "研判", "subStages": ["研判"]},
                {"id": "s3", "name": "执行", "subStages": ["执行"]},
            ],
            "lanes": [{"id": "lane1", "name": name[:8]}],
            "nodes": [
                {"id": "n1", "lane": "lane1", "stage": "s1", "type": "step", "label": "接收需求", "slot": 0},
                {"id": "n2", "lane": "lane1", "stage": "s2", "type": "step", "label": "分析方案", "slot": 0},
                {"id": "n3", "lane": "lane1", "stage": "s3", "type": "step", "label": "落地执行", "slot": 0},
            ],
            "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
            "focuses": [
                {
                    "title": "信息分散",
                    "body": "多系统取数需人工汇总，影响研判时效（样板）",
                    "is_pain": True,
                    "evidence": '"不同平台需要分别导出再汇总。" — 样板',
                },
                {
                    "title": "协同成本",
                    "body": "跨部门确认环节多，方案推进周期拉长（样板）",
                    "is_pain": True,
                    "evidence": '"电话确认和邮件来回较多。" — 样板',
                },
                {
                    "title": "闭环复盘",
                    "body": "执行后需归档经验，便于下次同类场景复用（样板）",
                    "is_pain": False,
                    "evidence": '"每次都会记录耗时和结果。" — 样板',
                },
            ],
            "focus_mode": "text",
        },
    }


def _persona_grid(pid: str, name: str) -> dict:
    return {
        "id": pid,
        "name": name,
        "layout": "layout-2b-grid",
        "components": [
            {
                "type": "identity_panel",
                "props": {
                    "persona_avatar": {"alt": name[:2]},
                    "identity_name": {"name": name[:12]},
                    "identity_desc": f"{name} — toB R5 类别画像样板",
                    "identity_meta_rows": [
                        {"key": "研究类型", "value": "toB"},
                        {"key": "范式", "value": "R5 多维分布"},
                    ],
                    "one_sentence_need": {
                        "text": "辅助分析须可解释，关键决策仍由人确认",
                        "source": "样板",
                    },
                },
            },
            {
                "type": "resp_rings",
                "props": {
                    "rings": [
                        {"label": "日常监控与响应", "percentage": 45},
                        {"label": "方案分析与协同", "percentage": 35},
                        {"label": "复盘与优化", "percentage": 20},
                    ]
                },
            },
            {
                "type": "painpoint_list",
                "props": {
                    "items": [
                        {
                            "title": "多源数据汇总慢",
                            "detail": "跨平台导出再人工对齐字段口径，研判前数据准备往往耗去半个班次（样板）",
                            "mention_badge": "1/1",
                        },
                        {
                            "title": "协同确认链条长",
                            "detail": "跨部门电话邮件来回确认方案细节，推进周期拉长且难以预估（样板）",
                            "mention_badge": "1/1",
                        },
                    ]
                },
            },
        ],
    }


def build_report() -> dict:
    persona_defs = [
        ("persona-1", "演算优先派", "high", "middle", "high"),
        ("persona-2", "研判协同派", "middle", "high", "middle"),
    ]
    personas = [
        {
            "id": "distribution",
            "name": "多维分布",
            "layout": "layout-distribution-multi",
            "components": [
                {
                    "type": "distribution_multi",
                    "props": {
                        "title": "toB R5 多维分布样板",
                        "subtitle": "总览页结构共用，配色随 theme=2b",
                        "footer_hint": "点击图例切换类别画像",
                        "value_variables": [
                            {"name": "决策方式", "levels": _LEVELS},
                            {"name": "协同深度", "levels": _LEVELS},
                            {"name": "工具依赖", "levels": _LEVELS},
                        ],
                        "personas": [
                            {
                                "id": pid,
                                "name": label,
                                "color": "#4A6FA5" if i == 0 else "#6B8E6B",
                                "positions": [
                                    {"variable_idx": 0, "level": p0},
                                    {"variable_idx": 1, "level": p1},
                                    {"variable_idx": 2, "level": p2},
                                ],
                                "respondents": ["刘老师"],
                            }
                            for i, (pid, label, p0, p1, p2) in enumerate(persona_defs)
                        ],
                    },
                }
            ],
        }
    ]
    for pid, label, *_ in persona_defs:
        personas.append(_persona_grid(pid, label))
        personas.append(
            {
                "id": f"{pid}-journey",
                "name": label,
                "layout": "layout-2b-journey",
                "components": [_journey_l2(label)],
            }
        )
    return {
        "metadata": {
            "report_title": "toB R5 最小样板",
            "page_title": "toB R5 多维分布样板",
            "theme": "2b",
            "density": "high",
            "source_count": 1,
            "persona_count": 2,
            "generated_at": "2026-05-29",
        },
        "personas": personas,
    }


def sync_regression(html_path: Path) -> None:
    LAYOUTS.mkdir(parents=True, exist_ok=True)
    dest = LAYOUTS / "2B-R5多维-样板.html"
    shutil.copy2(html_path, dest)
    for css in ("_components.css", "_design-tokens.css"):
        src = html_path.parent / css
        if src.exists():
            shutil.copy2(src, LAYOUTS / css)


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    report_path = PROC / "05-report.json"
    report_path.write_text(
        json.dumps(build_report(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    out_html = OUT_DIR / "report.html"
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "scripts" / "components" / "render_report.py"),
        "--input",
        str(report_path),
        "--output",
        str(out_html),
    ]
    subprocess.run(cmd, check=True, cwd=str(SKILL_ROOT))
    sync_regression(out_html)
    print(f"[OK] {out_html}")
    print(f"[OK] {LAYOUTS / '2B-R5多维-样板.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
