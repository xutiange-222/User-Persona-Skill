from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GridPlacement:
    component_type: str
    component_props: dict
    col_start: int
    col_span: int
    row: int
    page: int


def solve_grid(components: list[dict], renderer_registry: dict) -> tuple[list[GridPlacement], bool]:
    placements, overflow = _pack_page(components, renderer_registry, page=1, max_rows=3)
    if not overflow:
        return placements, False
    return _dual_page_split(components, renderer_registry), True


def _pack_page(components: list[dict], renderer_registry: dict, page: int, max_rows: int | None = None) -> tuple[list[GridPlacement], bool]:
    placements: list[GridPlacement] = []
    cur_row = 1
    cur_col = 1
    for comp in components:
        renderer = renderer_registry[comp["type"]]
        n_rows = renderer.estimate_rows(comp["props"])
        n_cols = renderer.min_cols(comp["props"])
        if cur_col + n_cols - 1 > 12:
            _extend_last_to_fill_row(placements, cur_row)
            cur_row += 1
            cur_col = 1
        if max_rows is not None and cur_row + n_rows - 1 > max_rows:
            return placements, True
        placements.append(GridPlacement(comp["type"], comp["props"], cur_col, n_cols, cur_row, page))
        cur_col += n_cols
        if cur_col > 12:
            cur_row += 1
            cur_col = 1
    if placements and cur_col <= 12 and cur_col > 1:
        _extend_last_to_fill_row(placements, cur_row)
    return placements, False


def _extend_last_to_fill_row(placements: list[GridPlacement], cur_row: int) -> None:
    for p in reversed(placements):
        if p.row == cur_row:
            p.col_span = 13 - p.col_start
            break


def _dual_page_split(components: list[dict], renderer_registry: dict) -> list[GridPlacement]:
    """按 grid solver 算法实际估算的溢出点切分。

    与旧实现(硬编码 components[:3])的差别:
    - 旧:LLM 给的前 3 个去第一页,与组件实际尺寸/估高脱钩
    - 新:跑一遍无限制 _pack_page 得到所有 placement 的真实 row;row<=3 留第一页,row>3 换第二页重新打包
    这样保证第一页恰好填满 3 行(贪心后的物理上限),不浪费空间也不溢出。
    """
    full_placements, _ = _pack_page(components, renderer_registry, page=1, max_rows=None)
    page1 = [p for p in full_placements if p.row <= 3]
    overflow_components = [
        {"type": p.component_type, "props": p.component_props}
        for p in full_placements if p.row > 3
    ]
    page2, _ = _pack_page(overflow_components, renderer_registry, page=2, max_rows=None)
    return page1 + page2

