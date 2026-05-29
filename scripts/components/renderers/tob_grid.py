from __future__ import annotations

import math

from ._utils import attach_grid_protocol, escape, format_evidence, format_evidence_attr, mention_badge, render_avatar, screenshot_exists


def _evidence_attr(quotes: list[dict]) -> str:
    return format_evidence_attr(quotes)


def _optional_evidence_attr(quotes: list[dict]) -> str:
    evidence = _evidence_attr(quotes)
    return f' data-evidence="{evidence}"' if evidence else ""


def render_identity_panel(props: dict) -> str:
    avatar = props["persona_avatar"]
    identity_name = props["identity_name"]
    name = identity_name["name"]
    alias = identity_name.get("alias")
    image_path = avatar.get("image_path")
    alt = avatar.get("alt", name)
    avatar_html = render_avatar(image_path, name, alt=alt)

    name_html = f'<div class="name-line">{escape(name)}</div>'
    if alias:
        name_html += f'<div class="name-line">{escape(alias)}</div>'

    def _br(s: str) -> str:
        # 允许 LLM 用 \n 换行;先 escape 再把转义后的占位换成 <br>
        return "<br>".join(escape(part) for part in s.split("\n"))
    meta = "".join(
        f'<div class="meta-row"><div class="meta-label">{_br(row["key"])}</div>'
        f'<div class="meta-value">{_br(row["value"])}</div></div>'
        for row in props["identity_meta_rows"]
    )
    need = props["one_sentence_need"]
    return (
        '<div class="identity-panel">'
        f'<div class="avatar-wrap">{avatar_html}</div>'
        f'<div class="identity-name">{name_html}</div>'
        f'<div class="identity-desc">{escape(props["identity_desc"])}</div>'
        f'<div class="identity-meta">{meta}</div>'
        '<div class="one-sentence-need">'
        f'<div class="osn-text">{escape(need["text"])}</div>'
        f'<div class="osn-source">— {escape(need["source"])}</div>'
        '</div></div>'
    )


def render_resp_rings(props: dict) -> str:
    radius = 24
    circumference = 2 * math.pi * radius
    items = []
    for ring in props["rings"]:
        pct = ring["percentage"]
        offset = circumference * (1 - pct / 100)
        evidence_attr = _evidence_attr(ring.get("evidence_quotes", []))
        attr_html = f' data-evidence="{evidence_attr}"' if evidence_attr else ""
        items.append(
            f'<div class="ring-item"{attr_html}>'
            '<svg class="ring-svg" viewBox="0 0 64 64">'
            f'<circle class="ring-track" cx="32" cy="32" r="{radius}"/>'
            f'<circle class="ring-fill" cx="32" cy="32" r="{radius}" stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}"/>'
            f'<text class="ring-pct" x="32" y="38" text-anchor="middle">{int(pct)}%</text>'
            '</svg>'
            f'<div class="ring-label">{escape(ring["label"])}</div>'
            '</div>'
        )
    return f'<div class="resp-rings">{"".join(items)}</div>'


def estimate_rows_resp_rings(props: dict) -> int:
    return 1


def min_cols_resp_rings(props: dict) -> int:
    return 6


def render_collab_flow(props: dict) -> str:
    """P7 契约对齐:label 硬编码 + data-field-key 三段固定。

    LLM 只填 value(具体内容),label 由 renderer 给出。
    这从根因切断「LLM 自创"上游/核心/下游"label 被 P7-BANNED-COLLAB-LABEL 拦截」的同类问题。
    """
    cells = [
        ("demand_source", "需求来源", props["demand_source"], False),
        ("deliverables", "交付物", props["deliverables"], True),
        ("downstream_flow", "下一步流转", props["downstream_flow"], False),
    ]
    flow = []
    for key, label, value, highlight in cells:
        cls = "flow-cell highlight" if highlight else "flow-cell"
        evidence_attr = _optional_evidence_attr(props.get(f"{key}_evidence_quotes", []))
        flow.append(
            f'<div class="{cls}" data-field-key="{key}"{evidence_attr}>'
            f'<div class="flow-cell-label">{escape(label)}</div>'
            f'<div class="flow-cell-value">{escape(value)}</div>'
            f'</div>'
        )
    kpi = props["kpi"]
    kpi_evidence_attr = _optional_evidence_attr(kpi.get("evidence_quotes", []))
    return (
        f'<div class="collab-flow">{"".join(flow)}</div>'
        f'<div class="kpi-block" data-field-key="kpi"{kpi_evidence_attr}>'
        f'<span class="kpi-label">{escape(kpi["title"])}</span>{escape(kpi["value"])}'
        f'</div>'
    )


def estimate_rows_collab_flow(props: dict) -> int:
    return 1


def min_cols_collab_flow(props: dict) -> int:
    return 6


def _render_scenario_grid(props: dict, is_ai: bool) -> str:
    """Scenario cards: image or placeholder -> caption -> optional description."""
    scenes = props["scenes"]
    grid_ai_cls = " is-ai" if is_ai else ""
    card_ai_cls = " is-ai" if is_ai else ""
    cards = []
    for scene in scenes:
        title = scene.get("title") or scene.get("caption", "")
        desc = scene.get("description", "")
        tools = scene.get("tools", [])
        tools_tag_html = "".join(f'<span class="tool-icon-tag">{escape(t)}</span>' for t in tools[:4])
        tools_caption = " / ".join(str(t) for t in tools)

        screenshot = scene.get("screenshot")
        has_real_image = bool(screenshot and screenshot_exists(screenshot))
        if has_real_image:
            img_html = f'<div class="scenario-image"><img src="assets/界面截图/{escape(screenshot, quote=True)}" alt="{escape(title, quote=True)}"></div>'
        else:
            img_html = f'<div class="scenario-image scenario-image-empty"><div class="scenario-placeholder-icons">{tools_tag_html}</div></div>'

        ev_html = _optional_evidence_attr(scene.get("evidence_quotes", []))
        has_image_cls = " has-image" if has_real_image else ""
        caption_tail = (
            f'<br><span class="scenario-tool-names">{escape(tools_caption)}</span>'
            if tools_caption
            else ""
        )
        desc_html = f'<div class="scenario-desc">{escape(desc)}</div>' if desc else ""

        cards.append(
            f'<div class="scenario-card{card_ai_cls}{has_image_cls}"{ev_html}>'
            f'{img_html}'
            f'<div class="scenario-caption"><strong>{escape(title)}</strong>{caption_tail}</div>'
            f'{desc_html}'
            f'</div>'
        )
    return f'<div class="scenarios-grid-{len(scenes)}{grid_ai_cls}">{"".join(cards)}</div>'


def render_scenario_grid(props: dict) -> str:
    return _render_scenario_grid(props, False)


def estimate_rows_scenario_grid(props: dict) -> int:
    return 1 if len(props["scenes"]) <= 2 else 2


def min_cols_scenario_grid(props: dict) -> int:
    return 6 if len(props["scenes"]) <= 2 else 12


def render_ai_scenario_grid(props: dict) -> str:
    return _render_scenario_grid(props, True)


def estimate_rows_ai_scenario_grid(props: dict) -> int:
    return estimate_rows_scenario_grid(props)


def min_cols_ai_scenario_grid(props: dict) -> int:
    return 6 if len(props["scenes"]) <= 2 else 12


def render_painpoint_list(props: dict) -> str:
    items = []
    for item in props["items"]:
        badge = mention_badge(item.get("mention_badge"))
        sep = '<span class="pp-sep"> | </span>'
        evidence_attr = _optional_evidence_attr(item.get("evidence_quotes", []))
        items.append(
            f'<li class="painpoint-item has-inline-metric"{evidence_attr}>'
            f'<span class="pp-title">{escape(item["title"])}</span>'
            f'{badge}'
            f'{sep}'
            f'<span class="pp-detail">{escape(item["detail"])}</span>'
            '</li>'
        )
    return f'<ul class="painpoints-list">{"".join(items)}</ul>'


def estimate_rows_painpoint_list(props: dict) -> int:
    # 真值 2B-DevOps 即使 5 个 items 也占单 grid row,
    # 沿用旧值 2 会让 grid_solver 误判溢出触发自动双页,与显式 detail tab 冲突。
    return 1


def min_cols_painpoint_list(props: dict) -> int:
    return 6


def render_titled_list(props: dict) -> str:
    items = []
    for item in props["items"]:
        insight = item.get("insight")
        insight_html = f'<span class="gl-insight">{escape(insight)}</span>' if insight else ""
        evidence_attr = _optional_evidence_attr(item.get("evidence_quotes", []))
        items.append(
            f'<li class="generic-list-item"{evidence_attr}>'
            f'<span class="gl-title">{escape(item["title"])}</span>'
            f'<span class="gl-detail">{escape(item["detail"])}</span>'
            f'{insight_html}'
            '</li>'
        )
    return f'<ul class="generic-list">{"".join(items)}</ul>'


def estimate_rows_titled_list(props: dict) -> int:
    return 1


def min_cols_titled_list(props: dict) -> int:
    return 6


def render_generic_text(props: dict) -> str:
    return f'<div class="generic-text-card">{escape(props["text"])}</div>'


def estimate_rows_generic_text(props: dict) -> int:
    return 1


def min_cols_generic_text(props: dict) -> int:
    return 6


def render_generic_bullet(props: dict) -> str:
    items = "".join(f'<li class="generic-bullet-item"><span class="bullet-text">{escape(i)}</span></li>' for i in props["items"])
    return f'<ul class="generic-bullet-list">{items}</ul>'


def estimate_rows_generic_bullet(props: dict) -> int:
    return 1 if len(props["items"]) <= 4 else 2


def min_cols_generic_bullet(props: dict) -> int:
    return 6


def render_generic_kv(props: dict) -> str:
    headers = props.get("headers")
    header_html = (
        f'<div class="kv-row kv-header-row">'
        f'<div class="kv-key">{escape(headers[0])}</div>'
        f'<div class="kv-value">{escape(headers[1])}</div>'
        '</div>'
        if headers else ""
    )
    rows = "".join(
        f'<div class="kv-row"><div class="kv-key">{escape(r["key"])}</div><div class="kv-value">{escape(r["value"])}</div></div>'
        for r in props["rows"]
    )
    return f'<div class="generic-kv-card">{header_html}{rows}</div>'


def estimate_rows_generic_kv(props: dict) -> int:
    return 1 if len(props["rows"]) <= 4 else 2


def min_cols_generic_kv(props: dict) -> int:
    return 6


for _name in (
    "resp_rings",
    "collab_flow",
    "scenario_grid",
    "ai_scenario_grid",
    "painpoint_list",
    "titled_list",
    "generic_text",
    "generic_bullet",
    "generic_kv",
):
    attach_grid_protocol(globals()[f"render_{_name}"], globals()[f"estimate_rows_{_name}"], globals()[f"min_cols_{_name}"])


