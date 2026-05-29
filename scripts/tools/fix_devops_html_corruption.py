#!/usr/bin/env python3
"""修复 DevOps report：删除游离 DOM、修正 journey 区段闭合、完整重建 slides。"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

REPORT = Path(__file__).resolve().parents[2] / (
    "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html"
)
BAK = REPORT.parent / "report.html.bak-20260529-161421"

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

CORRUPT_MARKERS = ("clas<section", 'class="<section', 'class="t<section', "</section>/div")
# 勿用 iv></div>：会误匹配正常 </div></div> 中的子串
TRUNCATE_MARKERS = CORRUPT_MARKERS


def fix_journey_close(sec: str) -> str:
    """截断破损闭合标记之后的垃圾，并规范为 </section>。"""
    m = re.match(
        r"(<section class=\"persona-slide[^\"]*\" id=\"[^\"]+\"[^>]*>)(.*)",
        sec,
        re.DOTALL,
    )
    if not m:
        return sec
    body = m.group(2)
    # refresh 脚本会在 </section> 后插入 iv>/div 碎片，须用「首个异常闭合」截断
    corrupt = re.search(r"</section>(?:iv>|/div)", body)
    if corrupt:
        body = body[: corrupt.start()]
    else:
        for marker in TRUNCATE_MARKERS:
            idx = body.find(marker)
            if idx >= 0:
                body = body[:idx]
                break
        close = body.rfind("</section>")
        if close >= 0:
            body = body[:close]
    return m.group(1) + body + "</section>"


def extract_section(html: str, sid: str) -> str | None:
    pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>'
    matches = list(re.finditer(pat, html))
    if not matches:
        return None
    for m in reversed(matches):
        rest = html[m.start() :]
        dup = rest.find('<section class="persona-slide', len(m.group(0)))
        chunk = rest[:dup] if dup > 0 else rest
        if sid.endswith("-journey") or any(x in chunk for x in CORRUPT_MARKERS):
            sec = fix_journey_close(chunk)
        else:
            close = chunk.rfind("</section>")
            if close < 0:
                continue
            sec = chunk[: close + len("</section>")]
            if any(x in sec for x in CORRUPT_MARKERS):
                continue
        if not sec.strip().endswith("</section>"):
            continue
        return sec
    return None


def main() -> None:
    html = REPORT.read_text(encoding="utf-8")
    bak = BAK.read_text(encoding="utf-8") if BAK.is_file() else html

    nav_start = html.find('<div class="demo-nav-area">')
    first_sec = html.find('<section class="persona-slide', nav_start)
    tail_start = html.rfind("  <script>")
    if nav_start < 0 or first_sec < 0 or tail_start < 0:
        raise SystemExit("cannot locate report regions")

    head = html[:nav_start]
    nav = html[nav_start:first_sec]
    tail = html[tail_start:]

    # 导航置于最上层，避免被破损 slide 遮挡
    if "demo-nav-area" in head and "z-index: 100" not in head:
        head = head.replace(
            ".demo-nav-area {",
            ".demo-nav-area {\n      position: relative;\n      z-index: 100;",
            1,
        )
    if ".report-meta-bar {" in head and "z-index: 100" not in head.split(".report-meta-bar {", 1)[1][:80]:
        head = head.replace(
            ".report-meta-bar {",
            ".report-meta-bar {\n      position: relative;\n      z-index: 100;",
            1,
        )

    slides = []
    for sid in ORDER:
        sec = extract_section(html, sid)
        if not sec and sid.endswith("-journey"):
            sec = extract_section(bak, sid)
        if not sec:
            raise SystemExit(f"missing section: {sid}")
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

    verify = REPORT.read_text(encoding="utf-8")
    between = verify[verify.find("demo-nav-area") : verify.rfind("<script>")]
    orphans = [
        o.strip()
        for o in re.findall(
            r"</section>\s*(?!<section)(.+?)(?=<section)",
            between,
            flags=re.DOTALL,
        )
        if o.strip()
    ]
    print(f"backup: {backup.name}")
    print(f"rebuilt sections: {len(slides)}")
    print(f"orphan blocks: {len(orphans)}")
    print(f"</section>/div count: {verify.count('</section>/div')}")
    print(f"iv> count: {verify.count('iv>')}")
    if orphans:
        raise SystemExit("still has orphan HTML between sections")


if __name__ == "__main__":
    main()
