from components.layouts.grid_solver import solve_grid
from components.registry import COMPONENT_REGISTRY
from scripts.components.tests.conftest import CASES


def comp(t):
    return {"type": t, "props": CASES[t][0]}


def test_single_page_packs_and_extends_last_row():
    placements, dual = solve_grid([comp("resp_rings"), comp("painpoint_list")], COMPONENT_REGISTRY)
    assert dual is False
    assert len(placements) == 2
    assert placements[-1].col_span == 6


def test_overflow_splits_dual_page():
    items = [
        comp("collab_flow"),
        comp("titled_list"),
        comp("scenario_grid"),
        comp("ai_scenario_grid"),
        comp("painpoint_list"),
        comp("generic_bullet"),
        comp("generic_text"),
    ]
    placements, dual = solve_grid(items, COMPONENT_REGISTRY)
    assert dual is True
    assert {p.page for p in placements} == {1, 2}
