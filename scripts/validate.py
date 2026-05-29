#!/usr/bin/env python3
"""Validate user-persona-v8 personas JSON.

This wrapper keeps the historical validate.py entrypoint while delegating the
v8 data contract to scripts/tests/check_personas_json.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="04-personas.json 或单画像 JSON 路径")
    parser.add_argument("--schema", default=None, help="兼容旧参数,当前不再区分 toB/toC")
    parser.add_argument("--fields", default=None, help="兼容旧参数,当前由 v8 JSON 自身结构校验")
    args = parser.parse_args()

    checker = Path(__file__).resolve().parent / "tests" / "check_personas_json.py"
    proc = subprocess.run(
        [sys.executable, str(checker), "--input", args.input],
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout)
        else:
            # 保持旧 validate.py 的关键字段名,方便既有调用方读取。
            payload["valid"] = bool(payload.get("success"))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
