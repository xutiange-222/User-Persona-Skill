from pathlib import Path
import re

h = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
for m in re.finditer(r".{0,40}iv>.{0,40}", h):
    print(m.group().replace("\n", "\\n"))

i = h.find("demo-nav-area")
j = h.find("<section", i)
nav = h[i:j]
Path(r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\scripts\tools\_nav_snippet.txt").write_text(
    nav, encoding="utf-8"
)
print("nav written", len(nav))

for sid in ["persona-2-journey", "persona-3-core"]:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', h, re.DOTALL)
    if m:
        b = m.group(1)
        print(sid, "div", b.count("<div"), b.count("</div>"))
