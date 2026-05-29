#!/usr/bin/env python3
"""恢复 DevOps 样例 report.html（修复 refresh_l2 破坏的 Tab 结构）。"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
REPORT = V9 / "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html"
V8_REPORT = (
    V9.parent / "user-persona-v8/用户画像报告输出/DevOps平台多角色-20260528-1432"
    / "最终交付件-2B-DevOps平台-5用户-多角色旅程/report.html"
)
TAIL_REF = V9 / "docs/reference/reports/D-二维矩阵/2B-电力调度员/report.html"

ORDER = [
    "journey-l1",
    "persona-1-core",
    "persona-1-detail",
    "persona-1-journey",
    "persona-2-core",
    "persona-2-detail",
    "persona-2-journey",
    "persona-3-core",
    "persona-3-detail",
    "persona-3-journey",
    "persona-4-core",
    "persona-4-detail",
    "persona-4-journey",
    "persona-5-core",
    "persona-5-detail",
    "persona-5-journey",
]

CORRUPT_MARKERS = ('clas<section', 'class="<section', 'class="t<section')
SECTION_OPEN = r'<section class="persona-slide[^"]*" id="{}"[^>]*>'

AVATAR_BY_CORE = {
    "persona-3-core": ("测试体系管理者", "assets/画像头像素材/测试体系管理者.png"),
    "persona-4-core": ("一线测试负责人", "assets/画像头像素材/一线测试负责人.png"),
    "persona-5-core": ("交付型SM", "assets/画像头像素材/交付型SM.png"),
}


def extract_section(html: str, sid: str) -> str | None:
    pat = SECTION_OPEN.format(re.escape(sid))
    matches = list(re.finditer(pat, html))
    if not matches:
        return None
    for m in reversed(matches):
        rest = html[m.start() :]
        dup = rest.find('<section class="persona-slide', len(m.group(0)))
        chunk = rest[:dup] if dup > 0 else rest
        close = chunk.rfind("</section>")
        if close < 0:
            continue
        sec = chunk[: close + len("</section>")]
        if any(x in sec for x in CORRUPT_MARKERS):
            continue
        return sec
    return None


def patch_v8_core_avatar(sec: str, sid: str) -> str:
    info = AVATAR_BY_CORE.get(sid)
    if not info:
        return sec
    name, src = info
    return re.sub(
        r'<div class="persona-avatar placeholder">[^<]+</div>',
        f'<img class="persona-avatar" src="{src}" alt="{name}">',
        sec,
        count=1,
    )


def main() -> None:
    v9 = REPORT.read_text(encoding="utf-8")
    v8 = V8_REPORT.read_text(encoding="utf-8") if V8_REPORT.is_file() else ""

    nav_start = v9.find('<div class="demo-nav-area">')
    first_sec = v9.find('<section class="persona-slide', nav_start)
    if nav_start < 0 or first_sec < 0:
        raise SystemExit("cannot locate nav / sections in V9 report")

    tail_ref = TAIL_REF.read_text(encoding="utf-8") if TAIL_REF.is_file() else ""
    tail_m = re.search(
        r"\n\s*<!-- ============ Tooltip JS.*?</html>\s*$",
        tail_ref,
        flags=re.DOTALL,
    )
    if not tail_m:
        raise SystemExit("cannot extract tooltip/tab script tail from reference report")

    head = v9[:nav_start]
    nav = v9[nav_start:first_sec]
    tail = tail_m.group(0)

    slides = []
    for sid in ORDER:
        sec = extract_section(v9, sid)
        if not sec and v8:
            sec = extract_section(v8, sid)
            if sec and sid in AVATAR_BY_CORE:
                sec = patch_v8_core_avatar(sec, sid)
        if not sec:
            raise SystemExit(f"cannot restore section: {sid}")
        if sid == "journey-l1":
            sec = re.sub(
                r'class="persona-slide[^"]*"',
                'class="persona-slide active layout-2b-journey is-l1"',
                sec,
                count=1,
            )
        else:
            sec = re.sub(r"(<section[^>]*)\sactive\b", r"\1", sec, count=1)
        slides.append(sec)

    backup = REPORT.with_name(
        f"report.html.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    shutil.copy2(REPORT, backup)

    out = head + nav + "\n\n" + "\n".join(slides) + "\n\n" + tail
    REPORT.write_text(out, encoding="utf-8")
    print(f"backup: {backup.name}")
    print(f"restored {REPORT.name} ({len(slides)} slides)")


if __name__ == "__main__":
    main()
