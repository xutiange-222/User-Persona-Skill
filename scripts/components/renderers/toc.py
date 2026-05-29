from __future__ import annotations

from pathlib import Path

from ._utils import (
    escape,
    escape_allow_strong,
    effective_avatar_filename,
    format_evidence,
    format_evidence_attr,
    render_illust,
    screenshot_exists,
)


def render_identity_card(props: dict) -> str:
    name = props["name"]
    tags = "".join(
        f'<div class="meta-tag-card"><span class="meta-tag-label">{escape(tag["label"])}</span>'
        f'<span class="meta-tag-value">{escape(tag["value"])}</span></div>'
        for tag in props["meta_tags"]
    )
    return (
        '<div class="identity-card">'
        f'{render_illust(props.get("illust_path"), name)}'
        '<div>'
        f'<h1 class="persona-name-anchor">{escape(name)}</h1>'
        f'<p class="persona-subtitle">{escape(props["subtitle"])}</p>'
        '</div>'
        f'<div class="meta-tags-list">{tags}</div>'
        '</div>'
    )


def render_persona_quote_pull(props: dict) -> str:
    evidence = format_evidence(props.get("evidence_quotes", []))
    evidence_attr = f' data-evidence="{format_evidence_attr(props.get("evidence_quotes", []))}"' if evidence else ""
    return (
        f'<div class="persona-quote-pull"{evidence_attr}>'
        f'{escape(props["quote"])}'
        f'<span class="quote-source">— {escape(props["source"])}</span>'
        '</div>'
    )


def render_section_block(props: dict) -> str:
    full_width_cls = " full-width" if props.get("full_width") else ""
    return (
        f'<div class="section-block{full_width_cls}">'
        f'<div class="section-block-title">{escape(props["title"])}</div>'
        f'<div class="section-block-summary">{escape(props["summary"])}</div>'
        f'<div class="section-block-body" data-evidence="{format_evidence_attr(props["evidence_quotes"])}">{escape_allow_strong(props["body"])}</div>'
        '</div>'
    )


def _validate_blocks_combo(blocks: list[dict]) -> None:
    n = len(blocks)
    full_count = sum(1 for b in blocks if b.get("full_width"))
    if n not in (4, 5, 6):
        raise ValueError(f"section_blocks_grid: block count must be 4/5/6, got {n}")
    valid = (
        (n == 4 and full_count in (0, 1, 2))
        or (n == 5 and full_count == 1)
        or (n == 6 and full_count == 0)
    )
    if not valid:
        raise ValueError(
            f"section_blocks_grid: illegal combination — {n} blocks with "
            f"{full_count} full_width. Legal: 4(+0|1|2 full) / 5(+1 full) / 6(+0 full)."
        )


def render_section_blocks_grid(props: dict) -> str:
    blocks = props["blocks"]
    if "full_width_index" in props:
        idx = int(props["full_width_index"])
        if 0 <= idx < len(blocks):
            blocks = [dict(b) for b in blocks]
            blocks[idx]["full_width"] = True
    if len(blocks) >= 4:
        _validate_blocks_combo(blocks)
    rendered = [render_section_block(b) for b in blocks]
    return f'<div class="section-blocks-grid count-{len(rendered)}">{"".join(rendered)}</div>'


def _optional_evidence_attr(quotes: list[dict]) -> str:
    evidence = format_evidence_attr(quotes)
    return f' data-evidence="{evidence}"' if evidence else ""


def render_detail_headline(props: dict) -> str:
    headline = escape(props["headline"]).replace("\n", "<br>")
    return f'<h1 class="l2c-headline">{headline}</h1>'


def _render_mockup_frame(mockup: dict) -> str:
    screenshot = mockup.get("screenshot")
    if screenshot and screenshot_exists(screenshot):
        return (
            '<div class="mockup-frame mockup-frame--has-img">'
            f'<img class="mockup-img" src="assets/界面截图/{escape(screenshot, quote=True)}" alt="">'
            '</div>'
        )
    label = mockup.get("frame_label") or mockup.get("frame", "")
    label_html = f'<br>{escape(label)}' if label else ""
    return f'<div class="mockup-frame">📱{label_html}</div>'


def render_mockup_list(props: dict) -> str:
    mockups = props["mockups"]
    n = len(mockups)
    items = "".join(
        f'<div class="mockup-item">{_render_mockup_frame(m)}'
        f'<div class="mockup-caption">{escape(m["caption"])}</div></div>'
        for m in mockups
    )
    return f'<div class="mockup-list mockup-{n}">{items}</div>'


def render_detail_analysis(props: dict) -> str:
    sections = []
    for sec in props["sections"]:
        evidence_attr = _optional_evidence_attr(sec.get("evidence_quotes", []))
        sections.append(
            '<div class="l2c-analysis-section">'
            f'<div class="l2c-analysis-title">{escape(sec["title"])}</div>'
            f'<div class="l2c-analysis-body"{evidence_attr}>{escape_allow_strong(sec["body"])}</div>'
            '</div>'
        )
    return "".join(sections)


def render_detail_illust_corner(props: dict) -> str:
    image_path = props.get("illust_path")
    persona_name = props.get("name") or (Path(image_path).stem if image_path else "")
    filename = effective_avatar_filename(image_path, persona_name)
    if not filename:
        return ""
    return f'<img class="l2c-corner" src="assets/画像头像素材/{escape(filename, quote=True)}" alt="">'
