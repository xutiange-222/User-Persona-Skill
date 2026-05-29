from __future__ import annotations

import os
import re
from html import escape as _escape
from pathlib import Path

from scripts.avatar_assets import (
    avatar_available,
    effective_avatar_filename,
    resolve_avatar_file,
)

__all__ = [
    "avatar_available",
    "effective_avatar_filename",
    "escape",
    "escape_allow_strong",
    "format_evidence",
    "format_evidence_attr",
    "illust_exists",
    "render_avatar",
    "render_illust",
    "resolve_avatar_file",
    "screenshot_exists",
]


def escape(s, quote: bool = True) -> str:
    """html.escape wrapper; quote=True is safe for text and attributes."""
    if s is None:
        return ""
    return _escape(str(s), quote=quote)


_STRONG_INNER_RE = re.compile(r"<strong>([^<>]+?)</strong>", re.DOTALL)


def escape_allow_strong(s) -> str:
    """Escape HTML, preserving only plain-text <strong>...</strong> blocks."""
    if s is None:
        return ""
    text = str(s)
    out = []
    last = 0
    for m in _STRONG_INNER_RE.finditer(text):
        out.append(_escape(text[last:m.start()], quote=True))
        out.append(f"<strong>{_escape(m.group(1), quote=True)}</strong>")
        last = m.end()
    out.append(_escape(text[last:], quote=True))
    return "".join(out)


def format_evidence(quotes: list[dict]) -> str:
    """Format evidence blocks for the tooltip parser in _base.html."""
    if not quotes:
        return ""
    blocks = []
    for q in quotes:
        text = str(q.get("quote", "")).strip()
        source = str(q.get("source", "")).strip()
        if text:
            block = f'"{text}"\n— {source}' if source else f'"{text}"'
            blocks.append(block)
    return "\n\n".join(blocks)


def escape_for_data_attr(text: str) -> str:
    """Escape text for HTML attribute values; raw newlines break attribute parsing."""
    if not text:
        return ""
    return escape(str(text), quote=True).replace("\r", "").replace("\n", "&#10;")


def format_evidence_attr(quotes: list[dict]) -> str:
    """format_evidence + escape_for_data_attr for data-evidence= attributes."""
    return escape_for_data_attr(format_evidence(quotes))


def screenshot_exists(filename: str | None) -> bool:
    if not filename:
        return False
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    candidates = (
        project_dir / "界面截图" / filename,
        project_dir / "assets" / "界面截图" / filename,
    )
    return any(p.is_file() for p in candidates)


def illust_exists(filename: str | None, persona_name: str | None = None) -> bool:
    if filename and resolve_avatar_file(filename):
        return True
    if persona_name and resolve_avatar_file(f"{persona_name}.png"):
        return True
    return False


def render_avatar(path: str | None, name: str, *, alt: str | None = None) -> str:
    """2B identity_panel 头像：用户图 → 默认库 → placeholder。"""
    label = alt or name
    initial = name[0] if name else "?"
    filename = effective_avatar_filename(path, name)
    if filename:
        return (
            f'<img class="persona-avatar" src="assets/画像头像素材/{escape(filename, quote=True)}" '
            f'alt="{escape(label, quote=True)}">'
        )
    return f'<div class="persona-avatar placeholder">{escape(initial)}</div>'


def render_illust(path: str | None, name: str, *, placeholder: str | None = None) -> str:
    """头像/插画：用户图 → 默认库(按画像名.png) → placeholder。"""
    label = placeholder if placeholder is not None else (name[0] if name else "?")
    filename = effective_avatar_filename(path, name)
    if filename:
        return (
            f'<img class="persona-illust" src="assets/画像头像素材/{escape(filename, quote=True)}" '
            f'alt="{escape(name, quote=True)}">'
        )
    return f'<div class="persona-illust-placeholder">{escape(label)}</div>'


def mention_badge(text: str | None) -> str:
    if not text:
        return ""
    return f'<span class="mention-badge">{escape(text)}</span>'


def attach_grid_protocol(fn, estimate_rows_fn, min_cols_fn):
    """挂 grid_solver 协议属性到 renderer 函数。

    grid_solver(scripts/components/layouts/grid_solver.py)在打包 12 列网格时
    会读 renderer 函数的两个属性:
      - fn.estimate_rows(props) -> int   估算占几行(1/2/3)
      - fn.min_cols(props)      -> int   最小占多少列(6/12)

    每个 body 组件 renderer 在模块底部用 attach_grid_protocol 挂上对应实现。
    若 renderer 未挂这两个属性,solver 会 AttributeError —— 这是有意的硬约束。
    """
    fn.estimate_rows = estimate_rows_fn
    fn.min_cols = min_cols_fn
    return fn
