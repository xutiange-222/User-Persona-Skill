from pathlib import Path

h = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
i = h.find("demo-nav-area")
j = h.find("<section", i)
print(h[i - 400 : j + 80])
