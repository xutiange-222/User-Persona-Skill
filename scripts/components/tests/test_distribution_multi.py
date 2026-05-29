from scripts.components.tests.conftest import render_case


def test_level_labels_render_near_points():
    html = render_case("distribution_multi", 0)
    assert "snake-point-level-label" in html


def test_point_evidence_is_grouped():
    html = render_case("distribution_multi", 0)
    assert "data-evidence=" in html
