from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REPORTS = {
    "docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html",
    "docs/reference/reports/A-单画像/2C-内行场景派/report.html",
    "docs/reference/reports/B-多角色/2B-DevOps五角色/report.html",
    "docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html",
    "docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html",
}


def test_obsolete_reference_sources_are_removed() -> None:
    for relative in (
        "assets/sample-sources",
        "docs/reference/archive",
        "docs/reference/layouts",
        "STRUCTURE.md",
        "VERSION.md",
        "scripts/merge.py",
        "scripts/cluster_personas.py",
    ):
        assert not (ROOT / relative).exists(), relative


def test_maintainer_tools_have_one_entrypoint() -> None:
    tools = {path.name for path in (ROOT / "scripts" / "tools").glob("*") if path.is_file()}
    assert tools == {"refresh_reference_reports.py"}


def test_human_manual_report_links_use_pages_and_exist() -> None:
    manual = (ROOT / "人类用户说明书.html").read_text(encoding="utf-8")
    links = re.findall(r'href="([^"]+)"', manual)
    pages_base = "https://xutiange-222.github.io/User-Persona-Skill/"
    report_links = [link for link in links if link.startswith(pages_base) and link.endswith("/report.html")]
    assert len(report_links) == 5
    for link in report_links:
        relative = unquote(urlparse(link).path.removeprefix("/User-Persona-Skill/"))
        assert (ROOT / relative).is_file(), link


def test_reference_report_set_is_exact_and_valid() -> None:
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs" / "reference" / "reports").rglob("report.html")
    }
    assert actual == EXPECTED_REPORTS
    for relative in sorted(EXPECTED_REPORTS):
        report = ROOT / relative
        text = report.read_text(encoding="utf-8")
        assert "</title>" in text
        assert "<body>" in text and "</body>" in text
        assert '<section class="persona-slide' in text or '<section class="persona-slide active' in text
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_html.py"), str(report), "--json"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        payload = json.loads(proc.stdout)
        assert payload["error_count"] == 0, relative


def test_prompt_corpus_uses_shared_language_contract_and_anonymous_examples() -> None:
    prompt_dir = ROOT / "assets" / "prompts"
    prompts = sorted(prompt_dir.glob("*"))
    assert prompts
    banned_examples = ("孔老师", "刘老师", "冯老师", "邓老师", "碳中和老师")
    for path in prompts:
        if not path.is_file():
            continue
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path.name
        text = raw.decode("utf-8")
        assert not any(name in text for name in banned_examples), path.name
    shared = (prompt_dir / "_shared-language-contract.txt").read_text(encoding="utf-8")
    for phrase in ("只输出任务要求的 JSON", "证据", "具体", "完整姓名"):
        assert phrase in shared
    assert "页面条数、模块容量和视觉密度不能成为删除研究真值的理由" in shared
    for name in (
        "reduce_responsibilities.txt", "reduce_scenario_list.txt", "reduce_string_list.txt",
        "reduce_system_list.txt", "reduce_titled_list.txt",
    ):
        text = (prompt_dir / name).read_text(encoding="utf-8")
        assert "完整保存" in text
        assert "[来源:访谈_" not in text


def test_default_avatar_library_is_available() -> None:
    avatars = list((ROOT / "assets" / "default-avatars").glob("*.png"))
    assert len(avatars) >= 5


def test_human_guide_exposes_only_human_decisions_and_valid_links() -> None:
    guide_path = ROOT / "人类用户说明书.html"
    text = guide_path.read_text(encoding="utf-8")
    for internal_term in (
        "SKILL.md", "scripts/", "组件 schema", "renderer", "content_ref", "display_components",
        "processed", "extracted", "reduced", "palette pack", "assets/default-avatars/",
        "不要通过删正文", "某一步只有 MD 或只有 JSON", "中断与异常",
    ):
        assert internal_term not in text
    for phrase in (
        "确认研究目标", "确认画像方式", "确认分类内容", "确认字段与视觉范围",
        "确认画像内容", "确认旅程内容", "确认报告结构",
    ):
        assert phrase in text
    assert "交给其他 AI" in text and "复制到 PPT" in text
    assert "你可以修改、删减或补充任何正文" in text
    assert "同步更新对应的 JSON" in text
    for label in (
        "单画像 · toB/toD", "单画像 · toC", "多角色 · toB/toD",
        "二维矩阵 · toC", "多维分布 · toC",
    ):
        assert label in text
    for href in re.findall(r'href="([^"]+)"', text):
        if href.startswith("#") or "://" in href:
            continue
        assert (guide_path.parent / href).resolve().is_file(), href


def test_root_repository_markers_have_active_purposes() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".pytest_cache/" in ignored
    assert "scripts/tests/_reports/" in ignored
    assert "__pycache__/" in ignored and "*.pyc" in ignored
    assert "用户画像报告输出/" in ignored
    assert (ROOT / ".nojekyll").is_file()
    assert any(ROOT.rglob("_components.css"))


def test_visual_references_have_one_authoritative_entrypoint() -> None:
    assert not (ROOT / "docs" / "reference" / "gallery").exists()
    assert not (ROOT / "scripts" / "components" / "tests" / "build_gallery.py").exists()
    assert not (ROOT / "scripts" / "components" / "tests" / "gallery_template.html").exists()
    reports = list((ROOT / "docs" / "reference" / "reports").rglob("report.html"))
    assert len(reports) == 5


def test_devops_detail_reference_uses_confirmed_four_module_layout() -> None:
    report = (
        ROOT / "docs" / "reference" / "reports" / "B-多角色" /
        "2B-DevOps五角色" / "report.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<section\b[^>]*id="persona-4-detail"[^>]*>(.*?)</section>',
        report,
        re.S,
    )
    assert match
    section = match.group(1)
    assert "工作流摘要" not in section
    assert section.count('<div class="grid-module ') == 4
    assert 'grid-module-painpoint-list grid-anchor-end' in section
