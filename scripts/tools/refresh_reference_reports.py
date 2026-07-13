#!/usr/bin/env python3
"""刷新并校验人类说明书中的五份参考报告。

维护范围固定为 A/2B、A/2C、B/2B、D/2C、E/2C。脚本只读取仓库内文件，
不依赖旧版本目录或外部项目。A 类单画像从 B/2B 和 D/2C 裁切生成。
"""
from __future__ import annotations

import html as html_lib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.components.layouts.layout_rules import accent_inline  # noqa: E402
from scripts.components.renderers.tob_journey import _stage_grid_columns  # noqa: E402

REPORTS = ROOT / "docs" / "reference" / "reports"
TEMPLATES = ROOT / "assets" / "templates"

B_2B = REPORTS / "B-多角色" / "2B-DevOps五角色"
D_2C = REPORTS / "D-二维矩阵" / "2C-HiRes-2维"
E_2C = REPORTS / "E-多维分布" / "2C-HiRes-多区分点"
A_2B = REPORTS / "A-单画像" / "2B-保障型运维工程师"
A_2C = REPORTS / "A-单画像" / "2C-内行场景派"

RETAINED = (A_2B, A_2C, B_2B, D_2C, E_2C)

HEX_TO_ACCENT = {
    "#9664ff": "purple",
    "#f05a28": "warm-orange",
    "#82b4b4": "moss-green",
    "#ffb41e": "mustard",
    "#5a8cfa": "mist-blue",
    "#32b4dc": "cyan-gold",
}
STYLE_TO_ACCENT = {
    "purple-default": "purple",
    "red-orange": "warm-orange",
    "green-gray": "moss-green",
    "yellow-orange": "mustard",
    "blue-yellow": "mist-blue",
    "cyan-gold": "cyan-gold",
}


def _extract_balanced(text: str, start: int, tag: str) -> tuple[str, int]:
    token = re.compile(rf"</?{tag}\b[^>]*>", re.I)
    depth = 0
    for match in token.finditer(text, start):
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return text[start:match.end()], match.end()
        else:
            depth += 1
    raise ValueError(f"unclosed <{tag}> at offset {start}")


def _extract_element(text: str, pattern: str, tag: str) -> str:
    match = re.search(pattern, text, re.I)
    if not match:
        raise ValueError(f"element not found: {pattern}")
    return _extract_balanced(text, match.start(), tag)[0]


def _extract_sections(text: str) -> list[str]:
    sections: list[str] = []
    seen_ids: set[str] = set()
    cursor = 0
    start_pattern = re.compile(r'<section\b[^>]*class="[^"]*persona-slide[^"]*"[^>]*>', re.I)
    while match := start_pattern.search(text, cursor):
        section, cursor = _extract_balanced(text, match.start(), "section")
        section_id = _section_id(section)
        if section_id and section_id not in seen_ids:
            sections.append(section)
            seen_ids.add(section_id)
    if not sections:
        raise ValueError("no persona-slide sections found")
    return sections


def _section_id(section: str) -> str:
    match = re.search(r'\bid="([^"]+)"', section[:1000])
    return html_lib.unescape(match.group(1)) if match else ""


def _pick_sections(text: str, ids: list[str]) -> list[str]:
    index = {_section_id(section): section for section in _extract_sections(text)}
    missing = [sid for sid in ids if sid not in index]
    if missing:
        raise ValueError(f"missing sections: {missing}")
    return [index[sid] for sid in ids]


def _mark_first_active(sections: list[str]) -> list[str]:
    result: list[str] = []
    for index, section in enumerate(sections):
        head_end = section.find(">")
        head, body = section[:head_end], section[head_end:]
        head = re.sub(r'\sactive(?=[\s"]|$)', "", head)
        if index == 0:
            head = head.replace('class="persona-slide', 'class="persona-slide active', 1)
        result.append(head + body)
    return result


def _accent_for_section(section: str) -> str:
    head = section[: section.find(">") + 1]
    match = re.search(r"--color-accent:\s*var\(--accent-([a-z-]+)\)", head, re.I)
    if match:
        accent = match.group(1).lower()
        return {"clay-red": "cyan-gold"}.get(accent, accent)
    match = re.search(r"--color-toc-style:\s*([a-z-]+)", head, re.I)
    if match and match.group(1).lower() in STYLE_TO_ACCENT:
        return STYLE_TO_ACCENT[match.group(1).lower()]
    match = re.search(r"--color-accent:\s*(#[0-9a-f]{6})", head, re.I)
    if match and match.group(1).lower() in HEX_TO_ACCENT:
        return HEX_TO_ACCENT[match.group(1).lower()]
    raise ValueError(f"2C section {_section_id(section)!r} has no recognized palette")


def _inject_palette(section: str) -> str:
    if "layout-2c-" not in section[:1000]:
        return section
    accent = _accent_for_section(section)
    head_end = section.find(">")
    head, body = section[:head_end], section[head_end:]
    head = re.sub(r'\sstyle="[^"]*"', "", head)
    return f"{head} {accent_inline(accent)}{body}"


def _normalize_emotion_markup(section: str) -> str:
    """Bring retained static 2C examples onto the current emotion safe-area contract."""
    if "journey-emotion-row" not in section:
        return section
    section = section.replace(
        '<div class="journey-cell journey-dimension-label">情绪</div>',
        '<div class="journey-cell journey-dimension-label journey-emotion-dimension-label">情绪</div>',
    )
    point_re = re.compile(
        r'(<div class="journey-emotion-point" style="[^"]*top:)(25\.0|50\.0|75\.0)(%[^"]*">.*?<div class="emotion-label )(above|below)(">)',
        re.S,
    )

    def repl(match: re.Match[str]) -> str:
        top = match.group(2)
        label_class = "below" if top == "25.0" else "above"
        return f"{match.group(1)}{top}{match.group(3)}{label_class}{match.group(5)}"

    return point_re.sub(repl, section)


def _normalize_devops_detail_reference(text: str) -> str:
    """Keep the 2B detail reference aligned with the confirmed four-module layout."""
    pattern = r'<section\b[^>]*id="persona-4-detail"[^>]*>'
    match = re.search(pattern, text, re.I)
    if not match:
        raise ValueError("persona-4-detail reference section not found")
    section, _ = _extract_balanced(text, match.start(), "section")

    duplicate_title = ">工作流摘要</div>"
    title_at = section.find(duplicate_title)
    if title_at >= 0:
        module_at = section.rfind('<div class="grid-module ', 0, title_at)
        if module_at < 0:
            raise ValueError("工作流摘要 module wrapper not found")
        _, module_end = _extract_balanced(section, module_at, "div")
        section = section[:module_at] + section[module_end:]

    section = section.replace(
        'grid-module-titled-list grid-anchor-end" style="grid-column: 7 / span 6;"',
        'grid-module-titled-list grid-anchor-start" style="grid-column: 1 / span 6;"',
        1,
    )
    section = section.replace(
        'grid-module-painpoint-list grid-anchor-full" style="grid-column: 1 / span 12;"',
        'grid-module-painpoint-list grid-anchor-end" style="grid-column: 7 / span 6;"',
        1,
    )
    original, _ = _extract_balanced(text, match.start(), "section")
    text = text[:match.start()] + section + text[match.start() + len(original):]

    journey_match = re.search(r'<section\b[^>]*id="journey-l1"[^>]*>', text, re.I)
    if not journey_match:
        raise ValueError("journey-l1 reference section not found")
    journey, _ = _extract_balanced(text, journey_match.start(), "section")
    stage_count = len(re.findall(r'class="l1-stage-cell"', journey))
    if stage_count < 1:
        raise ValueError("journey-l1 stage cells not found")
    grid = _stage_grid_columns(stage_count)
    journey = re.sub(
        r'(<div class="l1-row (?:stage|substage)-row")\s+style="(?:grid-template-columns|--l1-grid-columns):[^"]+"',
        rf'\1 style="--l1-grid-columns:{grid};"',
        journey,
    )
    original_journey, _ = _extract_balanced(text, journey_match.start(), "section")
    return text[:journey_match.start()] + journey + text[journey_match.start() + len(original_journey):]


def _text_in_div(text: str, class_name: str, fallback: str) -> str:
    match = re.search(
        rf'<div\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>(.*?)</div>',
        text,
        re.I | re.S,
    )
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else fallback


def _title(text: str, fallback: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else fallback


def _nav(text: str) -> str:
    match = re.search(r'<div\b[^>]*class="[^"]*(?:persona-nav|demo-nav-area)[^"]*"[^>]*>', text, re.I)
    if not match:
        return ""
    nav, _ = _extract_balanced(text, match.start(), "div")
    return nav.replace("demo-nav-area", "persona-nav")


def _render_shell(
    *, source: str, sections: list[str], theme: str, density: str,
    title: str | None = None, report_title: str | None = None,
    report_meta_info: str | None = None, nav: str | None = None,
) -> str:
    base = (TEMPLATES / "_base.html").read_text(encoding="utf-8")
    sections = _mark_first_active([_normalize_emotion_markup(_inject_palette(section)) for section in sections])
    values = {
        "{{theme}}": theme,
        "{{density}}": density,
        "{{accent_inline}}": "",
        "{{title}}": title or _title(source, "用户画像报告"),
        "{{report_title}}": report_title or _text_in_div(source, "report-meta-title", "用户画像报告"),
        "{{report_meta_info}}": report_meta_info or _text_in_div(source, "report-meta-info", "参考样例"),
        "{{persona_nav}}": _nav(source) if nav is None else nav,
        "{{main_content}}": "\n".join(sections),
    }
    for slot, value in values.items():
        count = base.count(slot)
        if count != 1:
            raise ValueError(f"base slot {slot} must appear once, found {count}")
        base = base.replace(slot, value, 1)
    unresolved = re.findall(r"\{\{[a-z_]+\}\}", base)
    if unresolved:
        raise ValueError(f"unresolved base slots: {sorted(set(unresolved))}")
    return base


def _write_reframed(
    report_dir: Path, *, theme: str, density: str,
    title: str, report_title: str, report_meta_info: str,
) -> None:
    path = report_dir / "report.html"
    source = path.read_text(encoding="utf-8")
    output = _render_shell(
        source=source,
        sections=_extract_sections(source),
        theme=theme,
        density=density,
        title=title,
        report_title=report_title,
        report_meta_info=report_meta_info,
    )
    for old, new in (("可发布?", "可发布？"), ("覆盖可信?", "覆盖可信？"), ("变更批准?", "变更批准？")):
        output = output.replace(old, new)
    if report_dir == B_2B:
        output = _normalize_devops_detail_reference(output)
    path.write_text(output, encoding="utf-8")


def _copy_template_css(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    for name in ("_design-tokens.css", "_components.css"):
        shutil.copy2(TEMPLATES / name, report_dir / name)


def _build_single_reports() -> None:
    source_2b = (B_2B / "report.html").read_text(encoding="utf-8")
    nav_2b = (
        '<div class="persona-nav"><div class="nav-trio">'
        '<button class="nav-btn nav-btn-persona active" data-target="persona-1-core">保障型运维工程师</button>'
        '<button class="nav-btn nav-btn-detail" data-target="persona-1-detail">› 细节</button>'
        '<button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>'
        "</div></div>"
    )
    A_2B.mkdir(parents=True, exist_ok=True)
    (A_2B / "report.html").write_text(
        _render_shell(
            source=source_2b,
            sections=_pick_sections(source_2b, ["persona-1-core", "persona-1-detail", "persona-1-journey"]),
            theme="2b",
            density="high",
            title="保障型运维工程师 · 2B 单画像样例",
            report_title="保障型运维工程师",
            report_meta_info="2B 单画像 · 字段 hover 可查看证据",
            nav=nav_2b,
        ),
        encoding="utf-8",
    )

    source_2c = (D_2C / "report.html").read_text(encoding="utf-8")
    nav_2c = (
        '<div class="persona-nav"><div class="nav-trio">'
        '<button class="nav-btn nav-btn-persona active" data-target="persona-1">内行场景派</button>'
        '<button class="nav-btn nav-btn-detail" data-target="persona-1-detail">› 细节</button>'
        '<button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>'
        "</div></div>"
    )
    A_2C.mkdir(parents=True, exist_ok=True)
    (A_2C / "report.html").write_text(
        _render_shell(
            source=source_2c,
            sections=_pick_sections(source_2c, ["persona-1", "persona-1-detail", "persona-1-journey"]),
            theme="2c",
            density="low",
            title="内行场景派 · 2C 单画像样例",
            report_title="内行场景派",
            report_meta_info="2C 单画像 · 画像、详情与旅程共用色卡",
            nav=nav_2c,
        ),
        encoding="utf-8",
    )


def _copy_referenced_assets(source_dir: Path, target_dir: Path) -> None:
    html = (target_dir / "report.html").read_text(encoding="utf-8")
    refs = {
        html_lib.unescape(match).replace("/", "\\")
        for match in re.findall(r'(?:src|href)="(assets/[^"?#]+)', html, re.I)
    }
    target_assets = target_dir / "assets"
    if target_assets.exists():
        shutil.rmtree(target_assets)
    for ref in sorted(refs):
        relative = Path(ref).relative_to("assets")
        candidates = [source_dir / "assets" / relative, B_2B / "assets" / relative, D_2C / "assets" / relative, E_2C / "assets" / relative]
        source = next((path for path in candidates if path.is_file()), None)
        if source is None:
            raise FileNotFoundError(f"missing referenced asset: {ref}")
        destination = target_assets / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _prune_assets(report_dir: Path) -> None:
    assets = report_dir / "assets"
    if not assets.exists():
        return
    html = (report_dir / "report.html").read_text(encoding="utf-8")
    keep = {
        (report_dir / Path(html_lib.unescape(ref))).resolve()
        for ref in re.findall(r'(?:src|href)="(assets/[^"?#]+)', html, re.I)
    }
    for path in sorted((p for p in assets.rglob("*") if p.is_file()), reverse=True):
        if path.resolve() not in keep:
            path.unlink()
    for path in sorted((p for p in assets.rglob("*") if p.is_dir()), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()


def _validate() -> None:
    for report_dir in RETAINED:
        report = report_dir / "report.html"
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_html.py"), str(report)],
            cwd=ROOT,
            check=True,
        )


def main() -> None:
    for directory in (B_2B, D_2C, E_2C):
        if not (directory / "report.html").is_file():
            raise FileNotFoundError(directory / "report.html")

    _write_reframed(
        B_2B, theme="2b", density="high",
        title="DevOps 平台多角色用户画像",
        report_title="DevOps 平台多角色用户画像",
        report_meta_info="5 个画像 · 总体旅程与单角色旅程",
    )
    _write_reframed(
        D_2C, theme="2c", density="low",
        title="华为音乐 Hi-Res 用户二维矩阵",
        report_title="华为音乐 Hi-Res 用户二维矩阵",
        report_meta_info="5 个画像 · 二维矩阵 · 详情与旅程",
    )
    _write_reframed(
        E_2C, theme="2c", density="low",
        title="华为音乐 Hi-Res 用户多维分布",
        report_title="华为音乐 Hi-Res 用户多维分布",
        report_meta_info="5 个画像 · 多维分布 · 详情与旅程",
    )
    _build_single_reports()

    for directory in RETAINED:
        _copy_template_css(directory)
    _copy_referenced_assets(B_2B, A_2B)
    _copy_referenced_assets(D_2C, A_2C)
    for directory in (B_2B, D_2C, E_2C):
        _prune_assets(directory)

    _validate()
    print("[OK] five reference reports refreshed and validated")


if __name__ == "__main__":
    main()
