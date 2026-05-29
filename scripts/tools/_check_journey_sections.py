import re
from pathlib import Path

bak = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html.bak-20260529-161421"
).read_text(encoding="utf-8")

for sid in ["persona-3-journey", "persona-4-journey", "persona-5-journey"]:
    ms = list(re.finditer(rf'id="{sid}"', bak))
    print(sid, "count", len(ms))
    for i, m in enumerate(ms):
        rest = bak[m.start() :]
        dup = rest.find('<section class="persona-slide', 20)
        chunk = rest[:dup] if dup > 0 else rest[:20000]
        close = chunk.rfind("</section>")
        bad = "</section>/div" in chunk or "clas<section" in chunk
        print(f"  [{i}] close={close} bad={bad} len={len(chunk[:close+10] if close>=0 else b'')}")
