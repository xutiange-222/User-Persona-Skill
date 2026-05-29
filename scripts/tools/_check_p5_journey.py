import re
from pathlib import Path

p = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
)
html = p.read_text(encoding="utf-8")
m = re.search(r'id="persona-5-journey"[^>]*>(.*)</section>', html, re.DOTALL)
print("len", len(m.group(1)) if m else 0)
if m:
    print("tail", repr(m.group(0)[-200:]))

bak = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html.bak-20260529-162435"
)
bh = bak.read_text(encoding="utf-8")
ms = list(re.finditer(r'id="persona-5-journey"', bh))
print("bak count", len(ms))
for i, m in enumerate(ms):
    rest = bh[m.start() : m.start() + 500]
    print(i, rest[:120])
