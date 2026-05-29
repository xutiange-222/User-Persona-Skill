import re
from pathlib import Path

h = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
for sid in ["persona-3-core", "persona-4-core", "persona-5-core"]:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', h, re.DOTALL)
    b = m.group(1)
    print(sid, "div", b.count("<div"), b.count("</div>"), "anchor", "grid-anchor-start" in b)
