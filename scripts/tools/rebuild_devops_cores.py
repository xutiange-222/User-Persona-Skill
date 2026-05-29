#!/usr/bin/env python3
"""用 05-report.json 重渲染 persona-3/4/5-core，修复 V9 样例缺 grid-anchor 的布局。"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V9))

from scripts.components.layouts.assemble import ASSEMBLERS

REPORT = V9 / "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html"
JSON_PATH = (
    V9.parent
    / "user-persona-v8/用户画像报告输出/DevOps平台多角色-20260528-1432/过程稿/05-report.json"
)

AVATARS = {
    "persona-3-core": ("测试体系管理者", "assets/画像头像素材/测试体系管理者.png"),
    "persona-4-core": ("一线测试负责人", "assets/画像头像素材/一线测试负责人.png"),
    "persona-5-core": ("交付型SM", "assets/画像头像素材/交付型SM.png"),
}


def _render_core(persona: dict, slide_id: str, metadata: dict) -> str:
    p = dict(persona)
    p["id"] = slide_id.replace("-core", "")
    slides = ASSEMBLERS["layout-2b-grid"](p, metadata)
    core_id = f'{p["id"]}-core'
    sec = next((s for s in slides if f'id="{core_id}"' in s), slides[0])
    sec = sec.replace(f'id="{p["id"]}"', f'id="{slide_id}"', 1)
    name, src = AVATARS[slide_id]
    sec = re.sub(
        r'<div class="persona-avatar[^"]*">[^<]*</div>|<img class="persona-avatar"[^>]*>',
        f'<img class="persona-avatar" src="{src}" alt="{name}">',
        sec,
        count=1,
    )
    return re.sub(r"(<section[^>]*)\sactive\b", r"\1", sec, count=1)


def _replace_section(html: str, slide_id: str, new_sec: str) -> str:
    pat = rf'<section class="persona-slide[^"]*" id="{re.escape(slide_id)}"[^>]*>.*?</section>'
    m = re.search(pat, html, flags=re.DOTALL)
    if not m:
        raise ValueError(f"section not found: {slide_id}")
    return html[: m.start()] + new_sec + html[m.end() :]


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    metadata = data["metadata"]
    by_id = {p["id"]: p for p in data["personas"]}

    html = REPORT.read_text(encoding="utf-8")
    backup = REPORT.with_name(
        f"report.html.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    shutil.copy2(REPORT, backup)

    mapping = {
        "persona-3-core": "persona-3",
        "persona-4-core": "persona-4",
        "persona-5-core": "persona-5",
    }
    for slide_id, pid in mapping.items():
        sec = _render_core(by_id[pid], slide_id, metadata)
        html = _replace_section(html, slide_id, sec)
        print(f"rebuilt {slide_id}")

    REPORT.write_text(html, encoding="utf-8")
    print(f"backup: {backup.name}")
    print(f"updated: {REPORT}")


if __name__ == "__main__":
    main()
