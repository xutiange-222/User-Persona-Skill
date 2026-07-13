from scripts.components.tests.conftest import render_case


def test_emotion_path_stays_in_viewbox():
    html = render_case("journey_2c", 0)
    assert 'viewBox="0 0 500 100"' in html
    assert 'top:28.0%' in html or 'top:50.0%' in html or 'top:72.0%' in html
    assert "journey-emotion-dimension-label" in html
    assert "emotion-label below" in html


def test_frequency_highlight_applied():
    html = render_case("journey_2c", 0)
    assert "journey-pain-highlight" in html
