#!/usr/bin/env python3
"""Quick structural checks on report.html sections."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parents[2] / (
    "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html"
)

ORDER = [
    "journey-l1",
    "persona-1-core",
    "persona-1-detail",
    "persona-1-journey",
    "persona-2-core",
    "persona-2-detail",
    "persona-2-journey",
    "persona-3-core",
    "persona-3-detail",
    "persona-3-journey",
    "persona-4-core",
    "persona-4-detail",
    "persona-4-journey",
    "persona-5-core",
    "persona-5-detail",
    "persona-5-journey",
]


def main() -> int:
    html = REPORT.read_text(encoding="utf-8")
    issues = []

    for sid in ORDER:
        pat = rf'<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>(.*?)</section>'
        m = re.search(pat, html, re.DOTALL)
        if not m:
            issues.append(f"missing section: {sid}")
            continue
        body = m.group(1)
        opens = len(re.findall(r"<div\b", body))
        closes = len(re.findall(r"</div>", body))
        if opens != closes:
            issues.append(f"{sid}: div imbalance open={opens} close={closes}")
        if sid.endswith("-core") and "grid-anchor-start" not in body:
            issues.append(f"{sid}: missing grid-anchor classes")

    actives = [
        sid
        for _, sid in re.findall(
            r'<section class="([^"]*)"[^>]*id="([^"]+)"', html
        )
        if "active" in re.split(r"\s+", _)[0]
    ]
    if len(actives) != 1:
        issues.append(f"active sections: {actives}")

    for msg in issues:
        print("ISSUE:", msg)
    if not issues:
        print("OK: structure checks passed")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
