from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import json
from components.registry import render_component

DATA = json.loads((Path(__file__).parent / "gallery_data.json").read_text(encoding="utf-8"))
CASES = {}
for group in DATA.values():
    for item in group["items"]:
        CASES.setdefault(item["type"], []).append(item["props"])

def render_case(component_type, idx=0):
    return render_component({"type": component_type, "props": CASES[component_type][idx]})

def assert_component_cases(component_type):
    html1 = render_case(component_type, 0)
    html2 = render_case(component_type, 1)
    assert isinstance(html1, str)
    assert isinstance(html2, str)
    assert "<script>" not in html2
