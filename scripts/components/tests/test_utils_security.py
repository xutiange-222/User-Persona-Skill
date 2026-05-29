from scripts.components.renderers._utils import escape_allow_strong


def test_escape_allow_strong_escapes_html_inside_strong():
    html = escape_allow_strong('<strong><img src=x onerror=alert(1)></strong>')
    assert "<img" not in html
    assert "onerror" in html
    assert "&lt;strong&gt;" in html


def test_escape_allow_strong_preserves_plain_strong_text():
    html = escape_allow_strong('常规 <strong>重点 & "证据"</strong> 文本')
    assert html == '常规 <strong>重点 &amp; &quot;证据&quot;</strong> 文本'

