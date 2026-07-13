from pathlib import Path

from scripts.validate_html import Report, check_mojibake


def test_validate_html_blocks_valid_utf8_mojibake() -> None:
    report = Report(html_path=Path("report.html"))
    check_mojibake("<html><body>鏍囩鍐呭?/div></body></html>", report)
    assert any(issue.code == "P0-MOJIBAKE" for issue in report.errors)


def test_validate_html_accepts_normal_chinese() -> None:
    report = Report(html_path=Path("report.html"))
    check_mojibake("<html><body>DevOps 平台多角色用户画像</body></html>", report)
    assert report.errors == []
