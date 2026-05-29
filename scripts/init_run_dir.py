#!/usr/bin/env python3
"""Create the public run directory for one persona report project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from path_utils import (
    AVATAR_ASSETS_DIR_NAME,
    INTERFACE_SCREENSHOTS_DIR_NAME,
    PROCESS_DIR_NAME,
    create_run_dir,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default=".", help="用户当前操作目录")
    parser.add_argument("--project-name", required=True, help="项目名,用于生成项目运行目录")
    args = parser.parse_args()

    run_dir = create_run_dir(Path(args.base_dir), args.project_name)
    result = {
        "success": True,
        "run_dir": str(run_dir),
        "process_dir": str(run_dir / PROCESS_DIR_NAME),
        "avatar_assets_dir": str(run_dir / AVATAR_ASSETS_DIR_NAME),
        "screenshot_dir": str(run_dir / INTERFACE_SCREENSHOTS_DIR_NAME),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
