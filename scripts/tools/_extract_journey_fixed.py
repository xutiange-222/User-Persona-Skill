import re
from pathlib import Path

bak = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html.bak-20260529-161421"
).read_text(encoding="utf-8")

def fix_journey(html: str, sid: str) -> str | None:
    pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>'
    ms = list(re.finditer(pat, html))
    if not ms:
        return None
    m = ms[-1]
    rest = html[m.start() :]
    dup = rest.find('<section class="persona-slide', len(m.group(0)))
    chunk = rest[:dup] if dup > 0 else rest
    m2 = re.match(
        rf'(<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>)(.*)',
        chunk,
        re.DOTALL,
    )
    if not m2:
        return None
    body = m2.group(2)
    for marker in ("</section>/div", 'class="t<section', "clas<section"):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
            break
    close = body.rfind("</section>")
    if close >= 0:
        body = body[:close]
    return m2.group(1) + body + "</section>"


for sid in ["persona-3-journey", "persona-4-journey", "persona-5-journey"]:
    sec = fix_journey(bak, sid)
    print(sid, "ok" if sec else "FAIL", "len", len(sec) if sec else 0)
    if sec:
        print("  tail", repr(sec[-60:]))
