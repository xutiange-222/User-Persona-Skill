#!/usr/bin/env python3
"""Validate canonical display components stored in 04-personas.json."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None


def validate_persona_checkpoint(process_dir: Path) -> list[dict]:
    process_dir = Path(process_dir)
    path = process_dir / "04-personas.json"
    if not path.is_file():
        return [{"code": "PERSONA_CHECKPOINT_MISSING", "path": path.name, "message": "04-personas.json 缺失。"}]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [{"code": "PERSONA_CHECKPOINT_INVALID", "path": path.name, "message": str(exc)}]
    errors: list[dict] = []
    schema_dir = Path(__file__).resolve().parent / "components" / "schemas"
    for p_idx, persona in enumerate(data.get("personas") or []):
        components = persona.get("display_components") if isinstance(persona, dict) else None
        members = persona.get("members") if isinstance(persona, dict) else []
        if persona.get("user_count") != len(members or []):
            errors.append({"code": "PERSONA_USER_COUNT_MISMATCH", "path": f"personas[{p_idx}].user_count", "message": "user_count 必须等于去重后的 members 数量。"})
        if not components:
            errors.append({"code": "PERSONA_DISPLAY_COMPONENTS_MISSING", "path": f"personas[{p_idx}]", "message": "缺少用户确认的 display_components。"})
            continue
        for c_idx, component in enumerate(components):
            comp_type = component.get("type") if isinstance(component, dict) else None
            schema_path = schema_dir / f"{comp_type}.json"
            base = f"personas[{p_idx}].display_components[{c_idx}]"
            if not schema_path.is_file():
                errors.append({"code": "PERSONA_COMPONENT_UNKNOWN", "path": base, "message": f"未注册组件 {comp_type!r}。"})
                continue
            if Draft202012Validator is not None:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                for err in Draft202012Validator(schema).iter_errors(component.get("props")):
                    suffix = ".".join(map(str, err.absolute_path))
                    errors.append({"code": "PERSONA_COMPONENT_SCHEMA", "path": base + (f".props.{suffix}" if suffix else ".props"), "message": err.message})
    return errors
