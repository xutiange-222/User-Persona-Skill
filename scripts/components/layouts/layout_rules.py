"""8 个 layout 的组件允许/必需/数量规则 + 通用校验。"""
from __future__ import annotations

from collections import Counter

from ..renderers._utils import escape

LAYOUT_2B_GRID_BODY_TYPES = {
    "resp_rings", "collab_flow", "scenario_grid",
    "ai_scenario_grid", "painpoint_list", "titled_list",
    "generic_text", "generic_bullet", "generic_kv",
}

LAYOUT_RULES = {
    "layout-2b-grid": {
        "required": {"identity_panel"},
        "allowed": {"identity_panel"} | LAYOUT_2B_GRID_BODY_TYPES,
        "counts": {"identity_panel": (1, 1)},
        "body_total": (1, 10),
        "theme_2c": False,
    },
    "layout-2b-grid-detail": {
        "required": set(),
        "allowed": LAYOUT_2B_GRID_BODY_TYPES,
        "counts": {},
        "body_total": (1, 10),
        "theme_2c": False,
    },
    "layout-2b-journey": {
        "required": set(),
        "allowed": {"tob_journey_l1", "tob_journey_l2"},
        "counts": {"tob_journey_l1": (0, 1), "tob_journey_l2": (0, 1)},
        "body_total": None,
        "theme_2c": False,
    },
    "layout-2c-portrait": {
        "required": {"identity_card", "persona_quote_pull", "section_blocks_grid"},
        "allowed": {"identity_card", "persona_quote_pull", "section_blocks_grid"},
        "counts": {
            "identity_card": (1, 1),
            "persona_quote_pull": (1, 1),
            "section_blocks_grid": (1, 1),
        },
        "body_total": None,
        "theme_2c": True,
    },
    "layout-2c-detail": {
        "required": {"detail_headline", "mockup_list", "detail_analysis"},
        "allowed": {
            "detail_headline", "mockup_list", "detail_analysis",
            "detail_illust_corner", "persona_quote_pull",
        },
        "counts": {
            "detail_headline": (1, 1),
            "mockup_list": (1, 1),
            "detail_analysis": (1, 1),
            "detail_illust_corner": (0, 1),
            "persona_quote_pull": (0, 1),
        },
        "body_total": None,
        "theme_2c": True,
    },
    "layout-2c-journey": {
        "required": {"journey_2c"},
        "allowed": {"journey_2c"},
        "counts": {"journey_2c": (1, 1)},
        "body_total": None,
        "theme_2c": True,
    },
    "layout-matrix-2d": {
        "required": {"matrix_guidance_strip", "matrix_2d"},
        "allowed": {"matrix_guidance_strip", "matrix_2d"},
        "counts": {"matrix_guidance_strip": (1, 1), "matrix_2d": (1, 1)},
        "body_total": None,
        "theme_2c": False,
    },
    "layout-distribution-multi": {
        "required": {"distribution_multi"},
        "allowed": {"distribution_multi"},
        "counts": {"distribution_multi": (1, 1)},
        "body_total": None,
        "theme_2c": False,
    },
}


def validate_layout_components(layout: str, persona: dict) -> tuple[list[dict], Counter]:
    """通用校验:必需 / 允许 / 数量。返回 (components, type_counter)。"""
    rules = LAYOUT_RULES[layout]
    components = persona.get("components", [])
    if not isinstance(components, list) or not components:
        raise ValueError(f"{layout}: components 必须是非空数组")

    actual_types = [c["type"] for c in components]
    type_counter = Counter(actual_types)
    actual_set = set(actual_types)

    missing = rules["required"] - actual_set
    if missing:
        raise ValueError(f"{layout}: 缺少必需组件 {sorted(missing)}")

    illegal = actual_set - rules["allowed"]
    if illegal:
        raise ValueError(f"{layout}: 不允许的组件 {sorted(illegal)}")

    for t, (lo, hi) in rules["counts"].items():
        n = type_counter.get(t, 0)
        if not (lo <= n <= hi):
            raise ValueError(f"{layout}: 组件 {t} 数量必须在 [{lo}, {hi}],实际 {n}")

    if rules["body_total"]:
        body_total = sum(1 for t in actual_types if t in LAYOUT_2B_GRID_BODY_TYPES)
        lo, hi = rules["body_total"]
        if not (lo <= body_total <= hi):
            raise ValueError(f"{layout}: body 组件总数必须在 [{lo}, {hi}],实际 {body_total}")

    return components, type_counter


def require_accent(layout: str, persona: dict) -> str:
    accent = persona.get("accent")
    if not accent:
        raise ValueError(f"{layout}: 2C 主题必须提供 accent(persona.accent)")
    return accent


def accent_inline(accent: str) -> str:
    return f'style="--color-accent: var(--accent-{escape(accent, quote=True)});"'
