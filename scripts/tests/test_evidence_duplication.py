"""P9-DUPLICATE-EVIDENCE 守门测试(validate_html 层)。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_html import check_evidence_duplication, Report


def _run(html: str) -> Report:
    rep = Report(html_path=Path("dummy.html"))
    check_evidence_duplication(html, rep)
    return rep


def test_three_duplicates_in_one_slide_errors():
    html = (
        '<section class="persona-slide layout-2b-grid" id="persona-1">'
        '<div data-evidence="&quot;同一句话&quot; — 张三"></div>'
        '<div data-evidence="&quot;同一句话&quot; — 张三"></div>'
        '<div data-evidence="&quot;同一句话&quot; — 张三"></div>'
        '</section>'
    )
    rep = _run(html)
    errors = [i for i in rep.issues if i.severity == "ERROR" and i.code == "P9-DUPLICATE-EVIDENCE"]
    assert len(errors) == 1


def test_two_duplicates_warn_only():
    html = (
        '<section class="persona-slide layout-2b-grid" id="persona-1">'
        '<div data-evidence="&quot;原话A&quot; — 张三"></div>'
        '<div data-evidence="&quot;原话A&quot; — 张三"></div>'
        '</section>'
    )
    rep = _run(html)
    assert any(i.code == "P9-EVIDENCE-REUSED" and i.severity == "WARNING" for i in rep.issues)
    assert not any(i.code == "P9-DUPLICATE-EVIDENCE" for i in rep.issues)


def test_unique_evidences_no_issue():
    html = (
        '<section class="persona-slide layout-2b-grid" id="persona-1">'
        '<div data-evidence="&quot;原话A&quot; — 张三"></div>'
        '<div data-evidence="&quot;原话B&quot; — 李四"></div>'
        '<div data-evidence="&quot;原话C&quot; — 王五"></div>'
        '</section>'
    )
    rep = _run(html)
    assert not any(i.code in ("P9-DUPLICATE-EVIDENCE", "P9-EVIDENCE-REUSED") for i in rep.issues)


def test_duplicates_across_slides_not_flagged():
    html = (
        '<section class="persona-slide" id="persona-1">'
        '<div data-evidence="&quot;原话A&quot; — 张三"></div>'
        '</section>'
        '<section class="persona-slide" id="persona-2">'
        '<div data-evidence="&quot;原话A&quot; — 张三"></div>'
        '</section>'
    )
    rep = _run(html)
    assert not any(i.code in ("P9-DUPLICATE-EVIDENCE", "P9-EVIDENCE-REUSED") for i in rep.issues)
