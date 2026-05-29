import re
from pathlib import Path

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

NODE_RE = re.compile(
    r'<g class="l1-node l1-(\w+)" transform="translate\(([\d.]+) ([\d.]+)\)">'
    r'[\s\S]*?class="l1-node-label[^"]*">([^<]+)</div>'
)

for sid in ["persona-1-journey", "persona-2-journey"]:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', html, re.DOTALL)
    sec = m.group(1)
    uml = re.search(r"tob-l2-uml-cell\">(.*?)tob-focus-cell", sec, re.DOTALL)
    if not uml:
        continue
    print(f"\n=== {sid} ===")
    for typ, x, y, label in NODE_RE.findall(uml.group(1)):
        print(f"  {float(x)+40:6.0f},{float(y)+14:3.0f} {typ:8} {label}")
