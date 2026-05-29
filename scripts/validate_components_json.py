#!/usr/bin/env python3
"""兼容入口 — 实现已迁至 scripts/components/validate.py。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.components.validate import (  # noqa: F401
    format_issues_for_human,
    main,
    validate_report_json,
)

if __name__ == "__main__":
    sys.exit(main())
