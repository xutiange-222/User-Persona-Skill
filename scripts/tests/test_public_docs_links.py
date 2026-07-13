from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
PAGES_BASE = "https://xutiange-222.github.io/User-Persona-Skill/"
MOJIBAKE_RE = re.compile(
    r"[\uE000-\uF8FF]|(?:鈥\?|銆\?|锛\?|锟斤拷|馃)|\?/(?:div|button|section|span)>",
    re.IGNORECASE,
)
MIN_REPORT_SLIDES = {
    "docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html": 3,
    "docs/reference/reports/A-单画像/2C-内行场景派/report.html": 3,
    "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html": 16,
    "docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html": 16,
    "docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html": 16,
}


def _pages_urls(text: str) -> list[str]:
    return re.findall(r"https://xutiange-222\.github\.io/User-Persona-Skill/[^\s\"')>]+", text)


def test_readme_html_links_use_github_pages() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    html_links = re.findall(r"\]\(([^)]+\.html)\)", readme)
    assert html_links
    assert all(url.startswith(PAGES_BASE) for url in html_links)


def test_public_docs_urls_map_to_existing_repository_files() -> None:
    texts = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "人类用户说明书.html").read_text(encoding="utf-8"),
    ]
    urls = {url for text in texts for url in _pages_urls(text)}
    assert len(urls) == 6
    for url in urls:
        relative = unquote(urlparse(url).path.removeprefix("/User-Persona-Skill/"))
        target = ROOT / relative
        assert target.is_file(), f"GitHub Pages 链接没有对应仓库文件：{url}"
        html = target.read_text(encoding="utf-8")
        match = MOJIBAKE_RE.search(html)
        assert match is None, f"GitHub Pages 文件含乱码或错误转码：{relative}，命中 {match.group(0)!r}"
        assert html.rstrip().endswith("</html>"), f"GitHub Pages 文件疑似被截断：{relative}"
        if relative in MIN_REPORT_SLIDES:
            slide_count = html.count('<section class="persona-slide')
            assert slide_count >= MIN_REPORT_SLIDES[relative], (
                f"GitHub Pages 参考报告页面数量异常：{relative}，"
                f"至少 {MIN_REPORT_SLIDES[relative]} 页，实际 {slide_count} 页"
            )
            for asset_name in ("_design-tokens.css", "_components.css"):
                copied_asset = target.parent / asset_name
                canonical_asset = ROOT / "assets" / "templates" / asset_name
                assert copied_asset.is_file(), f"参考报告缺少配套样式：{relative} -> {asset_name}"
                assert copied_asset.read_bytes() == canonical_asset.read_bytes(), (
                    f"参考报告 HTML 与配套样式版本不一致：{relative} -> {asset_name}"
                )
                assert f'href="{asset_name}?v=20260713-reference-bundle-sync-11"' in html
