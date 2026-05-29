#!/usr/bin/env python3
"""从 V8 最终交付件裁切单画像说明书样例。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

V9_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = V9_ROOT / "docs" / "reference" / "reports" / "A-单画像"

BASE_HEAD = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="{theme}" data-density="{density}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="_design-tokens.css">
  <link rel="stylesheet" href="_components.css">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      padding: var(--space-8);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--space-7);
    }}
    .report-meta-bar {{
      width: 100%;
      max-width: var(--canvas-max-w);
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 var(--space-3);
      color: var(--color-text-secondary);
      font-size: var(--text-lg);
    }}
    .report-meta-title {{
      font-size: var(--text-2xl);
      font-weight: var(--font-semibold);
      color: var(--color-text-primary);
    }}
    .report-meta-info {{ font-size: var(--text-lg); color: var(--color-text-secondary); }}
    .persona-nav, .demo-nav-area {{
      width: 100%;
      max-width: var(--canvas-max-w);
      display: flex;
      gap: var(--space-3);
      flex-wrap: wrap;
    }}
    .nav-btn {{
      padding: var(--space-2) var(--space-7);
      font-size: var(--text-lg);
      border: 1px solid var(--color-border-subtle);
      background: var(--color-bg-card);
      color: var(--color-text-primary);
      border-radius: var(--radius-pill);
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
    }}
    .nav-btn:hover {{
      background: var(--color-primary-light);
      border-color: var(--color-accent);
      color: var(--color-accent);
    }}
    .persona-nav .nav-pair, .demo-nav-area .nav-pair, .demo-nav-area .nav-trio {{
      display: inline-flex;
      align-items: stretch;
      gap: 0;
    }}
    .nav-btn-persona {{ border-top-right-radius: 0; border-bottom-right-radius: 0; margin-right: 0; }}
    .nav-btn-journey, .nav-btn-detail {{
      border-left: 0;
      border-top-left-radius: 0;
      border-bottom-left-radius: 0;
      padding-left: var(--space-4);
      padding-right: var(--space-5);
    }}
    .nav-btn.active {{
      background: var(--color-accent);
      color: var(--color-text-inverse);
      border-color: var(--color-accent);
    }}
    .persona-slide {{
      width: 100%;
      max-width: var(--canvas-max-w);
      aspect-ratio: var(--canvas-aspect);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-md);
      background: var(--color-bg-canvas-right);
      overflow: hidden;
      position: relative;
    }}
    .persona-slide:not(.active) {{ display: none; }}
    [data-evidence]:not([data-evidence=""]) {{ cursor: help; }}
    #global-tooltip {{
      position: fixed;
      background: var(--tooltip-bg);
      color: var(--tooltip-text);
      padding: var(--space-5) var(--space-6);
      border-radius: var(--radius-lg);
      font-size: var(--text-base);
      line-height: var(--leading-relaxed);
      max-width: 380px;
      z-index: 9999;
      box-shadow: var(--shadow-tooltip);
      pointer-events: none;
      display: none;
      opacity: 0;
      transition: opacity 0.12s;
    }}
    #global-tooltip.visible {{ display: block; opacity: 1; }}
    #global-tooltip .tip-quote {{
      padding: var(--space-2) 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }}
    #global-tooltip .tip-quote:last-child {{ border-bottom: none; }}
    #global-tooltip .tip-text {{ color: var(--tooltip-text); font-style: italic; }}
    #global-tooltip .tip-source {{ color: var(--tooltip-source); font-size: var(--text-sm); margin-top: var(--space-1); }}
    #global-tooltip::after {{
      content: "";
      position: absolute;
      bottom: -6px;
      left: 50%;
      transform: translateX(-50%);
      border: 6px solid transparent;
      border-top-color: var(--tooltip-bg);
    }}
  </style>
</head>
<body>
  <div id="global-tooltip"></div>
  <div class="report-meta-bar">
    <div class="report-meta-title">{meta_title}</div>
    <div class="report-meta-info">{meta_info}</div>
  </div>
  <div class="demo-nav-area">{nav_html}</div>
  {slides_html}
"""

BASE_TAIL = """
  <script>
    (function() {
      const tooltip = document.getElementById('global-tooltip');
      let hideTimer = null;
      function showTooltip(el) {
        const raw = el.getAttribute('data-evidence');
        if (!raw) return;
        const quotes = raw.split(/\\n\\n/).map(block => {
          const lines = block.split('\\n');
          const text = lines.slice(0, -1).join('\\n').replace(/^"|"$/g, '');
          const source = (lines[lines.length - 1] || '').replace(/^—\\s*/, '');
          return '<div class="tip-quote"><div class="tip-text">"' + text + '"</div><div class="tip-source">— ' + source + '</div></div>';
        }).join('');
        tooltip.innerHTML = quotes;
        const rect = el.getBoundingClientRect();
        tooltip.style.left = Math.min(rect.left, window.innerWidth - 400) + 'px';
        tooltip.style.top = Math.max(rect.top - tooltip.offsetHeight - 12, 8) + 'px';
        tooltip.classList.add('visible');
      }
      function hideTooltip() { tooltip.classList.remove('visible'); }
      document.body.addEventListener('mouseover', function(e) {
        const target = e.target.closest('[data-evidence]');
        if (!target) return;
        clearTimeout(hideTimer);
        showTooltip(target);
      });
      document.body.addEventListener('mouseout', function(e) {
        const target = e.target.closest('[data-evidence]');
        if (!target) return;
        hideTimer = setTimeout(hideTooltip, 50);
      });
      document.body.addEventListener('click', function(e) {
        const trigger = e.target.closest('.nav-btn[data-target]');
        if (!trigger) return;
        const targetId = trigger.getAttribute('data-target');
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        trigger.classList.add('active');
        document.querySelectorAll('.persona-slide').forEach(s => s.classList.remove('active'));
        const slide = document.getElementById(targetId);
        if (slide) slide.classList.add('active');
      });
    })();
  </script>
</body>
</html>
"""


def extract_sections(html: str, slide_ids: list[str]) -> list[str]:
    sections = []
    for sid in slide_ids:
        pattern = rf'(<section class="persona-slide[^"]*" id="{re.escape(sid)}"[^>]*>.*?</section>)'
        m = re.search(pattern, html, re.DOTALL)
        if not m:
            raise ValueError(f"section not found: {sid}")
        sections.append(m.group(1))
    return sections


def mark_active(slides: list[str], active_id: str) -> list[str]:
    out = []
    for s in slides:
        s = re.sub(r'\sclass="persona-slide', ' class="persona-slide', s, count=1)
        s = re.sub(r'class="persona-slide([^"]*)"', r'class="persona-slide\1"', s, count=1)
        sid_m = re.search(r'id="([^"]+)"', s)
        sid = sid_m.group(1) if sid_m else ""
        s = re.sub(r'\sactive', '', s)
        if sid == active_id:
            s = s.replace('class="persona-slide', 'class="persona-slide active', 1)
        out.append(s)
    return out


def build_report(
    *,
    theme: str,
    density: str,
    title: str,
    meta_title: str,
    meta_info: str,
    nav_html: str,
    slides_html: str,
) -> str:
    return BASE_HEAD.format(
        theme=theme,
        density=density,
        title=title,
        meta_title=meta_title,
        meta_info=meta_info,
        nav_html=nav_html,
        slides_html=slides_html,
    ) + BASE_TAIL


def copy_assets(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ("_design-tokens.css", "_components.css"):
        shutil.copy2(src_dir / name, dst_dir / name)


def main() -> None:
    # --- 2B: DevOps 保障型运维工程师 ---
    devops_src = (
        V9_ROOT
        / "docs/reference/reports/B-多角色/2B-DevOps五角色"
    )
    devops_html = (devops_src / "report.html").read_text(encoding="utf-8")
    devops_ids = ["persona-1-core", "persona-1-detail", "persona-1-journey"]
    devops_slides = mark_active(extract_sections(devops_html, devops_ids), "persona-1-core")
    devops_out = OUT_ROOT / "2B-保障型运维工程师"
    copy_assets(devops_src, devops_out)
    nav_2b = (
        '<div class="nav-trio">'
        '<button class="nav-btn nav-btn-persona active" data-target="persona-1-core">保障型运维工程师</button>'
        '<button class="nav-btn nav-btn-detail" data-target="persona-1-detail">› 细节</button>'
        '<button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>'
        '</div>'
    )
    report_2b = build_report(
        theme="2b",
        density="high",
        title="保障型运维工程师 — 2B 单画像样例",
        meta_title="保障型运维工程师（2B · 单画像合并）",
        meta_info="字段 hover 可看原话",
        nav_html=nav_2b,
        slides_html="\n".join(devops_slides),
    )
    (devops_out / "report.html").write_text(report_2b, encoding="utf-8")

    # --- 2C: HiRes 内行场景派 ---
    hires_src = (
        V9_ROOT
        / "docs/reference/reports/D-二维矩阵/2C-HiRes-2维"
    )
    hires_html = (hires_src / "report.html").read_text(encoding="utf-8")
    hires_ids = ["persona-1", "persona-1-detail", "persona-1-journey"]
    hires_slides = mark_active(extract_sections(hires_html, hires_ids), "persona-1")
    hires_out = OUT_ROOT / "2C-内行场景派"
    copy_assets(hires_src, hires_out)
    nav_2c = (
        '<div class="nav-trio">'
        '<button class="nav-btn nav-btn-persona active" data-target="persona-1">内行场景派</button>'
        '<button class="nav-btn nav-btn-detail" data-target="persona-1-detail">› 专题</button>'
        '<button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>'
        '</div>'
    )
    report_2c = build_report(
        theme="2c",
        density="low",
        title="内行场景派 — 2C 单画像样例",
        meta_title="内行场景派（2C · 单画像合并）",
        meta_info="字段 hover 可看原话",
        nav_html=nav_2c,
        slides_html="\n".join(hires_slides),
    )
    (hires_out / "report.html").write_text(report_2c, encoding="utf-8")

    print(f"Wrote {devops_out / 'report.html'}")
    print(f"Wrote {hires_out / 'report.html'}")


if __name__ == "__main__":
    main()
