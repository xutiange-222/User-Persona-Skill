from __future__ import annotations

from ._utils import escape, format_evidence, format_evidence_attr, render_illust


def _optional_evidence_attr(quotes: list[dict]) -> str:
    evidence = format_evidence_attr(quotes)
    return f' data-evidence="{evidence}"' if evidence else ""


# 33 个语义名 → Unicode emoji 字符。
# 渲染时直接输出 Unicode,依赖浏览器系统 emoji 字体(Win/Mac/Linux/移动端都内置)。
# 不再依赖 assets/icons/emoji/*.png 文件,跨设备视觉一致。
EMOJI_UNICODE_MAP = {
    # 笑脸 / 愉悦 (8)
    "smile": "🙂", "smile_blush": "😊", "grin": "😀", "laughing": "😄",
    "content": "😌", "relaxed": "☺️", "proud": "😎", "star_struck": "🤩",
    # 困惑 / 思考 (5)
    "thinking": "🤔", "confused": "😕", "raised_eyebrow": "🤨",
    "neutral": "😐", "hmm": "🙄",
    # 消极 / 负面 (7)
    "frowning": "😦", "disappointed": "😞", "frustrated": "😩",
    "persevere": "😣", "tired": "😪", "sad": "🙁", "crying": "😢",
    # 惊讶 / 强反应 (3)
    "surprised": "😯", "shocked": "😲", "exclamation": "❗",
    # 兴奋 / 积极 (4)
    "excited": "😆", "celebrate": "🎉", "fire": "🔥", "heart_eyes": "😍",
    # 物品 / 隐喻 (6)
    "headphone": "🎧", "light_bulb": "💡", "target": "🎯",
    "thumbs_up": "👍", "thumbs_down": "👎", "question": "❓",
}
EMOJI_VALID_SET = set(EMOJI_UNICODE_MAP.keys())


def parse_frequency(freq: str) -> float:
    try:
        n, total = map(int, freq.split("/"))
        return n / total
    except (ValueError, ZeroDivisionError):
        return 0.0


def render_emotion_row(emotion: list[dict], n_stages: int) -> str:
    level_y = {"high": 20, "middle": 40, "low": 60}
    viewbox_w = 500
    viewbox_h = 80
    points = [((idx + 0.5) / n_stages * viewbox_w, level_y[e["level"]]) for idx, e in enumerate(emotion)]
    path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(1, len(points)):
        if i == 1:
            cx, cy = (points[0][0] + points[1][0]) / 2, points[0][1]
            path_d += f" Q {cx:.1f} {cy:.1f} {points[1][0]:.1f} {points[1][1]:.1f}"
        else:
            path_d += f" T {points[i][0]:.1f} {points[i][1]:.1f}"
    area_d = path_d + f" L {points[-1][0]:.1f} {viewbox_h} L {points[0][0]:.1f} {viewbox_h} Z"
    nodes = []
    for e, (x, y) in zip(emotion, points):
        emoji_name = e["emoji"]
        if emoji_name not in EMOJI_UNICODE_MAP:
            raise ValueError(f"invalid emoji: {emoji_name}(合法 33 个见 EMOJI_UNICODE_MAP)")
        emoji_char = EMOJI_UNICODE_MAP[emoji_name]
        label_cls = "above" if y <= 46 else "below"
        nodes.append(
            f'<div class="journey-emotion-point" style="left:{x/viewbox_w*100:.1f}%;top:{y/viewbox_h*100:.1f}%">'
            '<span class="emotion-dot"></span>'
            f'<div class="emotion-label {label_cls}">'
            f'<span class="emoji" aria-label="{escape(emoji_name, quote=True)}">{emoji_char}</span>'
            f'<span class="label-text">{escape(e["stage_label"])}</span></div></div>'
        )
    return (
        '<div class="journey-emotion-row">'
        f'<svg class="journey-emotion-svg" viewBox="0 0 {viewbox_w} {viewbox_h}" preserveAspectRatio="none">'
        f'<path class="emotion-area" d="{area_d}"/><path d="{path_d}"/></svg>'
        f'<div class="journey-emotion-points-overlay">{"".join(nodes)}</div></div>'
    )


def render_journey_2c(props: dict) -> str:
    stages = props["stages"]
    header = ['<div class="journey-cell journey-dimension-label">阶段</div>']
    for idx, stage in enumerate(stages, start=1):
        header.append(
            '<div class="journey-cell journey-stage-header">'
            f'<span class="journey-stage-number">{idx}</span>{escape(stage)}</div>'
        )
    rows = []
    for dim, cells in zip(props["dimensions"], props["cells"]):
        row_cells = []
        for cell in cells:
            cls = "journey-cell"
            if parse_frequency(cell.get("frequency", "0/1")) >= 0.8:
                cls += " journey-pain-highlight"
            evidence_attr = _optional_evidence_attr(cell.get("evidence_quotes", []))
            touchpoints = ""
            if cell.get("touchpoints"):
                tags = "".join(f'<span class="touchpoint-tag">{escape(t)}</span>' for t in cell["touchpoints"])
                touchpoints = f'<div class="journey-cell-touchpoint">{tags}</div>'
            row_cells.append(
                f'<div class="{cls}"{evidence_attr}><span class="journey-cell-keyword">{escape(cell["keyword"])}</span>'
                f'<div class="journey-cell-summary">{escape(cell["summary"])}</div>{touchpoints}</div>'
            )
        rows.append(f'<div class="journey-cell journey-dimension-label">{escape(dim)}</div>{"".join(row_cells)}')

    title = props["title"]
    if "·" not in title and title.endswith("旅程") and len(title) > 2:
        title = f'{title[:-2].rstrip()} · 旅程'
    # schema 已强制 title minLength:1,title[:1] 永远非空
    initial = title[:1]
    illust_html = render_illust(props.get("illust_path"), title, placeholder=initial)
    emotion_label = '<div class="journey-cell journey-dimension-label">情绪</div>'
    return (
        '<div class="journey-header">'
        f'{illust_html}'
        '<div>'
        f'<div class="journey-title">{escape(title)}</div>'
        f'<div class="journey-subtitle">{escape(props["subtitle"])}</div>'
        '</div></div>'
        f'<div class="journey-grid" style="--journey-stages: {len(stages)};">'
        f'{"".join(header)}{"".join(rows)}{emotion_label}{render_emotion_row(props["emotion"], len(stages))}</div>'
    )

