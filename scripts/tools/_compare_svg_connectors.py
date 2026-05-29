import re
from pathlib import Path

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

for sid in ["persona-1-journey", "persona-2-journey", "persona-3-journey", "persona-4-journey", "persona-5-journey"]:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', html, re.DOTALL)
    if not m:
        print(sid, "MISSING")
        continue
    sec = m.group(1)
    svg_m = re.search(r'<svg class="l1-uml-svg"[^>]*>(.*?)</svg>', sec, re.DOTALL)
    if not svg_m:
        print(sid, "no svg")
        continue
    svg = svg_m.group(0)
    vb = re.search(r'viewBox="([^"]+)"', svg)
    markers = re.findall(r'id="([^"]+)"', svg)
    paths = re.findall(r'<path class="l1-connector[^"]*" d="([^"]+)"', svg)
    nodes = len(re.findall(r'class="l1-node', svg))
    print(f"\n{sid}: viewBox={vb.group(1) if vb else '?'} nodes={nodes} paths={len(paths)} marker_ids={set(markers)}")
    if paths:
        print("  last path:", paths[-1][:80])
        print("  path[-2]:", paths[-2][:80] if len(paths) > 1 else "")
