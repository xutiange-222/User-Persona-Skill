"""Matrix 组件测试：smoke + 标签/nudge/evidence 守门。"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.components.renderers.matrix import compute_nudge_px, render_matrix_2d
from scripts.components.tests.conftest import assert_component_cases, render_case

SAMPLE_PROPS = {
    "axis_labels": {
        "top": "音质鉴别", "bottom": "氛围随听",
        "left": "反复比价", "right": "认可即买",
    },
    "quadrants": [
        {"id": "p1", "label": "内行派", "position": "q1"},
        {"id": "p2", "label": "优惠派", "position": "q2"},
        {"id": "p3", "label": "助眠派", "position": "q3"},
        {"id": "p4", "label": "认价派", "position": "q4"},
    ],
    "respondents": [
        {
            "x": 78.0, "y": 20.0,
            "display_name": "黄先生",
            "quadrant_persona": "内行派",
            "evidence": [
                {"quote": "我能听出小提琴的木头味", "source": "黄先生"},
                {"quote": "普通音质我现在听不下去", "source": "黄先生"},
            ],
        },
        {
            "x": 22.0, "y": 35.0,
            "display_name": "丁先生",
            "quadrant_persona": "优惠派",
            "evidence": [{"quote": "等折扣再开", "source": "丁先生"}],
        },
    ],
}


def test_matrix_smoke_basic():
    html = render_case("matrix_2d", 0)
    assert isinstance(html, str)


def test_matrix_smoke_second_case():
    assert_component_cases("matrix_2d")


def test_empty_quadrant_rendered():
    html = render_case("matrix_2d", 0)
    assert "matrix-empty-quadrant" in html
    assert "empty-tag" in html


def test_respondents_use_flex_wrapper_not_legacy_direction():
    html = render_case("matrix_2d", 0)
    wrappers = re.findall(r'<div class="matrix-respondent"[^>]*>', html)
    assert wrappers
    for tag in wrappers:
        assert "--matrix-nudge-x:" in tag and "--matrix-nudge-y:" in tag
    assert not re.search(r'class="respondent-label\s+label-', html)


def test_wrapper_has_position_and_nudge():
    html = render_matrix_2d(SAMPLE_PROPS)
    wrappers = re.findall(r'<div class="matrix-respondent"[^>]*>', html)
    assert wrappers
    for tag in wrappers:
        assert re.search(r'style="left:[0-9.]+%;top:[0-9.]+%', tag)
        assert "--matrix-nudge-x:" in tag and "--matrix-nudge-y:" in tag


def test_triangle_before_name_in_dom():
    html = render_matrix_2d(SAMPLE_PROPS)
    for m in re.finditer(
        r'<div class="matrix-respondent"[^>]*>'
        r'<span class="matrix-respondent-dot"></span>'
        r'<span class="respondent-label">([^<]+)</span></div>',
        html,
    ):
        assert m.group(1) in ("黄先生", "丁先生")


def test_data_evidence_on_wrapper_only():
    html = render_matrix_2d(SAMPLE_PROPS)
    assert html.count('class="matrix-respondent-dot"') == 2
    assert 'class="matrix-respondent-dot" data-evidence' not in html
    assert html.count('class="matrix-respondent" data-evidence') == 2


def test_data_evidence_contains_no_raw_newline():
    html = render_matrix_2d(SAMPLE_PROPS)
    for m in re.finditer(r'data-evidence="([^"]*)"', html):
        assert "\n" not in m.group(1)
        assert "\r" not in m.group(1)


def test_nudge_points_toward_center():
    nx, ny = compute_nudge_px(78, 20, 0)
    assert nx < 0 and ny > 0
    nx2, ny2 = compute_nudge_px(26, 24, 0)
    assert nx2 > 0 and ny2 > 0


def test_same_quadrant_stagger_differs():
    assert compute_nudge_px(78, 20, 0) != compute_nudge_px(70, 32, 1)


def test_label_spacing_flex_gap_in_css():
    css_path = Path(__file__).resolve().parents[3] / "assets" / "templates" / "_components.css"
    rule = re.search(r"\.matrix-container > \.matrix-respondent\s*\{([^}]+)\}", css_path.read_text(encoding="utf-8"))
    assert rule and "gap: 8px" in rule.group(1)


def test_data_evidence_position_relative_excludes_matrix():
    css_path = Path(__file__).resolve().parents[3] / "assets" / "templates" / "_components.css"
    css_text = css_path.read_text(encoding="utf-8")
    rule_match = re.search(
        r'\[data-evidence\]:not\(\[data-evidence=""\]\)([^\{]*)\{[^}]*position:\s*relative',
        css_text,
    )
    assert rule_match
    selector_tail = rule_match.group(1)
    assert ":not(.matrix-respondent)" in selector_tail
    assert ":not(.matrix-respondent-dot)" in selector_tail
    assert ":not(.respondent-label)" in selector_tail


def test_no_legacy_label_direction_classes():
    html = render_matrix_2d(SAMPLE_PROPS)
    assert "label-bottom-left" not in html
    assert "label-top-right" not in html
