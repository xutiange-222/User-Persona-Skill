#!/usr/bin/env python3
"""将模板 CSS、裁切截图与 2C 专题页 HTML 结构同步到 docs/reference/reports/。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
REPORTS = V9 / "docs/reference/reports"
TEMPLATE_CSS = V9 / "assets/templates/_components.css"
ASSET_SOURCE = REPORTS / "A-单画像/2C-内行场景派/assets"


def patch_l2c_detail_html(html: str) -> tuple[str, int]:
    changes = 0
    if 'l2c-body"><div><div class="mockup-list' in html:
        html = html.replace(
            'l2c-body"><div><div class="mockup-list',
            'l2c-body"><div class="l2c-col-mockup"><div class="mockup-list',
        )
        changes += 1
    if '</div></div></div><div><div class="l2c-analysis' in html:
        html = html.replace(
            '</div></div></div><div><div class="l2c-analysis',
            '</div></div></div><div class="l2c-col-analysis"><div class="l2c-analysis',
        )
        changes += 1
    new_html, n = re.subn(
        r'<div class="mockup-frame"><img class="mockup-img"',
        r'<div class="mockup-frame mockup-frame--has-img"><img class="mockup-img"',
        html,
    )
    changes += n
    return new_html, changes


def sync_css(report_dir: Path) -> None:
    css = report_dir / "_components.css"
    if css.exists():
        shutil.copy2(TEMPLATE_CSS, css)


def sync_screenshots(shot_dir: Path) -> None:
    src_shots = ASSET_SOURCE / "界面截图"
    if not src_shots.is_dir():
        raise SystemExit(f"missing source shots: {src_shots}")
    shot_dir.mkdir(parents=True, exist_ok=True)
    for f in src_shots.glob("hires-*.png"):
        dest = shot_dir / f.name
        if dest.resolve() == f.resolve():
            continue
        shutil.copy2(f, dest)


def main() -> None:
    if not TEMPLATE_CSS.is_file():
        raise SystemExit(f"missing template: {TEMPLATE_CSS}")
    if not ASSET_SOURCE.is_dir():
        raise SystemExit(f"missing asset source: {ASSET_SOURCE}")

    for report in sorted(REPORTS.rglob("report.html")):
        report_dir = report.parent
        sync_css(report_dir)

        html = report.read_text(encoding="utf-8")
        html, n = patch_l2c_detail_html(html)
        if n:
            report.write_text(html, encoding="utf-8")
            print(f"html patch ({n}): {report_dir.relative_to(V9)}")

        shot_dir = report_dir / "assets" / "界面截图"
        if ("layout-2c-detail" in html or "hires-" in html) and shot_dir.parent.parent != ASSET_SOURCE.parent:
            sync_screenshots(shot_dir)
            print(f"screenshots: {report_dir.relative_to(V9)}")

    # 其余含 assets/ 的样例同步界面截图(不覆盖整包,保留各报告自有头像命名)
    for assets in REPORTS.rglob("assets"):
        if assets.resolve() == ASSET_SOURCE.resolve():
            continue
        if (assets / "界面截图").is_dir():
            sync_screenshots(assets / "界面截图")

    print("done: docs/reference/reports/")


if __name__ == "__main__":
    main()
