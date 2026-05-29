import re
import sys
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V9))
from scripts.tools.refresh_l2_uml_in_reports import _parse_l2_section

html = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html"
).read_text(encoding="utf-8")

checks = [
    ("persona-1-journey", "接口齐了吗", "日志定位"),
    ("persona-2-journey", "环境验证", "通知研发"),
    ("persona-3-journey", "发布门禁", "复盘整改"),
    ("persona-4-journey", "提交缺陷", "跟踪报告"),
    ("persona-5-journey", "协调发布", "发布清单"),
]

for sid, a, b in checks:
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', html, re.DOTALL)
    props = _parse_l2_section(m.group(1))
    labels = {n["id"]: n["label"] for n in props["nodes"]}
    ok = any(labels[e["from"]] == a and labels[e["to"]] == b for e in props["edges"])
    print(sid, f"{a} -> {b}", "OK" if ok else "MISSING")
