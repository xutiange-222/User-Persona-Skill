from pathlib import Path

import pytest

from scripts.components.render_report import _replace_single_slot


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "assets" / "templates" / "_base.html"
SLOTS = (
    "theme",
    "density",
    "accent_inline",
    "title",
    "report_title",
    "report_meta_info",
    "persona_nav",
    "main_content",
)


def test_every_base_slot_occurs_once() -> None:
    template = BASE.read_text(encoding="utf-8")
    for name in SLOTS:
        assert template.count("{{" + name + "}}") == 1


def test_single_slot_replacement_fails_loudly() -> None:
    with pytest.raises(ValueError, match="恰好出现 1 次"):
        _replace_single_slot("{{x}} {{x}}", "x", "value")
