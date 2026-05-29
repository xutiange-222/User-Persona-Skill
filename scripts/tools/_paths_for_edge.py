import re
import sys
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V9))

from scripts.tools.refresh_l2_uml_in_reports import _parse_l2_section
from scripts.components.renderers.tob_journey import _render_uml_journey

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

sid = "persona-2-journey"
m = re.search(
    rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>(.*?)</section>',
    html,
    re.DOTALL,
)
props = _parse_l2_section(m.group(1))
props["marker_id"] = "persona_2_journey"
uml = _render_uml_journey(props, show_lane_rail=False, density_mode="l2", validate_density=False)

NODE_RE = re.compile(
    r'<g class="l1-node l1-(\w+)" transform="translate\(([\d.]+) ([\d.]+)\)">'
    r'[\s\S]*?class="l1-node-label[^"]*">([^<]+)</div>'
)
print("Rendered nodes:")
for typ, x, y, label in NODE_RE.findall(uml):
    print(f"  {label}: translate({x},{y})")

print("\nEdges:")
by_id = {n["id"]: n["label"] for n in props["nodes"]}
for e in props["edges"]:
    print(f"  {by_id[e['from']]} -> {by_id[e['to']]}")

paths = re.findall(r'<path class="l1-connector[^"]*" d="([^"]+)"', uml)
print("\nLast two paths:", paths[-2:])
