"""2B grid 模块外壳：默认标题/图标 + grid-column 拼装。"""
from __future__ import annotations

from ..registry import render_component
from ..renderers._utils import escape
from .grid_solver import GridPlacement

_MODULE_ICON_RECT4 = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="2" y="2" width="5" height="5" rx="1" fill="white"/>'
    '<rect x="9" y="2" width="5" height="5" rx="1" fill="white"/>'
    '<rect x="2" y="9" width="5" height="5" rx="1" fill="white"/>'
    '<rect x="9" y="9" width="5" height="5" rx="1" fill="white"/></svg>'
)
_MODULE_ICON_FLOW = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="3" cy="8" r="1.5" fill="white"/>'
    '<circle cx="8" cy="8" r="1.5" fill="white"/>'
    '<circle cx="13" cy="8" r="1.5" fill="white"/>'
    '<line x1="4.5" y1="8" x2="6.5" y2="8" stroke="white" stroke-width="1.2"/>'
    '<line x1="9.5" y1="8" x2="11.5" y2="8" stroke="white" stroke-width="1.2"/></svg>'
)
_MODULE_ICON_LIST = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="2" y="3" width="2" height="2" fill="white"/>'
    '<rect x="6" y="3" width="8" height="2" fill="white"/>'
    '<rect x="2" y="7" width="2" height="2" fill="white"/>'
    '<rect x="6" y="7" width="8" height="2" fill="white"/>'
    '<rect x="2" y="11" width="2" height="2" fill="white"/>'
    '<rect x="6" y="11" width="8" height="2" fill="white"/></svg>'
)
_MODULE_ICON_SCREEN = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="2" y="3" width="12" height="9" rx="1" fill="none" stroke="white" stroke-width="1.5"/>'
    '<line x1="5" y1="14" x2="11" y2="14" stroke="white" stroke-width="1.5" stroke-linecap="round"/>'
    '<line x1="8" y1="12" x2="8" y2="14" stroke="white" stroke-width="1.5"/></svg>'
)
_MODULE_ICON_DOT = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="8" cy="8" r="6" fill="none" stroke="white" stroke-width="1.5"/>'
    '<circle cx="8" cy="8" r="2.5" fill="white"/></svg>'
)
_MODULE_ICON_AI = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M8 2 L9.5 6.5 L14 8 L9.5 9.5 L8 14 L6.5 9.5 L2 8 L6.5 6.5 Z" fill="white"/></svg>'
)

MODULE_META: dict[str, tuple[str, str]] = {
    "resp_rings":       ("工作职责",     _MODULE_ICON_RECT4),
    "collab_flow":      ("上下游协同",   _MODULE_ICON_FLOW),
    "scenario_grid":    ("典型业务场景", _MODULE_ICON_SCREEN),
    "ai_scenario_grid": ("AI 辅助场景", _MODULE_ICON_AI),
    "painpoint_list":   ("核心痛点",     _MODULE_ICON_DOT),
    "titled_list":      ("",             _MODULE_ICON_LIST),
    "generic_text":     ("",             _MODULE_ICON_LIST),
    "generic_bullet":   ("",             _MODULE_ICON_LIST),
    "generic_kv":       ("",             _MODULE_ICON_LIST),
}


def _module_title_html(component_type: str, props: dict) -> str:
    default_title, icon_svg = MODULE_META.get(component_type, ("", _MODULE_ICON_LIST))
    title = props.get("module_title") or default_title
    if not title:
        return ""
    return (
        f'<div class="module-title">'
        f'<span class="module-icon">{icon_svg}</span>'
        f'{escape(title)}'
        f'</div>'
    )


def _column_align_class(col_start: int, col_span: int) -> str:
    """detail 页左/右半栏贴边对齐用；主画像页忽略这些 class。"""
    if col_span >= 12:
        return "grid-anchor-full"
    if col_start >= 7:
        return "grid-anchor-end"
    return "grid-anchor-start"


def render_grid_placements(placements: list[GridPlacement]) -> str:
    """把 GridPlacement 列表渲染为 .grid-module 序列。"""
    parts = []
    for p in placements:
        title_html = _module_title_html(p.component_type, p.component_props)
        inner = render_component({"type": p.component_type, "props": p.component_props})
        kebab_type = p.component_type.replace("_", "-")
        align_class = _column_align_class(p.col_start, p.col_span)
        parts.append(
            f'<div class="grid-module grid-module-{kebab_type} {align_class}" '
            f'style="grid-column: {p.col_start} / span {p.col_span};">'
            f'{title_html}<div class="module-body">{inner}</div>'
            f'</div>'
        )
    return "".join(parts)
