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

sid = "persona-1-journey"
m = re.search(
    rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>(.*?)</section>',
    html,
    re.DOTALL,
)
props = _parse_l2_section(m.group(1))
by = {n["id"]: n["label"] for n in props["nodes"]}
print("nodes (x order):")
for n in sorted(props["nodes"], key=lambda n: props and 0):
    pass
from scripts.tools.refresh_l2_uml_in_reports import _parse_l2_section as p2

# re-get centers from parse - use node labels
import re as re2
NODE_RE = re2.compile(
    r'<g class="l1-node l1-(\w+)" transform="translate\(([\d.]+) ([\d.]+)\)">'
    r'[\s\S]*?class="l1-node-label[^"]*">([^<]+)</div>'
)
uml = re2.search(r"tob-l2-uml-cell\">(.*?)tob-focus-cell", m.group(1), re.DOTALL)
for typ, x, y, label in sorted(NODE_RE.findall(uml.group(1)), key=lambda t: float(t[1])):
    print(f"  {float(x):6.0f} {label} ({typ})")

print("\nedges:")
for e in props["edges"]:
    br = f" [{e.get('branch')}]" if e.get("branch") else ""
    print(f"  {by[e['from']]} -> {by[e['to']]}{br}")

props["marker_id"] = "persona_1_journey"
uml_html = _render_uml_journey(props, show_lane_rail=False, density_mode="l2", validate_density=False)
paths = re.findall(r'<path class="l1-connector[^"]*" d="([^"]+)"', uml_html)
print("\npaths:")
for e, d in zip(props["edges"], paths):
    print(f"  {by[e['from']]} -> {by[e['to']]}: {d}")
