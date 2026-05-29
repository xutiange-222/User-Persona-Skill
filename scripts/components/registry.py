from __future__ import annotations

from .renderers import distribution, matrix, tob_grid, tob_journey, toc, toc_journey


COMPONENT_REGISTRY = {
    "identity_panel": tob_grid.render_identity_panel,
    "resp_rings": tob_grid.render_resp_rings,
    "collab_flow": tob_grid.render_collab_flow,
    "scenario_grid": tob_grid.render_scenario_grid,
    "ai_scenario_grid": tob_grid.render_ai_scenario_grid,
    "painpoint_list": tob_grid.render_painpoint_list,
    "titled_list": tob_grid.render_titled_list,
    "generic_text": tob_grid.render_generic_text,
    "generic_bullet": tob_grid.render_generic_bullet,
    "generic_kv": tob_grid.render_generic_kv,
    "tob_journey_l1": tob_journey.render_tob_journey_l1,
    "tob_journey_l2": tob_journey.render_tob_journey_l2,
    "identity_card": toc.render_identity_card,
    "persona_quote_pull": toc.render_persona_quote_pull,
    "section_blocks_grid": toc.render_section_blocks_grid,
    "section_block": toc.render_section_block,
    "detail_headline": toc.render_detail_headline,
    "mockup_list": toc.render_mockup_list,
    "detail_analysis": toc.render_detail_analysis,
    "detail_illust_corner": toc.render_detail_illust_corner,
    "journey_2c": toc_journey.render_journey_2c,
    "matrix_guidance_strip": matrix.render_matrix_guidance_strip,
    "matrix_2d": matrix.render_matrix_2d,
    "distribution_multi": distribution.render_distribution_multi,
}


def render_component(comp: dict) -> str:
    return COMPONENT_REGISTRY[comp["type"]](comp["props"])
