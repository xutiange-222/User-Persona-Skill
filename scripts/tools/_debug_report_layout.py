from pathlib import Path

t = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
nav = t.find("demo-nav-area")
print("nav", nav, repr(t[nav - 60 : nav + 80]))
i = t.find('<section class="persona-slide', nav)
print("first section after nav", i, repr(t[i : i + 100]) if i >= 0 else "NONE")
print("script rfind", t.rfind("<script"), t.rfind("  <script>"))
