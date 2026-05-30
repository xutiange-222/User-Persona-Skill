#!/usr/bin/env python3
"""Shared path helpers for user-persona-v8.

The public workspace structure is:

用户画像报告输出/
└── <项目名>-<日期时间>/
    ├── 过程稿/
    ├── 画像头像素材/
    ├── 界面截图/
    └── 最终交付件-*/
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

OUTPUT_ROOT_NAME = "用户画像报告输出"
PROCESS_DIR_NAME = "过程稿"
AVATAR_ASSETS_DIR_NAME = "画像头像素材"
INTERFACE_SCREENSHOTS_DIR_NAME = "界面截图"


def sanitize_project_name(name: str) -> str:
    """Return a readable folder-safe project name."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", str(name or "").strip())
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned[:32] or "用户画像项目"


def checkpoints_template_path() -> Path:
    """Return bundled CHECKPOINTS.md for new process dirs."""
    return Path(__file__).resolve().parent.parent / "assets" / "templates" / "CHECKPOINTS.md"


def bootstrap_process_dir(process_dir: Path) -> None:
    """Create subfolders and checkpoint readme under 过程稿/."""
    for sub in ("processed", "extracted", "logs", "drafts"):
        (process_dir / sub).mkdir(parents=True, exist_ok=True)
    template = checkpoints_template_path()
    target = process_dir / "CHECKPOINTS.md"
    if template.is_file() and not target.exists():
        target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")


def create_run_dir(base_dir: Path, project_name: str, now: datetime | None = None) -> Path:
    """Create a project run directory and required user-facing folders."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    root = Path(base_dir).resolve() / OUTPUT_ROOT_NAME
    run_dir = root / f"{sanitize_project_name(project_name)}-{timestamp}"
    for child in (
        PROCESS_DIR_NAME,
        AVATAR_ASSETS_DIR_NAME,
        INTERFACE_SCREENSHOTS_DIR_NAME,
    ):
        (run_dir / child).mkdir(parents=True, exist_ok=True)
    bootstrap_process_dir(run_dir / PROCESS_DIR_NAME)
    return run_dir


def resolve_process_dir(workdir: Path) -> Path:
    """Resolve scripts' data directory from either a run dir or process dir."""
    path = Path(workdir).resolve()
    if path.name == PROCESS_DIR_NAME:
        return path
    process_dir = path / PROCESS_DIR_NAME
    if process_dir.exists():
        return process_dir
    return path


def avatar_assets_dir(run_dir: Path) -> Path:
    return Path(run_dir).resolve() / AVATAR_ASSETS_DIR_NAME


def interface_screenshots_dir(run_dir: Path) -> Path:
    return Path(run_dir).resolve() / INTERFACE_SCREENSHOTS_DIR_NAME
