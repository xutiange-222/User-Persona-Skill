import re
from pathlib import Path

p = Path(r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html")
html = p.read_text(encoding="utf-8")
for m in re.finditer(r'<section class="persona-slide[^"]*" id="([^"]+)"', html):
    print(m.group(1))
print("corrupt", "clas<section" in html)
