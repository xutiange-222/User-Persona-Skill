"""Scan _components.css for top-level classes and report orphans not produced by any renderer.

Usage:
    python scripts/tests/check_css_orphans.py

Behavior:
    - Reads assets/templates/_components.css
    - Extracts every top-level class selector (e.g. .foo-bar, .layout-2c-portrait)
    - Greps all renderer .py files for the string "foo-bar" (in attributes, f-strings, etc.)
    - Lists classes never referenced by any renderer as "orphan candidates"

Note:
    This is a soft check — it prints findings, does not exit non-zero. Wire it into CI
    if you want it to fail on new orphans. Some legitimate orphan candidates exist
    (e.g. hover/state classes referenced only in CSS), so review output before deleting.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "assets" / "templates" / "_components.css"
RENDERER_DIR = ROOT / "scripts" / "components" / "renderers"
LAYOUTS_DIR = ROOT / "scripts" / "components" / "layouts"

# Classes intentionally produced only by hover/state CSS, or emitted via f-string templates
# the substring check cannot resolve. Add here rather than delete.
ALLOWLIST = {
    # state modifiers (CSS-only)
    "is-active", "is-hover", "is-focused", "is-coop", "is-pain", "is-empty",
    "is-terminal", "is-highlight", "is-ai", "is-l1", "is-l2", "is-reserved",
    "is-reduced", "has-image", "has-screenshot", "has-tooltip-js", "has-inline-metric",
    "dimmed", "empty", "active", "accent", "alt", "single", "full-width", "highlight",
    "placeholder", "soft", "small",
    # dynamically composed via f-string (renderer emits these but substring check misses)
    "mockup-1", "mockup-2", "mockup-3",
    "count-4", "count-5", "count-6",
    "scenarios-grid-1", "scenarios-grid-2", "scenarios-grid-3", "scenarios-grid-4",
    "scenario-card", "scenario-name", "scenario-tools", "scenario-desc", "scenario-image",
    "scenario-image-empty",
    "section-block", "section-block-title", "section-block-summary", "section-block-body",
    "section-blocks-grid",
    "grid-module",
    "l1-action", "l1-step", "l1-decision", "l1-doc", "l1-end", "l1-start", "l1-lane-bg",
    "l1-node", "l1-node-label",
    "ai-mark",
    "matrix-quadrant", "matrix-empty-quadrant",
    # SVG xmlns artifact from regex matching `.org` / `.w3` in CSS string literals
    "org", "w3",
    # legacy/defensive rules intentionally kept (display:none guards, backwards-compat aliases)
    "tob-banner-corner",       # display:none guard
    "matrix-note",              # display:none guard
    "decision-strip",           # used by external snippets per comment
    "pp-insight",               # backwards-compat sibling of .gl-insight
    "journey-pain-opportunity-tag",  # future emoji-tag slot, kept for forward compat
    "tool",                     # bare `.tool` used in scenario placeholder icons
    "meta-row-pair",            # paired meta-row layout option, reserved for identity_panel future
}

# 前缀白名单:assemble.py 用 f'grid-module grid-module-{kebab_type}' 为每个组件动态拼
# class(grid-module-generic-kv / grid-module-titled-list / …),substring 检查看不到,
# 整族按前缀放行,避免每加一个组件都要往 ALLOWLIST 补一条(并消除误报的非确定性)。
ALLOWLIST_PREFIXES = (
    "grid-module-",
)


def extract_top_level_classes(css_text: str) -> set[str]:
    """Match any `.classname` in selectors, including chained (`.foo.bar`) and pseudo-prefixed."""
    # Strip CSS comments first so /* .foo */ doesn't count
    no_comments = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    # Match `.classname` anywhere (chained selectors give multiple hits)
    pattern = re.compile(r"\.([a-zA-Z][\w-]*)")
    return set(pattern.findall(no_comments))


def collect_renderer_source() -> str:
    parts: list[str] = []
    for d in (RENDERER_DIR, LAYOUTS_DIR):
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


def main() -> int:
    if not CSS.exists():
        print(f"ERROR: {CSS} not found", file=sys.stderr)
        return 1
    css_text = CSS.read_text(encoding="utf-8")
    classes = extract_top_level_classes(css_text)
    renderer_src = collect_renderer_source()

    orphans: list[str] = []
    for cls in sorted(classes):
        if cls in ALLOWLIST or any(cls.startswith(p) for p in ALLOWLIST_PREFIXES):
            continue
        # Match class as quoted string, in space-separated class list, or after `class="`.
        # We do NOT match `f-{cls}` / `{cls}-` style — those create false positives because
        # `cls-` could substring-match an unrelated class.
        if (
            f'"{cls}"' in renderer_src
            or f"'{cls}'" in renderer_src
            or f' {cls} ' in renderer_src
            or f' {cls}"' in renderer_src
            or f'"{cls} ' in renderer_src
            or f' {cls}\'' in renderer_src
        ):
            continue
        orphans.append(cls)

    if not orphans:
        print("OK: no orphan CSS classes found.")
        return 0

    print(f"Found {len(orphans)} orphan candidate classes (review before deleting):")
    for cls in orphans:
        print(f"  .{cls}")
    print(
        "\nNote: some may be legitimate (used only as state modifiers in CSS, "
        "or referenced via dynamic template). Add to ALLOWLIST to silence."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
