from pathlib import Path


def test_l2_uml_has_no_horizontal_inset_from_stage_headers():
    css = (
        Path(__file__).resolve().parents[3]
        / "assets"
        / "templates"
        / "_components.css"
    ).read_text(encoding="utf-8")
    assert ".tob-l2-uml-cell .l1-uml-wrap {\n  padding: 10px 0;\n}" in css
