from pathlib import Path

t = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
tail = t[-500:]
idx = tail.find("script")
print("idx in tail", idx)
if idx >= 0:
    frag = tail[max(0, idx - 15) : idx + 20]
    print("repr", repr(frag))
    print("ords", [hex(ord(c)) for c in frag])
