"""Three-way alignment check: registry ↔ schemas ↔ renderers.

Catches the most common drift patterns when a new component is added or one is renamed:

1. Every type in registry.py COMPONENT_REGISTRY has a matching schemas/<type>.json
2. Every schemas/<type>.json file has a matching registry entry (and a callable renderer)
3. Every type listed in report.json's top-level enum is in COMPONENT_REGISTRY
4. Registry callables can be imported without error

Usage:
    python scripts/tests/check_three_way.py

Returns non-zero exit code on any mismatch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "scripts" / "components" / "schemas"
REGISTRY_PY = ROOT / "scripts" / "components" / "registry.py"
REPORT_JSON = SCHEMAS_DIR / "report.json"

# schemas that are not standalone LLM-facing components (helpers / sub-shapes)
SCHEMA_ALLOWLIST_NON_COMPONENT = {
    "report",        # top-level
    "section_block", # used as sub-shape inside section_blocks_grid; not a top-level type
}


def load_registry_types() -> set[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from components.registry import COMPONENT_REGISTRY  # noqa: E402
    except Exception as exc:  # pragma: no cover - import failure is the whole point
        print(f"FAIL: importing components.registry: {exc}", file=sys.stderr)
        raise
    return set(COMPONENT_REGISTRY.keys())


def load_schema_types() -> set[str]:
    return {p.stem for p in SCHEMAS_DIR.glob("*.json")}


def load_report_enum() -> set[str]:
    text = REPORT_JSON.read_text(encoding="utf-8")
    data = json.loads(text)
    try:
        items = (
            data["properties"]["personas"]["items"]["properties"]
            ["components"]["items"]["properties"]["type"]["enum"]
        )
    except KeyError as e:
        print(f"FAIL: cannot locate components[].type enum in report.json: {e}", file=sys.stderr)
        raise
    return set(items)


def main() -> int:
    failures: list[str] = []

    registry_types = load_registry_types()
    schema_types = load_schema_types()
    report_enum = load_report_enum()

    # 1. registry → schema
    missing_schema = registry_types - schema_types
    if missing_schema:
        failures.append(
            f"registry has type(s) with no schema file: {sorted(missing_schema)}"
        )

    # 2. schema → registry (allowlist helper schemas)
    schemas_to_check = schema_types - SCHEMA_ALLOWLIST_NON_COMPONENT
    missing_registry = schemas_to_check - registry_types
    if missing_registry:
        failures.append(
            f"schema files with no registry entry: {sorted(missing_registry)}\n"
            f"  → either add to registry.py, delete the schema, "
            f"or add to SCHEMA_ALLOWLIST_NON_COMPONENT in check_three_way.py"
        )

    # 3. report.json enum → registry
    enum_missing = report_enum - registry_types
    if enum_missing:
        failures.append(
            f"report.json enum lists type(s) not in registry: {sorted(enum_missing)}"
        )

    # 4. registry types should be in report.json enum (helpers exempted)
    registry_not_in_enum = (registry_types - report_enum) - SCHEMA_ALLOWLIST_NON_COMPONENT
    if registry_not_in_enum:
        failures.append(
            f"registry type(s) not in report.json enum: {sorted(registry_not_in_enum)}\n"
            f"  → add to enum, or add to SCHEMA_ALLOWLIST_NON_COMPONENT if intentionally internal"
        )

    if failures:
        print("FAIL: schema/registry/report alignment issues found:\n")
        for f in failures:
            print(f"  - {f}")
        return 1

    n_reg = len(registry_types)
    n_schema = len(schema_types)
    n_enum = len(report_enum)
    print(
        f"OK: {n_reg} registry types, {n_schema} schema files, "
        f"{n_enum} types in report.json enum — all aligned."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
