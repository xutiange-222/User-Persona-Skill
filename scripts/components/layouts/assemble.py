"""8 个 layout 的 assemble 函数(P8 C 阶段)。

契约见 scripts/components/layouts/CONTRACTS.md。统一接口:

    def assemble_layout_XXX(persona: dict, metadata: dict) -> list[str]
"""
from __future__ import annotations

from ..registry import COMPONENT_REGISTRY, render_component
from ..renderers._utils import escape
from .grid_module import render_grid_placements
from .grid_solver import GridPlacement, solve_grid
from .layout_rules import accent_inline, require_accent, validate_layout_components


def assemble_layout_2b_grid(persona: dict, metadata: dict) -> list[str]:
    """toB/toD 单画像。溢出时拆双页,返回 2 个 slide。"""
    components, _ = validate_layout_components("layout-2b-grid", persona)
    pid = persona["id"]
    name = persona["name"]

    identity = next(c for c in components if c["type"] == "identity_panel")
    body = [c for c in components if c["type"] != "identity_panel"]

    if not body:
        identity_html = render_component(identity)
        slide = (
            f'<section class="persona-slide layout-2b-grid" id="{escape(pid, quote=True)}">'
            f'{identity_html}'
            f'<div class="modules-panel"></div>'
            f'</section>'
        )
        return [slide]

    placements, overflow = solve_grid(body, COMPONENT_REGISTRY)
    identity_html = render_component(identity)

    if not overflow:
        body_html = render_grid_placements(placements)
        slide = (
            f'<section class="persona-slide layout-2b-grid" id="{escape(pid, quote=True)}">'
            f'{identity_html}'
            f'<div class="modules-panel">{body_html}</div>'
            f'</section>'
        )
        return [slide]

    page1 = [p for p in placements if p.page == 1]
    page2 = [p for p in placements if p.page == 2]
    page1_html = render_grid_placements(page1)
    page2_html = render_grid_placements(page2)

    core_id, detail_id = _dual_page_ids(pid)
    slide1 = (
        f'<section class="persona-slide layout-2b-grid" id="{escape(core_id, quote=True)}">'
        f'{identity_html}'
        f'<div class="modules-panel">{page1_html}</div>'
        f'</section>'
    )
    slide2 = (
        f'<section class="persona-slide layout-2b-grid-detail" id="{escape(detail_id, quote=True)}">'
        f'<div class="detail-page-banner">{escape(name)} · 工作细节</div>'
        f'<div class="modules-panel">{page2_html}</div>'
        f'</section>'
    )
    return [slide1, slide2]


def _dual_page_ids(pid: str) -> tuple[str, str]:
    if pid.endswith("-core"):
        return pid, pid[:-len("-core")] + "-detail"
    if pid.endswith("-detail"):
        return pid[:-len("-detail")] + "-core", pid
    return f"{pid}-core", f"{pid}-detail"


def assemble_layout_2b_grid_detail(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-2b-grid-detail", persona)
    pid = persona["id"]

    if len(components) > 6:
        raise ValueError(
            f"layout-2b-grid-detail: 最多 6 个组件(2 列 × 3 行),"
            f"当前 {len(components)} 个 — 拆到更多 detail tab 或砍内容"
        )

    placements = [
        GridPlacement(
            component_type=comp["type"],
            component_props=comp["props"],
            col_start=(i % 2) * 6 + 1,
            col_span=6,
            row=i // 2 + 1,
            page=1,
        )
        for i, comp in enumerate(components)
    ]

    body_html = render_grid_placements(placements)
    slide = (
        f'<section class="persona-slide layout-2b-grid-detail" id="{escape(pid, quote=True)}">'
        f'<div class="modules-panel">{body_html}</div>'
        f'</section>'
    )
    return [slide]


def assemble_layout_2b_journey(persona: dict, metadata: dict) -> list[str]:
    components, type_counter = validate_layout_components("layout-2b-journey", persona)
    total = type_counter.get("tob_journey_l1", 0) + type_counter.get("tob_journey_l2", 0)
    if total != 1:
        raise ValueError(
            f"layout-2b-journey: 必须恰好含 1 个 tob_journey_l1 或 tob_journey_l2,实际 {total}"
        )

    pid = persona["id"]
    comp = components[0]
    modifier = "is-l1" if comp["type"] == "tob_journey_l1" else "is-l2"
    inner = render_component(comp)
    slide = (
        f'<section class="persona-slide layout-2b-journey {modifier}" '
        f'id="{escape(pid, quote=True)}">'
        f'{inner}'
        f'</section>'
    )
    return [slide]


def assemble_layout_2c_portrait(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-2c-portrait", persona)
    accent = require_accent("layout-2c-portrait", persona)
    pid = persona["id"]

    type_to_comp = {c["type"]: c for c in components}
    identity_html = render_component(type_to_comp["identity_card"])
    quote_html = render_component(type_to_comp["persona_quote_pull"])
    grid_html = render_component(type_to_comp["section_blocks_grid"])

    slide = (
        f'<section class="persona-slide layout-2c-portrait" '
        f'id="{escape(pid, quote=True)}" {accent_inline(accent)}>'
        f'{identity_html}{quote_html}{grid_html}'
        f'</section>'
    )
    return [slide]


def assemble_layout_2c_detail(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-2c-detail", persona)
    accent = require_accent("layout-2c-detail", persona)
    pid = persona["id"]

    type_to_comp = {c["type"]: c for c in components}
    headline_html = render_component(type_to_comp["detail_headline"])
    mockup_html = render_component(type_to_comp["mockup_list"])
    analysis_html = render_component(type_to_comp["detail_analysis"])
    quote_html = render_component(type_to_comp["persona_quote_pull"]) if "persona_quote_pull" in type_to_comp else ""
    illust_html = render_component(type_to_comp["detail_illust_corner"]) if "detail_illust_corner" in type_to_comp else ""

    slide = (
        f'<section class="persona-slide layout-2c-detail" '
        f'id="{escape(pid, quote=True)}" {accent_inline(accent)}>'
        f'{headline_html}{quote_html}'
        f'<div class="l2c-body">'
        f'<div class="l2c-col-mockup">{mockup_html}</div>'
        f'<div class="l2c-col-analysis">{analysis_html}</div>'
        f'</div>'
        f'{illust_html}'
        f'</section>'
    )
    return [slide]


def assemble_layout_2c_journey(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-2c-journey", persona)
    accent = require_accent("layout-2c-journey", persona)
    pid = persona["id"]

    inner = render_component(components[0])
    slide = (
        f'<section class="persona-slide layout-2c-journey" '
        f'id="{escape(pid, quote=True)}" {accent_inline(accent)}>'
        f'{inner}'
        f'</section>'
    )
    return [slide]


def assemble_layout_matrix_2d(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-matrix-2d", persona)
    pid = persona["id"]

    type_to_comp = {c["type"]: c for c in components}
    strip_html = render_component(type_to_comp["matrix_guidance_strip"])
    matrix_html = render_component(type_to_comp["matrix_2d"])

    slide = (
        f'<section class="persona-slide layout-matrix-2d" id="{escape(pid, quote=True)}">'
        f'{strip_html}{matrix_html}'
        f'</section>'
    )
    return [slide]


def assemble_layout_distribution_multi(persona: dict, metadata: dict) -> list[str]:
    components, _ = validate_layout_components("layout-distribution-multi", persona)
    pid = persona["id"]

    inner = render_component(components[0])
    slide = (
        f'<section class="persona-slide layout-distribution-multi" id="{escape(pid, quote=True)}">'
        f'{inner}'
        f'</section>'
    )
    return [slide]


ASSEMBLERS = {
    "layout-2b-grid": assemble_layout_2b_grid,
    "layout-2b-grid-detail": assemble_layout_2b_grid_detail,
    "layout-2b-journey": assemble_layout_2b_journey,
    "layout-2c-portrait": assemble_layout_2c_portrait,
    "layout-2c-detail": assemble_layout_2c_detail,
    "layout-2c-journey": assemble_layout_2c_journey,
    "layout-matrix-2d": assemble_layout_matrix_2d,
    "layout-distribution-multi": assemble_layout_distribution_multi,
}
