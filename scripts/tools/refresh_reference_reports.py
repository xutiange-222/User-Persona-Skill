#!/usr/bin/env python3
"""一键刷新 docs/reference/reports/ 六份说明书样例。

顺序: 重渲染(可用 JSON 的样例) → 同步模板 CSS → 写入 assets → 裁切 A 单画像 → 结构补丁。

用法（skill 根目录）:
    python scripts/tools/refresh_reference_reports.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
V8 = V9.parent / "user-persona-v8"
REPORTS = V9 / "docs/reference/reports"
TEMPLATE = V9 / "assets/templates"

HIRES_R4_JSON = (
    V8
    / "用户画像报告输出/HiRes音乐专区-20260528-启动/过程稿/05-report.json"
)
HIRES_R4_OUT = REPORTS / "D-二维矩阵/2C-HiRes-2维"
HIRES_R5_SRC = (
    V8
    / "用户画像报告输出/HiRes音乐专区-20260528-启动/最终交付件-2C-华为音乐HiRes专区-5用户-多区分点"
)
HIRES_R5_OUT = REPORTS / "E-多维分布/2C-HiRes-多区分点"

STALE_MARKERS = (
    "snake-axis-x-sublabel",
    "respondent-label label-",
    'class="matrix-respondent-dot"></div><span class="respondent-label',
)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=V9, check=True)


def sync_template_css() -> None:
    for name in ("_components.css", "_design-tokens.css"):
        src = TEMPLATE / name
        for dest in REPORTS.rglob(name):
            shutil.copy2(src, dest)
    print("synced template CSS → docs/reference/reports/")


def rerender_hires_r4() -> None:
    if not HIRES_R4_JSON.is_file():
        print(f"[skip] missing {HIRES_R4_JSON}")
        return
    run(
        [
            sys.executable,
            "scripts/components/render_report.py",
            "--input",
            str(HIRES_R4_JSON),
            "--output",
            str(HIRES_R4_OUT / "report.html"),
        ]
    )


def refresh_hires_r5() -> None:
    src_report = HIRES_R5_SRC / "report.html"
    if not src_report.is_file():
        print(f"[skip] missing {src_report}")
        return
    shutil.copy2(src_report, HIRES_R5_OUT / "report.html")
    print(f"copied R5 report → {HIRES_R5_OUT.relative_to(V9)}")


def assert_fresh_reports() -> None:
    issues: list[str] = []
    for report in sorted(REPORTS.rglob("report.html")):
        text = report.read_text(encoding="utf-8")
        rel = report.relative_to(V9)
        for marker in STALE_MARKERS:
            if marker in text:
                issues.append(f"{rel}: stale marker `{marker}`")
        assets = report.parent / "assets"
        if not assets.is_dir():
            issues.append(f"{rel}: missing assets/")
        elif not list((assets / "画像头像素材").glob("*.png")):
            issues.append(f"{rel}: assets/画像头像素材/ empty")
    if issues:
        raise SystemExit("样例校验未通过:\n" + "\n".join(f"  - {i}" for i in issues))
    print("validation OK: 6 reports + assets")


def main() -> None:
    rerender_hires_r4()
    refresh_hires_r5()
    sync_template_css()
    run([sys.executable, "scripts/tools/build_sample_visuals.py"])
    run([sys.executable, "scripts/tools/build_single_persona_samples.py"])
    run([sys.executable, "scripts/tools/sync_reference_reports.py"])
    assert_fresh_reports()
    print("done: docs/reference/reports/")


if __name__ == "__main__":
    main()
