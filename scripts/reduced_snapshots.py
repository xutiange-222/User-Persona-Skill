"""Persist one deterministic merge snapshot per persona for recovery."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def persist_persona_snapshots(data: dict[str, Any], process_dir: Path) -> list[str]:
    root = process_dir / "reduced"
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for persona in data.get("personas") or []:
        if not isinstance(persona, dict):
            continue
        persona_id = str(persona.get("id") or "").strip()
        fields = persona.get("fields") or {}
        if not persona_id or not isinstance(fields, dict):
            continue
        payload = {
            "persona_id": persona_id,
            "persona_name": persona.get("name"),
            "members": persona.get("members") or [],
            "fields": fields,
            "field_decisions": persona.get("field_decisions") or [],
            "generated_from": "04-personas.draft.json",
        }
        path = root / f"{persona_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path.relative_to(process_dir).as_posix())
    return written
