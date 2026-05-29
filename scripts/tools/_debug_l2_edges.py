import re
import sys
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V9))

from scripts.tools.refresh_l2_uml_in_reports import _parse_l2_section

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

for sid in ["persona-1-journey", "persona-2-journey"]:
    m = re.search(
        rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>(.*?)</section>',
        html,
        re.DOTALL,
    )
    props = _parse_l2_section(m.group(1))
    print(f"\n{sid} nodes={len(props['nodes'])} edges={len(props['edges'])}")
    by_id = {n["id"]: n["label"] for n in props["nodes"]}
    for e in props["edges"]:
        print(f"  {by_id[e['from']]} -> {by_id[e['to']]}" + (f" ({e.get('branch')})" if e.get("branch") else ""))
