import re
from pathlib import Path

bak = Path(
    r"C:\Users\HUAWEI\.claude\skills\user-persona-V9\docs\reference\reports\B-多角色\2B-DevOps五角色\report.html.bak-20260529-162435"
).read_text(encoding="utf-8")

sid = "persona-2-journey"
pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>'
m = list(re.finditer(pat, bak))[-1]
rest = bak[m.start() :]
dup = rest.find('<section class="persona-slide', len(m.group(0)))
chunk = rest[:dup]
first_close = chunk.find("</section>")
body = chunk[len(m.group(0)) - (m.start() - m.start()) :]  # noqa
open_tag = re.match(r"<section[^>]*>", chunk).group(0)
body = chunk[len(open_tag) : first_close]
print("open len", len(open_tag), "body len", len(body), "tail body", repr(body[-80:]))
print("after first close", repr(chunk[first_close : first_close + 30]))
