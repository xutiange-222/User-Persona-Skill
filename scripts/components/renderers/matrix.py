from __future__ import annotations

from ._utils import escape, escape_for_data_attr, format_evidence


def render_matrix_guidance_strip(props: dict) -> str:
    items = []
    for item in props["items"]:
        label = item.get("label") or item.get("question", "")
        hint = item.get("hint")
        if hint is None:
            hint = " / ".join(str(p) for p in item.get("points", []))
        items.append(
            '<div class="matrix-guidance-item">'
            f'<div class="mg-label">{escape(label)}</div>'
            f'<div class="mg-hint">{escape(hint)}</div>'
            '</div>'
        )
    return f'<div class="matrix-guidance-strip">{"".join(items)}</div>'


def which_quadrant(x, y):
    if x >= 50 and y < 50:
        return "q1"
    if x < 50 and y < 50:
        return "q2"
    if x < 50 and y >= 50:
        return "q3"
    return "q4"


def _quadrant_bucket(x: float, y: float) -> tuple[bool, bool]:
    return (x >= 50, y >= 50)


def compute_nudge_px(x: float, y: float, slot: int = 0) -> tuple[int, int]:
    """将 [三角][姓名] 整组向矩阵中心平移(px),远离四角象限胶囊。

    slot: 同象限第 N 个点(0-based),沿垂直于中心方向错开,避免标签互叠。
    """
    cx, cy = 50.0, 50.0
    dx, dy = cx - x, cy - y
    mag = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    ux, uy = dx / mag, dy / mag
    edge = min(x, 100 - x, y, 100 - y)
    strength = int(max(56, min(112, 130 - edge * 1.1)))
    nx = round(ux * strength)
    ny = round(uy * strength)
    # 垂直于「指向中心」方向错开同象限多点
    px = round(-uy * slot * 20)
    py = round(ux * slot * 20)
    return nx + px, ny + py


def render_quadrant(quadrant: dict) -> str:
    pos = quadrant["position"]
    if quadrant.get("is_empty"):
        return f'<div class="matrix-quadrant {pos} matrix-empty-quadrant"><span class="empty-tag">本研究样本未覆盖</span></div>'
    return (
        f'<div class="matrix-quadrant {pos}">'
        f'<button class="matrix-quadrant-label" data-target="{escape(quadrant["id"], quote=True)}">{escape(quadrant["label"])}</button>'
        '</div>'
    )


def _respondent_evidence(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return format_evidence([raw])
    if isinstance(raw, list):
        return format_evidence(raw)
    return ""


def render_matrix_2d(props: dict) -> str:
    axis = props["axis_labels"]
    quadrants = "".join(render_quadrant(q) for q in props["quadrants"])
    respondents = []
    quadrant_slots: dict[tuple[bool, bool], int] = {}

    for r in props["respondents"]:
        x = float(r["x"])
        y = float(r["y"])
        bucket = _quadrant_bucket(x, y)
        slot = quadrant_slots.get(bucket, 0)
        quadrant_slots[bucket] = slot + 1
        nx, ny = compute_nudge_px(x, y, slot)
        evidence = _respondent_evidence(r.get("evidence", []))
        ev_attr = f' data-evidence="{escape_for_data_attr(evidence)}"' if evidence else ""
        style = (
            f' style="left:{x:.1f}%;top:{y:.1f}%;'
            f"--matrix-nudge-x:{nx}px;--matrix-nudge-y:{ny}px\""
        )
        respondents.append(
            f'<div class="matrix-respondent"{ev_attr}{style}>'
            f'<span class="matrix-respondent-dot"></span>'
            f'<span class="respondent-label">{escape(r["display_name"])}</span>'
            f'</div>'
        )

    return (
        '<div class="matrix-container">'
        '<div class="matrix-axis horizontal"></div><div class="matrix-axis vertical"></div>'
        f'<div class="matrix-axis-label top">{escape(axis["top"])}</div>'
        f'<div class="matrix-axis-label bottom">{escape(axis["bottom"])}</div>'
        f'<div class="matrix-axis-label left">{escape(axis["left"])}</div>'
        f'<div class="matrix-axis-label right">{escape(axis["right"])}</div>'
        f'{quadrants}{"".join(respondents)}</div>'
    )
