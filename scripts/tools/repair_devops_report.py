#!/usr/bin/env python3
"""修复 refresh_l2 多次替换导致的 HTML 错位（按 section id 保留首段合法闭合）。"""
from __future__ import annotations

import re
from pathlib import Path

REPORT = (
    Path(__file__).resolve().parents[2]
    / "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html"
)

SECTION_RE = re.compile(
    r'<section class="persona-slide[^"]*" id="([^"]+)"[^>]*>',
    re.MULTILINE,
)


def extract_sections(html: str) -> tuple[str, str, dict[str, str]]:
    """head + tail(nav 前) + {id: section_html 含闭合}"""
    nav_m = re.search(r'<div class="demo-nav-area">', html)
    if not nav_m:
        raise SystemExit("demo-nav-area not found")
    head = html[: nav_m.start()]
    rest = html[nav_m.start() :]
    script_m = re.search(r"<script>", rest)
    tail = rest[script_m.start() :] if script_m else ""

    main = rest[: script_m.start() if script_m else len(rest)]
    nav_m2 = re.match(r"(<div class="demo-nav-area">.*?</div>)", main, re.DOTALL)
    nav_html = nav_m2.group(1) if nav_m2 else ""
    slides_blob = main[len(nav_html) :] if nav_m2 else main

    ids = [m.group(1) for m in SECTION_RE.finditer(slides_blob)]
    sections: dict[str, str] = {}
    for i, sid in enumerate(ids):
        start = slides_blob.find(f'id="{sid}"')
        if i + 1 < len(ids):
            next_id = ids[i + 1]
            end = slides_blob.find(f'id="{next_id}"', start + 1)
        else:
            end = len(slides_blob)
        chunk = slides_blob[start:end]
        # 从 <section 起截到该段最后一个 </section>
        sec_start = chunk.find("<section")
        if sec_start < 0:
            continue
        chunk = chunk[sec_start:]
        close_idx = chunk.rfind("</section>")
        if close_idx < 0:
            continue
        sec_html = chunk[: close_idx + len("</section>")]
        if "clas<section" in sec_html or 'class="<section' in sec_html or 'class="t<section' in sec_html:
            continue
        if sid not in sections:
            sections[sid] = sec_html

    return head, nav_html + "\n", sections


def main() -> None:
    html = REPORT.read_text(encoding="utf-8")
    head, nav_and_newline, sections = extract_sections(html)
    order = [
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
    missing = [k for k in order if k not in sections]
    if missing:
        raise SystemExit(f"missing sections after repair: {missing}")

    script_m = re.search(r"<script>.*</script>\s*</body>\s*</html>", html, re.DOTALL)
    if not script_m:
        raise SystemExit("script tail not found")
    tail = html[script_m.start() :]

    slides = "\n".join(sections[k] for k in order)
    out = head + nav_and_newline + slides + "\n" + tail
    REPORT.write_text(out, encoding="utf-8")
    print(f"repaired {REPORT.name}: {len(sections)} sections")
    if missing:
        print("still missing:", missing)


if __name__ == "__main__":
    main()
