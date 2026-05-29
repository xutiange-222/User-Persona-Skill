#!/usr/bin/env python3
"""将说明书样例/DevOps 报告中的头像同步到 skill 内置默认库 assets/default-avatars/。"""
from __future__ import annotations

import shutil
from pathlib import Path

V9 = Path(__file__).resolve().parents[2]
DEST = V9 / "assets" / "default-avatars"
SOURCES = [
    V9 / "docs/reference/reports/B-多角色/2B-DevOps五角色/assets/画像头像素材",
]


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in SOURCES:
        if not src.is_dir():
            print(f"[skip] missing {src}")
            continue
        for png in sorted(src.glob("*.png")):
            shutil.copy2(png, DEST / png.name)
            copied += 1
    print(f"synced {copied} avatars → {DEST.relative_to(V9)}")


if __name__ == "__main__":
    main()
