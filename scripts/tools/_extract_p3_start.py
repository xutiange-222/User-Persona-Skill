import re
from pathlib import Path

h = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
m = re.search(r'id="persona-3-core"[^>]*>(.{0,800})', h, re.DOTALL)
out = Path(__file__).parent / "_p3_start.txt"
out.write_text(m.group(1) if m else "NOT FOUND", encoding="utf-8")

# broken tag scan
for needle in ["iv>", '="report-meta', "clas<section", "<di ", "<di>"]:
    print(needle, h.count(needle))
