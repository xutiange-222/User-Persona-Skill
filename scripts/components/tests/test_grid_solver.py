import pytest
from pathlib import Path

from components.layouts.grid_solver import solve_grid
from components.layouts.assemble import assemble_layout_2b_grid
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


def test_overflow_switches_report_density_to_mid():
    persona = {
        "id": "persona-1",
        "name": "测试画像",
        "layout": "layout-2b-grid",
        "components": [
            comp("identity_panel"),
            comp("collab_flow"),
            comp("titled_list"),
            comp("scenario_grid"),
            comp("ai_scenario_grid"),
            comp("painpoint_list"),
            comp("generic_bullet"),
            comp("generic_text"),
        ],
    }
    metadata = {"theme": "2b", "density": "high"}
    with pytest.raises(ValueError, match="sparse detail tab"):
        assemble_layout_2b_grid(persona, metadata)
    assert metadata["_internal_density_override"] == "mid"


def test_single_overflow_component_requires_user_content_decision():
    persona = {
        "id": "persona-1",
        "name": "测试画像",
        "layout": "layout-2b-grid",
        "components": [
            comp("identity_panel"),
            comp("resp_rings"),
            comp("collab_flow"),
            comp("scenario_grid"),
            comp("ai_scenario_grid"),
            comp("generic_bullet"),
            comp("generic_text"),
            comp("painpoint_list"),
        ],
    }
    metadata = {"theme": "2b", "density": "high"}
    with pytest.raises(ValueError, match="explicit confirmation"):
        assemble_layout_2b_grid(persona, metadata)


def test_detail_page_css_balances_space_and_limits_dividers():
    root = Path(__file__).resolve().parents[3]
    css = (root / "assets" / "templates" / "_components.css").read_text(encoding="utf-8")
    assert ".persona-slide.layout-2b-grid-detail.active" in css
    assert "grid-template-rows: auto minmax(0, 1fr)" in css
    assert "grid-auto-rows: auto" in css
    assert "align-content: center" in css
    assert "background: #fbfcfe" in css
    assert "content: none" in css
    assert "width: min(88%, 520px)" not in css
