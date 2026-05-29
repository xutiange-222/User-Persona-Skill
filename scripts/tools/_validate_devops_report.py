import re
from pathlib import Path

p = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
)
html = p.read_text(encoding="utf-8")

ids = re.findall(r'<section[^>]*\sid="([^"]+)"', html)
print("section count", len(ids))
from collections import Counter
c = Counter(ids)
dups = {k: v for k, v in c.items() if v > 1}
print("duplicate ids", dups)

nav_start = html.find("demo-nav-area")
script_start = html.rfind("<script>")
between = html[nav_start:script_start]
orphans = re.findall(
    r"</section>\s*(?!<section)(.+?)(?=<section)",
    between,
    flags=re.DOTALL,
)
orphans = [o.strip() for o in orphans if o.strip()]
print("orphan blocks", len(orphans))
for i, o in enumerate(orphans[:5]):
    print(f"  [{i}] len={len(o)} {o[:120]!r}")

for bad in ("</section>/div", "clas<section", "iv>", "<script"):
    print(bad, html.count(bad))

# div balance per section
for sid in sorted(set(ids)):
    m = re.search(rf'<section[^>]*id="{re.escape(sid)}"[^>]*>(.*)</section>', html, re.DOTALL)
    if not m:
        print(sid, "NO MATCH")
        continue
    body = m.group(1)
    opens = body.count("<div")
    closes = body.count("</div>")
    if opens != closes:
        print(sid, f"div imbalance {opens} vs {closes}")

# nav targets vs sections
targets = re.findall(r'data-target="([^"]+)"', html[:script_start])
missing = [t for t in targets if t not in ids]
print("nav targets missing section", missing)
