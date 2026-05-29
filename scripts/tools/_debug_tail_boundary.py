import re
from pathlib import Path

t = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")
last = list(re.finditer(r"</section>", t))[-1]
print("last </section> at", last.end())
print(repr(t[last.end() : last.end() + 120]))

v8 = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-v8\用户画像报告输出\DevOps平台多角色-20260528-1432\最终交付件-2B-DevOps平台-5用户-多角色旅程\report.html"
).read_text(encoding="utf-8")
ts = v8.find("  <script>")
print("v8 script at", ts)
