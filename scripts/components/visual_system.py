"""Load the machine-readable visual system shared by renderers and validators."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


VISUAL_SYSTEM_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "templates" / "_visual-system.json"
)


@lru_cache(maxsize=1)
def load_visual_system() -> dict:
    data = json.loads(VISUAL_SYSTEM_PATH.read_text(encoding="utf-8"))
    for key in ("foundations", "semantic_tokens", "themes", "component_contracts"):
        if key not in data:
            raise ValueError(f"visual system missing required group: {key}")
    return data


def toc_palette_for_accent(accent: str) -> tuple[str, dict[str, str]]:
    system = load_visual_system()
    toc = system["themes"]["2c"]
    style = toc["accent_map"].get(accent)
    if not style:
        allowed = ", ".join(sorted(toc["accent_map"]))
        raise ValueError(f"unknown or deprecated 2C accent {accent!r}; choose one of: {allowed}")
    values = toc["palette_packs"][style]["values"]
    return style, values


def toc_palette_pack_for_style(style: str) -> dict:
    return load_visual_system()["themes"]["2c"]["palette_packs"][style]


def tob_journey_contract() -> dict:
    return load_visual_system()["themes"]["2b"]["journey"]
