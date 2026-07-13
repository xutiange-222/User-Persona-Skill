from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
PAGES_BASE = "https://xutiange-222.github.io/User-Persona-Skill/"


def _pages_urls(text: str) -> list[str]:
    return re.findall(r"https://xutiange-222\.github\.io/User-Persona-Skill/[^\s\"')>]+", text)


def test_readme_html_links_use_github_pages() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    html_links = re.findall(r"\]\(([^)]+\.html)\)", readme)
    assert len(html_links) == 6
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
        assert (ROOT / relative).is_file(), f"GitHub Pages 链接没有对应仓库文件：{url}"
