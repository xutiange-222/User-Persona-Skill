import re
from pathlib import Path

bak = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html.bak-20260529-162435"
).read_text(encoding="utf-8")

for sid in ["persona-3-journey", "persona-4-journey", "persona-5-journey"]:
    pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>'
    ms = list(re.finditer(pat, bak))
    m = ms[-1]
    rest = bak[m.start() :]
    dup = rest.find('<section class="persona-slide', len(m.group(0)))
    chunk = rest[:dup] if dup > 0 else rest[:15000]
    idx = chunk.find("iv></div>")
    print(sid, "chunk len", len(chunk), "first iv></div> at", idx)
    if idx >= 0:
        print("  context", repr(chunk[max(0, idx - 40) : idx + 40]))
