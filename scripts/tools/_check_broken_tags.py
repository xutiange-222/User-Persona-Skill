import re
from pathlib import Path

h = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

for sid in ["persona-3-core", "persona-4-core", "persona-5-core"]:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', h, re.DOTALL)
    if not m:
        print(sid, "MISSING")
        continue
    b = m.group(1)
    bad = [x for x in ["<di ", "<di>", "</di>", "modules-panel\"><di"] if x in b]
    print(sid, "len", len(b), "bad", bad)
    idx = b.find("modules-panel")
    if idx >= 0:
        print("  snippet:", repr(b[idx : idx + 80]))

# duplicate ids
ids = re.findall(r'\bid="([^"]+)"', h)
from collections import Counter
dups = [k for k, v in Counter(ids).items() if v > 1]
print("duplicate ids:", dups[:20])

# nav targets vs sections
targets = re.findall(r'data-target="([^"]+)"', h.split("<script")[0])
sections = set(re.findall(r'<section[^>]*\bid="([^"]+)"', h))
missing = [t for t in targets if t not in sections]
print("nav targets missing section:", missing)
