#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.tools.fix_focus_evidence_quotes import fix_evidence, walk_report

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
for persona in data.get("personas", []):
    for comp in persona.get("components", []):
        if comp.get("type") != "tob_journey_l2":
            continue
        for focus in comp.get("props", {}).get("focuses", []) or []:
            if "evidence" in focus:
                focus["evidence"] = fix_evidence(focus["evidence"])
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("done", path)
