#!/usr/bin/env python3
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
html = path.read_text(encoding="utf-8")
for sid in re.findall(r'id="(persona-\d+-journey)"', html):
    m = re.search(rf'id="{sid}"[^>]*>(.*?)</section>', html, re.DOTALL)
    if not m:
        continue
    sec = m.group(1)
    for label in re.findall(r'l1-decision.*?l1-node-label[^>]*>([^<]+)<', sec, re.DOTALL):
        print(f"{sid}: {label.strip()}")
