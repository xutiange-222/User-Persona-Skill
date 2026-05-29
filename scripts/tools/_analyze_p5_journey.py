import re
from pathlib import Path

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
sid = "persona-5-journey"
pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"'
ms = list(re.finditer(pat, html))
m = ms[-1]
rest = html[m.start() :]
dup = rest.find('<section class="persona-slide', len(m.group(0)))
chunk = rest[:dup] if dup > 0 else rest[:20000]
close = chunk.rfind("</section>")
sec = chunk[: close + len("</section>")]
print("len", len(sec))
print("tail20", repr(sec[-80:]))
print("has script", "addEventListener" in sec)
