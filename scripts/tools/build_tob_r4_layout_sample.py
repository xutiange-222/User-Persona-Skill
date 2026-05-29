# -*- coding: utf-8 -*-
"""toB R4 最小构建样板 — 4 象限 + layout-2b-grid + tob_journey_l2。

勿照抄 HiRes build_hires_report.py（仅 toC）。
完整实跑见：docs/reference/reports/D-二维矩阵/2B-电力调度员/report.html

矩阵旅程(思考/行为/痛点/触点) → tob_journey_l2 时：
  - 「思考」行 → focuses.cards 中 is_pain=false（★ 关注点）
  - 「痛点」行 → focuses.cards 中 is_pain=true（⚠ 痛点）
  禁止只导出痛点行且全部 is_pain=true。

用法（在 skill 根目录）:
    python scripts/tools/build_tob_r4_layout_sample.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = SKILL_ROOT / "docs" / "reference" / "layouts" / "_build" / "r4-minimal"
PROC = OUT_DIR / "过程稿"


def _journey_l2(name: str) -> dict:
    return {
        "type": "tob_journey_l2",
        "props": {
            "banner_title": f"{name} · 工作流程",
            "banner_subtitle": "toB R4 样板旅程（最小数据）",
            "stages": [
                {"id": "s1", "name": "发现", "subStages": ["发现"]},
                {"id": "s2", "name": "研判", "subStages": ["研判"]},
                {"id": "s3", "name": "执行", "subStages": ["执行"]},
                {"id": "s4", "name": "复盘", "subStages": ["复盘"]},
            ],
            "lanes": [{"id": "lane1", "name": name[:8]}],
            "nodes": [
                {"id": "n1", "lane": "lane1", "stage": "s1", "type": "step", "label": "接收告警", "slot": 0},
                {"id": "n2", "lane": "lane1", "stage": "s2", "type": "step", "label": "演算方案", "slot": 0},
                {"id": "n3", "lane": "lane1", "stage": "s3", "type": "step", "label": "下发指令", "slot": 0},
                {"id": "n4", "lane": "lane1", "stage": "s4", "type": "step", "label": "归档复盘", "slot": 0},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
                {"from": "n3", "to": "n4"},
            ],
            "focuses": [
                {
                    "title": "信息核对",
                    "body": "限额与联络开关需人工交叉核对，系统未统一时耗时长",
                    "is_pain": True,
                    "evidence": '"负载率都要人工去核对。" — 样板',
                },
                {
                    "title": "算力瓶颈",
                    "body": "多路径转供人工演算曾需一小时以上，影响故障窗口",
                    "is_pain": True,
                    "evidence": '"人工算下来需要至少一个小时以上。" — 样板',
                },
                {
                    "title": "协同验证",
                    "body": "三人值班交叉验证转供方案，电话与网络令并行",
                    "is_pain": False,
                    "evidence": '"不同经验调度员会一起验证方案。" — 样板',
                },
                {
                    "title": "闭环记录",
                    "body": "复盘对比人工与系统结果，沉淀可配置边界条件",
                    "is_pain": False,
                    "evidence": '"大家都用了多长时间验证准不准。" — 样板',
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
                    "identity_desc": f"{name} — toB R4 象限画像样板",
                    "identity_meta_rows": [
                        {"key": "研究类型", "value": "toB"},
                        {"key": "范式", "value": "R4 二维矩阵"},
                    ],
                    "one_sentence_need": {
                        "text": "辅助演算须可解释，最终下令仍由人确认",
                        "source": "样板",
                    },
                },
            },
            {
                "type": "resp_rings",
                "props": {
                    "rings": [
                        {"label": "运行监控与故障处置", "percentage": 50},
                        {"label": "负荷转供方案演算", "percentage": 30},
                        {"label": "协同与复盘归档", "percentage": 20},
                    ]
                },
            },
            {
                "type": "painpoint_list",
                "props": {
                    "items": [
                        {
                            "title": "人工算路耗时",
                            "detail": "多线路转供组合人工可算一整天，影响故障处置窗口（样板）",
                            "mention_badge": "1/1",
                        },
                        {
                            "title": "系统分散",
                            "detail": "限额标准分散在多系统，需人工核对负载率与联络关系（样板）",
                            "mention_badge": "1/1",
                        },
                    ]
                },
            },
        ],
    }


def build_report() -> dict:
    quadrants = [
        ("persona-1", "演算派"),
        ("persona-2", "研判派"),
        ("persona-3", "统筹派"),
        ("persona-4", "协同派"),
    ]
    personas = [
        {
            "id": "matrix",
            "name": "用户矩阵",
            "layout": "layout-matrix-2d",
            "components": [
                {
                    "type": "matrix_guidance_strip",
                    "props": {
                        "items": [
                            {"label": "X轴：组织位置", "hint": "toB R4 样板"},
                            {"label": "Y轴：决策方式", "hint": "toB R4 样板"},
                        ]
                    },
                },
                {
                    "type": "matrix_2d",
                    "props": {
                        "axis_labels": {
                            "top": "方案演算",
                            "bottom": "研判协同",
                            "left": "场站侧",
                            "right": "电网中心",
                        },
                        "quadrants": [
                            {"id": pid, "label": label, "position": f"q{i}"}
                            for i, (pid, label) in enumerate(quadrants, start=1)
                        ],
                        "respondents": [
                            {
                                "x": 75,
                                "y": 25,
                                "display_name": "刘老师",
                                "quadrant_persona": quadrants[0][1],
                                "evidence": [
                                    {
                                        "quote": "人工算下来需要至少一个小时以上。",
                                        "source": "刘老师",
                                    },
                                    {
                                        "quote": "用系统后可以直接 AI 计算满载过载情况。",
                                        "source": "刘老师",
                                    },
                                ],
                            }
                        ],
                    },
                },
            ],
        }
    ]
    for pid, label in quadrants:
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
            "report_title": "toB R4 最小样板",
            "page_title": "toB R4 样板",
            "theme": "2b",
            "density": "high",
            "source_count": 1,
            "persona_count": 4,
            "generated_at": "2026-05-29",
        },
        "personas": personas,
    }


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
    print(f"[OK] {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
