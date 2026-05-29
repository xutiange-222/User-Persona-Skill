import re
from pathlib import Path

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
CORRUPT = ("clas<section", 'class="<section', 'class="t<section')

for sid in ["persona-2-journey", "persona-3-journey", "persona-5-journey"]:
    pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"'
    ms = list(re.finditer(pat, html))
    print(sid, "matches", len(ms))
    for i, m in enumerate(ms):
        rest = html[m.start() :]
        dup = rest.find('<section class="persona-slide', len(m.group(0)))
        chunk = rest[:dup] if dup > 0 else rest[:80000]
        close = chunk.rfind("</section>")
        sec = chunk[: close + len("</section>")] if close >= 0 else ""
        print(
            f"  [{i}] len={len(sec)} corrupt={any(x in sec for x in CORRUPT)} closed={close >= 0}"
        )
