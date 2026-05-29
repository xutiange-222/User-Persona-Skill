#!/usr/bin/env python3
"""为 tob_journey_l2 focuses.evidence 补上中文引号,满足 validate_html P7-EVIDENCE-NO-QUOTE。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def fix_evidence(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return t
    if any(q in t for q in ('"', """, """, "&quot;")):
        return t
    # validate_html P7 认 ASCII/弯引号,不认「」
    def wrap_quote(part: str) -> str:
        part = part.strip().strip("「」")
        return f"\u201c{part}\u201d"

    if " — " in t:
        quote_part, rest = t.split(" — ", 1)
        quote_part = quote_part.strip()
        if quote_part:
            quote_part = wrap_quote(quote_part)
        return f"{quote_part} — {rest.strip()}"
    return wrap_quote(t)


def walk_report(data: dict) -> int:
    n = 0
    for persona in data.get("personas", []):
        for comp in persona.get("components", []):
            if comp.get("type") != "tob_journey_l2":
                continue
            for focus in comp.get("props", {}).get("focuses", []) or []:
                if "evidence" in focus:
                    old = focus["evidence"]
                    new = fix_evidence(old)
                    if new != old:
                        focus["evidence"] = new
                        n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--inplace", action="store_true")
    args = parser.parse_args()
    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))
    count = walk_report(data)
    out = path if args.inplace else path.with_suffix(".fixed.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] fixed {count} evidence field(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
