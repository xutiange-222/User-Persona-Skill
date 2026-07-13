#!/usr/bin/env python3
"""HTML 交付物体检脚本 (user-persona-v8 P7, 2026-05-21).

每次 `render_report.py` 产出 report.html 之后,自动跑这个体检。
任意一项 ERROR 都阻塞交付,WARNING 仅提示。

设计原则:
- 不解析完整 DOM,用 regex 扫"已知会被弄坏"的模式
- 失败必须给出可定位的行号和触发原因
- 不预测未来需求,只防御已经发生过的真实失败

历史:
- P0 2026-05-19:LLM 自创视觉系统(暗色主题、自创类名)
- P1 2026-05-20:多画像旅程页正文整片复用
- P2 2026-05-20:R4 矩阵点位和标签避让缺失
- P5 2026-05-20:画像/旅程未做成组合页签
- P7 2026-05-21:
    1. accent token 名错(--accent-blue 而非 --accent-mist-blue)→ 静默白屏
    2. matrix 点位 hover 气泡丢原话(data-evidence 格式与 JS parser 不匹配)
    3. journey 情绪曲线漏 emoji 子元素
    4. ds-v4-flash 漏写整个 script 块,所有 hover 失效原话堆顶部
    5. 协作字段被自创"上游/核心/下游",不忠实于 schema 的需求来源/交付物/流转去向
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from scripts.components.visual_system import load_visual_system
except ImportError:
    from components.visual_system import load_visual_system

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


# ============================================================
# 白名单 / 黑名单常量
# ============================================================

# 在 _design-tokens.css 真实存在的 accent token
LEGAL_ACCENT_TOKENS = {
    "--accent-purple",
    "--accent-mist-blue",
    "--accent-moss-green",
    "--accent-warm-orange",
    "--accent-mustard",
    "--accent-cyan-gold",
    # 主题语义色,合法
    "--color-accent",
    "--color-primary",
}

# 8 个允许的 layout 类,SKILL.md 约束 7 锁定(P8 新增 layout-2b-grid-detail 双页兜底)
LEGAL_LAYOUTS = {
    "layout-2b-grid",
    "layout-2b-grid-detail",
    "layout-2b-journey",
    "layout-2c-portrait",
    "layout-2c-detail",
    "layout-2c-journey",
    "layout-matrix-2d",
    "layout-distribution-multi",
}

# 协作字段 data-field-key 白名单,与 schema-tob.md collaboration 严格一致
LEGAL_COLLAB_KEYS = {
    "demand_source",
    "deliverables",
    "downstream_flow",
    "kpi",
}

# 已知会被 LLM 自创的协作字段坏名,出现就报错
BANNED_COLLAB_LABELS = {
    "上游",
    "核心",
    "下游",
    "输入",
    "输出",
    "产出",
    "源头",
    "终点",
}

# 任何时候不能出现的内部代号
BANNED_RESPONDENT_PATTERNS = [
    re.compile(r">受访者\d+<"),
    re.compile(r">U\d+_[一-鿿]+<"),  # U1_黄捷 这种带真名的
]


@dataclass
class Issue:
    severity: str  # "ERROR" / "WARNING"
    code: str
    message: str
    line: int = 0
    snippet: str = ""

    def format(self) -> str:
        loc = f"L{self.line}" if self.line else "全文"
        head = f"[{self.severity}] {self.code} @ {loc}"
        body = f"  {self.message}"
        tail = f"  ┃ {self.snippet[:140]}" if self.snippet else ""
        return "\n".join(filter(None, [head, body, tail]))


@dataclass
class Report:
    html_path: Path
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, line: int = 0, snippet: str = "") -> None:
        self.issues.append(Issue(severity, code, message, line, snippet))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    def to_dict(self) -> dict:
        return {
            "html": str(self.html_path),
            "success": not self.errors,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "line": i.line,
                    "snippet": i.snippet[:200],
                }
                for i in self.issues
            ],
        }


# ============================================================
# 辅助:按行号定位 match
# ============================================================

def line_no_of(html: str, pos: int) -> int:
    return html.count("\n", 0, pos) + 1


def snippet_around(html: str, pos: int, width: int = 80) -> str:
    start = max(0, pos - 10)
    end = min(len(html), pos + width)
    return html[start:end].replace("\n", "⏎")


# ============================================================
# 检查项
# ============================================================

def check_skeleton(html: str, rep: Report) -> None:
    """1. 必须 link 骨架 CSS + data-theme + layout 类(SKILL.md 约束 7)"""
    if "_design-tokens.css" not in html:
        rep.add("ERROR", "P0-NO-TOKENS-CSS",
                "缺少 <link rel='stylesheet' href='_design-tokens.css'>,违反骨架硬约束")
    if "_components.css" not in html:
        rep.add("ERROR", "P0-NO-COMPONENTS-CSS",
                "缺少 <link rel='stylesheet' href='_components.css'>,违反骨架硬约束")
    if not re.search(r'<html[^>]*data-theme=', html):
        rep.add("ERROR", "P0-NO-DATA-THEME",
                "<html> 缺少 data-theme 属性")
    if not re.search(r'<html[^>]*data-density=', html):
        rep.add("ERROR", "P0-NO-DATA-DENSITY",
                "<html> 缺少 data-density 属性")

    # 至少一个合法 layout 类
    used_layouts = set(re.findall(r"layout-[a-z0-9-]+", html))
    if not (used_layouts & LEGAL_LAYOUTS):
        rep.add("ERROR", "P0-NO-LEGAL-LAYOUT",
                f"未使用任何合法 layout 类(允许 {sorted(LEGAL_LAYOUTS)},实际出现 {sorted(used_layouts)})")
    illegal = used_layouts - LEGAL_LAYOUTS
    if illegal:
        rep.add("ERROR", "P0-ILLEGAL-LAYOUT",
                f"出现非白名单 layout 类:{sorted(illegal)},必须从 {sorted(LEGAL_LAYOUTS)} 选")


def check_section_boundaries(html: str, rep: Report) -> None:
    """Block leaked tab content caused by malformed section boundaries."""
    bad_patterns = [
        ("</section>/div>", "P0-BROKEN-SECTION-DIV",
         "section close is followed by raw /div>; later slide content may leak into the active tab"),
        ("</section>iv>", "P0-BROKEN-SECTION-IV",
         "section close is followed by raw iv>; later slide content may leak into the active tab"),
    ]
    for needle, code, message in bad_patterns:
        pos = html.find(needle)
        if pos >= 0:
            rep.add("ERROR", code, message, line_no_of(html, pos), snippet_around(html, pos, 120))

    leak = re.search(r"</section>\s*(?:</div>\s*)*<div class=\"meta-row\"", html)
    if leak:
        rep.add("ERROR", "P0-SECTION-META-LEAK",
                "persona meta-row appears directly after a section close; slide wrapper is broken",
                line_no_of(html, leak.start()), snippet_around(html, leak.start(), 140))


def check_accent_tokens(html: str, rep: Report) -> None:
    """2. 所有 var(--accent-XXX) 必须在 token 白名单内
       注意:只校验 --accent-* 系列(LLM 最常写错的);
       --color-primary-* / --color-text-* 等其他 token 在 design-tokens.css 已声明,不校验。
    """
    # 推荐使用的"全名" token,使用别名时给 WARNING 提示
    preferred = {
        "--accent-purple",
        "--accent-mist-blue",
        "--accent-moss-green",
        "--accent-warm-orange",
        "--accent-mustard",
        "--accent-cyan-gold",
    }
    for m in re.finditer(r"var\((--accent-[a-z][a-z0-9-]*)\b", html):
        token = m.group(1)
        if token not in LEGAL_ACCENT_TOKENS:
            rep.add("ERROR", "P7-UNKNOWN-ACCENT-TOKEN",
                    f"引用了未定义的 token:var({token}),会静默坏掉",
                    line_no_of(html, m.start()),
                    snippet_around(html, m.start()))
        elif token not in preferred:
            rep.add("WARNING", "P7-ACCENT-ALIAS-USED",
                    f"用了别名 var({token}),CSS 已 alias 到正确色但建议改成全名(如 --accent-mist-blue)",
                    line_no_of(html, m.start()))


def check_tooltip_script(html: str, rep: Report) -> None:
    """3. tooltip JS 必须存在并标记 has-tooltip-js(P7 真实失败)"""
    has_script = re.search(r"<script[^>]*>", html, re.IGNORECASE)
    has_marker = "has-tooltip-js" in html
    has_global_tooltip_div = 'id="global-tooltip"' in html or "id='global-tooltip'" in html

    # data-evidence 有但 script 缺
    has_evidence = "data-evidence=" in html
    if has_evidence and not has_script:
        rep.add("ERROR", "P7-MISSING-SCRIPT",
                "页面有 data-evidence 但没有任何 <script>,hover 气泡会全部失效")
    if has_evidence and has_script and not has_marker:
        rep.add("ERROR", "P7-MISSING-TOOLTIP-MARKER",
                "<script> 存在但未执行 document.body.classList.add('has-tooltip-js'),"
                "会导致 CSS 兜底 tooltip 和 JS tooltip 同时出现")
    if has_evidence and not has_global_tooltip_div:
        rep.add("WARNING", "P7-NO-GLOBAL-TOOLTIP-DIV",
                "没有 <div id='global-tooltip'>,只能依赖 CSS-only 兜底(美观度下降)")


def check_data_evidence_format(html: str, rep: Report) -> None:
    """4. 每个 data-evidence 必须含引号包裹的原话(不能只是姓名)"""
    pattern = re.compile(r'data-evidence=(["\'])(.*?)\1', re.DOTALL)
    for m in pattern.finditer(html):
        value = m.group(2)
        if not value.strip():
            rep.add("WARNING", "P7-EMPTY-EVIDENCE",
                    "data-evidence 为空字符串", line_no_of(html, m.start()))
            continue
        # 必须含 HTML-encoded 引号或裸引号或中文引号
        has_quote = (
            "&quot;" in value
            or '"' in value
            or '“' in value  # "
            or '”' in value  # "
        )
        if not has_quote:
            rep.add("ERROR", "P7-EVIDENCE-NO-QUOTE",
                    f"data-evidence 不含任何引号包裹的原话(只是姓名/标签?):{value[:80]}",
                    line_no_of(html, m.start()),
                    snippet_around(html, m.start()))


def check_matrix(html: str, rep: Report) -> None:
    """5. 矩阵点位结构(P5 2026-05-20 真实失败再加固)"""
    if "matrix-respondent-dot" not in html:
        return  # 没矩阵,跳过

    wrappers = list(re.finditer(r'<div class="matrix-respondent"[^>]*>', html))
    dots = list(re.finditer(r'<[^>]+class="[^"]*matrix-respondent-dot[^"]*"[^>]*>', html))
    labels = list(re.finditer(r'<[^>]+class="[^"]*respondent-label[^"]*"[^>]*>', html))

    if len(dots) != len(labels):
        rep.add("ERROR", "P5-DOT-LABEL-MISMATCH",
                f"matrix-respondent-dot 数量({len(dots)})≠ respondent-label 数量({len(labels)})")

    if wrappers:
        if len(wrappers) != len(dots):
            rep.add("ERROR", "P5-WRAPPER-DOT-MISMATCH",
                    f"matrix-respondent 数量({len(wrappers)})≠ dot 数量({len(dots)})")
        for m in wrappers:
            tag = m.group(0)
            if "matrix-respondent-dot" in tag:
                continue
            if not re.search(r'style="left:[0-9.]+%;top:[0-9.]+%', tag):
                rep.add("ERROR", "P5-WRAPPER-NO-POSITION",
                        f"matrix-respondent 缺 left%/top% 定位:{tag[:120]}",
                        line_no_of(html, m.start()))
    else:
        # 旧版分离 DOM:每个 label 必须带方向类
        direction_classes = {"label-right", "label-left", "label-top", "label-bottom",
                             "label-top-right", "label-bottom-right",
                             "label-top-left", "label-bottom-left"}
        for m in labels:
            tag = m.group(0)
            classes = re.search(r'class="([^"]*)"', tag).group(1).split()
            if not (set(classes) & direction_classes):
                rep.add("ERROR", "P5-LABEL-NO-DIRECTION",
                        f"respondent-label 缺方向类(必须从 {sorted(direction_classes)} 选一):{tag[:120]}",
                        line_no_of(html, m.start()))

    # 受访者代号不可见
    for pat in BANNED_RESPONDENT_PATTERNS:
        for m in pat.finditer(html):
            rep.add("ERROR", "P5-RAW-RESPONDENT-CODE",
                    f"展示层出现受访者内部代号:{m.group(0)}",
                    line_no_of(html, m.start()))

    # 矩阵象限标签必须是 button
    quadrant_labels = re.findall(r'<(\w+)[^>]+class="[^"]*matrix-quadrant-label[^"]*"', html)
    for tag in quadrant_labels:
        if tag != "button":
            rep.add("ERROR", "P5-QUADRANT-NOT-BUTTON",
                    f".matrix-quadrant-label 标签是 <{tag}>,必须是 <button>(否则无法点击切画像)")


def check_nav_pair(html: str, rep: Report) -> None:
    """6. 画像 + 旅程必须成组(P5 2026-05-20)"""
    journey_ids = re.findall(r'id="(persona-\d+-journey)"', html)
    for jid in journey_ids:
        # 必须存在带 data-target=jid 的 .nav-btn-journey
        if f'data-target="{jid}"' not in html:
            rep.add("ERROR", "P5-NO-NAV-FOR-JOURNEY",
                    f"存在 {jid} 但 nav 里没有对应 data-target='{jid}' 的按钮")
        # 只检查与当前 L2 journey id 绑定的按钮，不能误把前面的 L1“总体旅程”当成 L2 文案。
        button = re.search(
            rf'<button\b(?=[^>]*\bdata-target="{re.escape(jid)}")'
            rf'(?=[^>]*\bclass="[^"]*\bnav-btn-journey\b[^"]*")[^>]*>(.*?)</button>',
            html,
            re.DOTALL,
        )
        label = re.sub(r"<[^>]+>", "", button.group(1)).strip() if button else ""
        if label and "›" not in label:
            rep.add("WARNING", "P5-OLD-JOURNEY-NAV-TEXT",
                    f"旅程按钮文案是 '{label}',应改为 '› 旅程'")


def check_journey_emotion(html: str, rep: Report) -> None:
    """7. 旅程情绪曲线节点结构(P7 emoji 兜底已经在 CSS,这里只 WARNING)"""
    points = re.findall(r'<[^>]+class="[^"]*journey-emotion-point[^"]*"', html)
    emotion_labels = re.findall(r'<[^>]+class="[^"]*emotion-label[^"]*"', html)
    if points and not emotion_labels:
        rep.add("ERROR", "P7-NO-EMOTION-LABEL",
                f"有 {len(points)} 个 journey-emotion-point 但没有 emotion-label,情绪标签全丢")
    # emoji span 缺失只是 WARNING,CSS 兜底会补
    if emotion_labels:
        no_emoji_count = 0
        for m in re.finditer(r'<span class="emotion-label[^"]*">(.*?)</span>', html, re.DOTALL):
            if 'class="emoji"' not in m.group(1):
                no_emoji_count += 1
        if no_emoji_count:
            rep.add("WARNING", "P7-NO-EMOJI-SPAN",
                    f"{no_emoji_count} 个 emotion-label 缺 .emoji 子元素(CSS 兜底会补默认图,建议补真实 emoji)")


def _find_balanced_div(html: str, start_pos: int) -> int:
    """从 <div ...> 起始位置开始,返回与之匹配的 </div> 的结尾位置(包含)。
    用栈匹配嵌套的 <div>/</div>,忽略 attr 里出现的字符串。
    找不到返回 -1。"""
    tag_re = re.compile(r"<(/?)div\b[^>]*>", re.IGNORECASE)
    depth = 0
    pos = start_pos
    while True:
        m = tag_re.search(html, pos)
        if not m:
            return -1
        if m.group(1) == "":  # 开标签
            depth += 1
        else:  # 闭标签
            depth -= 1
            if depth == 0:
                return m.end()
        pos = m.end()


def check_section_block(html: str, rep: Report) -> None:
    """8. toC section-block 必须有 title + summary + body 三层。
       注意:section-block 内部还有 3 个嵌套 div,必须用栈匹配,不能用懒惰 regex。"""
    # 只匹配 section-block 这个根类,不匹配子类(section-block-title 等)
    for m in re.finditer(r'<div\s+class="section-block(?:\s[^"]*)?"[^>]*>', html):
        end = _find_balanced_div(html, m.start())
        if end < 0:
            rep.add("WARNING", "P4-SECTION-UNCLOSED",
                    "section-block 似乎没有匹配的 </div>", line_no_of(html, m.start()))
            continue
        inner = html[m.end():end]
        line = line_no_of(html, m.start())
        if "section-block-title" not in inner:
            rep.add("ERROR", "P4-SECTION-NO-TITLE",
                    "section-block 缺 .section-block-title", line)
        if "section-block-summary" not in inner:
            rep.add("ERROR", "P4-SECTION-NO-SUMMARY",
                    "section-block 缺 .section-block-summary(2C 必须三层结构)", line)
        if "section-block-body" not in inner:
            rep.add("ERROR", "P4-SECTION-NO-BODY",
                    "section-block 缺 .section-block-body", line)


def check_collab_fields(html: str, rep: Report) -> None:
    """9. 协作字段名锁定(P7 真实失败:被 ds-v4-flash 自创'上游/核心/下游')"""
    # 黑名单文案直接 hit
    for label in BANNED_COLLAB_LABELS:
        pattern = re.compile(rf'class="flow-cell-label"[^>]*>\s*{label}\s*<')
        for m in pattern.finditer(html):
            rep.add("ERROR", "P7-BANNED-COLLAB-LABEL",
                    f"协作字段使用了禁用名 '{label}',必须用 schema 锁定的 需求来源/交付物/流转去向/KPI",
                    line_no_of(html, m.start()),
                    snippet_around(html, m.start()))

    # 所有 flow-cell 必须有 data-field-key
    # 关键:负向预查防止误匹配 flow-cell-label / flow-cell-value 这些子元素
    flow_cells = list(re.finditer(r'<div\s+class="flow-cell(?!-)[^"]*"([^>]*)>', html))
    for m in flow_cells:
        attrs = m.group(1)
        key_match = re.search(r'data-field-key="([^"]+)"', attrs)
        if not key_match:
            rep.add("ERROR", "P7-FLOW-CELL-NO-KEY",
                    f"flow-cell 没有 data-field-key,LLM 自创 label 无法被 CSS 兜底矫正",
                    line_no_of(html, m.start()),
                    snippet_around(html, m.start()))
        elif key_match.group(1) not in LEGAL_COLLAB_KEYS:
            rep.add("ERROR", "P7-INVALID-COLLAB-KEY",
                    f"flow-cell data-field-key='{key_match.group(1)}' 不在白名单 {sorted(LEGAL_COLLAB_KEYS)}",
                    line_no_of(html, m.start()))


def check_chinese_punctuation(html: str, rep: Report) -> None:
    """10. 中文标点清洗(约束 9)。只扫展示文本,不动 attribute/script。"""
    # 提取 <p> / <div class="section-block-body"> 等正文文本
    text_blocks = re.findall(r'>([^<>]{4,200})<', html)
    bad_patterns = [
        (re.compile(r'[一-鿿],[一-鿿]'), "P9-EN-COMMA-IN-CN", "中文之间出现英文逗号 , 应改为中文 ,"),
        (re.compile(r'[一-鿿]\?'), "P9-EN-QUESTION-IN-CN", "中文后接英文 ? 应改为中文 ?"),
        (re.compile(r'[一-鿿];[一-鿿]'), "P9-EN-SEMICOLON-IN-CN", "中文之间出现英文分号 ; 应改为中文 ;"),
    ]
    seen = set()
    for txt in text_blocks:
        for pat, code, msg in bad_patterns:
            m = pat.search(txt)
            if m:
                key = (code, txt[max(0, m.start() - 5):m.end() + 5])
                if key in seen:
                    continue
                seen.add(key)
                rep.add("WARNING", code, f"{msg}:'{key[1]}'")


def check_journey_emotion_copy(html: str, rep: Report) -> None:
    """11. 多画像旅程页正文不能整片复用(P1 2026-05-20 真实失败)"""
    journeys = re.findall(r'<section[^>]*id="(persona-\d+-journey)"[^>]*>(.*?)</section>',
                          html, re.DOTALL)
    if len(journeys) < 2:
        return
    # 提取每个旅程的所有 journey-cell-summary 文本
    summaries = {}
    for jid, content in journeys:
        cells = re.findall(r'<span class="journey-cell-summary">([^<]+)</span>', content)
        summaries[jid] = "|".join(cells)

    ids = list(summaries.keys())
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if summaries[a] and summaries[a] == summaries[b]:
                rep.add("ERROR", "P1-JOURNEY-DUPLICATE",
                        f"旅程页 {a} 和 {b} 的 journey-cell-summary 整列完全一致,违反每画像独立分析硬约束")
            elif summaries[a] and similarity(summaries[a], summaries[b]) > 0.7:
                rep.add("WARNING", "P1-JOURNEY-HIGH-SIMILARITY",
                        f"旅程页 {a} 和 {b} 正文相似度 > 70%,需要差异化")


def similarity(a: str, b: str) -> float:
    """简易相似度:共同 unigram 数 / 最大 unigram 数。够用做差异检测。"""
    if not a or not b:
        return 0.0
    s1 = set(a)
    s2 = set(b)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / max(len(s1), len(s2))


def check_tab_count(html: str, rep: Report) -> None:
    """12. nav 组数 ≤ 12(visual-system.md 上限)。

    trio/pair 内多个 nav-btn 只占一个 tab 槽位,按 .demo-nav-area 顶层子元素计数。
    """
    nav_area = re.search(r'<div class="demo-nav-area">(.*?)</div>\s*(?:<div class="report-meta-bar"|</div>)', html, re.S)
    if not nav_area:
        return
    inner = nav_area.group(1)
    # 顶层: single 按钮 | nav-pair | nav-trio
    groups = re.findall(
        r'(?:<button class="nav-btn single"|<div class="nav-(?:pair|trio)")',
        inner,
    )
    if len(groups) > 12:
        rep.add("ERROR", "P4-TAB-OVER-12",
                f"nav 组数 {len(groups)} 超过 12 上限,会撑破单行")


def check_avatar_usage(html: str, rep: Report, project_dir: Path | None) -> None:
    """13. 头像素材目录有图但 HTML 没引用 → WARNING(避免占位符替代真头像)"""
    if not project_dir or not project_dir.exists():
        return
    avatar_dir = project_dir / "画像头像素材"
    if not avatar_dir.exists():
        return
    images = [p for p in avatar_dir.iterdir()
              if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}]
    if not images:
        return
    used = sum(1 for p in images if p.name in html or p.stem in html)
    if used == 0:
        names = ", ".join(p.name for p in images[:5])
        rep.add("WARNING", "P7-UNUSED-AVATARS",
                f"画像头像素材/ 下有 {len(images)} 张图但 HTML 都没引用({names}...);"
                "可能是模型用了文字占位 .persona-illust-placeholder 而未询问/复制头像")


def check_persona_subtitle_repeat(html: str, rep: Report) -> None:
    """14. 多画像的 subtitle 整段重复 → 偷懒信号(P7 用户反馈"右侧描述明显偷懒")"""
    subtitles = re.findall(r'<div class="persona-subtitle">([^<]+)</div>', html)
    if len(subtitles) >= 2 and len(set(subtitles)) == 1:
        rep.add("WARNING", "P7-SUBTITLE-DUPLICATE",
                f"{len(subtitles)} 个画像 subtitle 完全相同:'{subtitles[0]}',疑似偷懒")


def check_evidence_duplication(html: str, rep: Report) -> None:
    """15. 同 slide 内 data-evidence 大面积复用 → 偷懒信号(2026-05-28 真实失败:
    DevOps 报告 hover 上 7/10 处显示同一句"我买了机器…手工去录",
    根因是 build_report.py 复用 quotes[0],未按组件绑定证据)。

    规则:同 .persona-slide 内,同一 data-evidence 文本完全相同出现:
    - ≥ 3 次 → ERROR(违反约束 5"证据全量")
    - 2 次   → WARNING(可能合理,如同一句话支撑两个观点,但提示模型核对)
    """
    # 按 slide 切片
    slide_pattern = re.compile(
        r'<section[^>]*class="[^"]*persona-slide[^"]*"[^>]*>(.*?)</section>',
        re.DOTALL,
    )
    for slide_match in slide_pattern.finditer(html):
        slide_html = slide_match.group(1)
        slide_id_m = re.search(r'id="([^"]+)"', slide_match.group(0))
        slide_id = slide_id_m.group(1) if slide_id_m else "?"
        evidences = re.findall(r'data-evidence="([^"]+)"', slide_html)
        if not evidences:
            continue
        counts: dict[str, int] = {}
        for ev in evidences:
            # 取前 40 字符作 fingerprint(避免长字符串差异)
            fp = ev[:40]
            counts[fp] = counts.get(fp, 0) + 1
        for fp, cnt in counts.items():
            if cnt >= 3:
                rep.add("ERROR", "P9-DUPLICATE-EVIDENCE",
                        f"slide '{slide_id}' 内同一 data-evidence 重复 {cnt} 次(前 40 字:'{fp}'),"
                        f"违反约束 5(证据全量且分组件绑定),"
                        f"应让每个 ring/scene/painpoint 用自己的支撑原话",
                        line_no_of(html, slide_match.start()))
            elif cnt == 2:
                rep.add("WARNING", "P9-EVIDENCE-REUSED",
                        f"slide '{slide_id}' 内同一 data-evidence 出现 2 次(前 40 字:'{fp}'),"
                        f"如系同一原话同时支撑两个观点可保留,否则请补不同证据",
                        line_no_of(html, slide_match.start()))


def check_2b_l1_role_rail(html: str, rep: Report) -> None:
    """Guard against overlapping 2B L1 role names and role tags."""
    l1_match = re.search(
        r'<section[^>]*id="journey-l1"[^>]*>(?P<body>.*?)</section>',
        html,
        re.S,
    )
    if not l1_match:
        return
    body = l1_match.group("body")
    if '<svg class="l1-uml-svg"' not in body:
        return
    old_role_coord = re.search(
        r'<text class="l1-role-text" x="36" y="\d+">.*?</text>\s*'
        r'<text class="l1-role-tag" x="60" y="\d+">',
        body,
        re.S,
    )
    if old_role_coord:
        rep.add(
            "ERROR",
            "P10-2B-L1-ROLE-RAIL-OVERLAP",
            "2B L1 左侧角色栏仍使用旧坐标 x=36/x=60,角色名和动作标签会重叠。"
            "请用渲染器的 _render_lane_role 固定盒内排版重新生成。",
            line_no_of(html, l1_match.start() + old_role_coord.start()),
        )
    role_texts = re.findall(r'<text class="l1-role-text"[^>]*>(.*?)</text>', body, re.S)
    for raw in role_texts:
        text = re.sub(r'<[^>]+>', '', raw).strip()
        if len(text) > 4 and "<tspan" not in raw:
            rep.add(
                "ERROR",
                "P10-2B-L1-ROLE-NO-WRAP",
                f"2B L1 左侧角色名 '{text}' 超过 4 字但没有 tspan 换行,会挤压或截断。",
                line_no_of(html, l1_match.start()),
            )


def check_2b_l1_stage_grid(html: str, rep: Report) -> None:
    """Guard against stage/substage rows drifting away from the SVG lane grid."""
    l1_match = re.search(
        r'<section[^>]*id="journey-l1"[^>]*>(?P<body>.*?)</section>',
        html,
        re.S,
    )
    if not l1_match:
        return
    body = l1_match.group("body")
    if '<div class="l1-stage-board">' not in body or '<svg class="l1-uml-svg"' not in body:
        return

    journey_contract = load_visual_system()["themes"]["2b"]["journey"]
    stage_count = len(re.findall(r'class="l1-stage-cell"', body))
    if stage_count < 1:
        return
    rail_width = float(journey_contract["role_rail_width"])
    view_box_width = float(journey_contract["view_box_width"])
    stage_width = (view_box_width - rail_width) / stage_count
    expected_values = [rail_width / view_box_width * 100]
    expected_values.extend(stage_width / view_box_width * 100 for _ in range(stage_count))
    expected_grid = " ".join(f"{value:.6f}%" for value in expected_values)
    compact_expected = _compact_css(expected_grid)
    css = _load_visual_css(rep)
    compact_body = _compact_css(body)
    compact_css = _compact_css(css)

    bad_inline_patterns = [
        "grid-template-columns:87fr219fr218fr219fr218fr219fr",
        "grid-template-columns:87pxrepeat(",
        "grid-template-columns:92pxrepeat(",
        "grid-template-columns:92pxrepeat(5,1fr)",
    ]
    bad_css_patterns = [
        ".persona-slide.layout-2b-journey.is-l1.l1-row{grid-template-columns:87fr",
        ".persona-slide.layout-2b-journey.is-l1.l1-row{grid-template-columns:92px",
    ]
    if any(pattern in compact_body for pattern in bad_inline_patterns) or any(pattern in compact_css for pattern in bad_css_patterns):
        rep.add(
            "ERROR",
            "P10-2B-L1-STAGE-GRID-MISMATCH",
            "2B L1 阶段/子阶段表头仍使用旧列定义,会和下方 SVG 虚线泳道漂移。"
            f"必须使用 viewBox 派生列: {expected_grid}",
            line_no_of(html, l1_match.start()),
        )

    if compact_expected not in compact_body and compact_expected not in compact_css:
        rep.add(
            "ERROR",
            "P10-2B-L1-STAGE-GRID-MISMATCH",
            f"2B L1 未找到同源列定义: {expected_grid}。"
            "阶段、子阶段、SVG 泳道必须共用这套比例。",
            line_no_of(html, l1_match.start()),
        )

    stage_bg_ok = ".persona-slide.layout-2b-journey.is-l1.l1-row.stage-row{background:#96befa!important" in compact_css
    substage_bg_ok = ".persona-slide.layout-2b-journey.is-l1.l1-row.substage-row{background:#dcf0fa!important" in compact_css
    if not stage_bg_ok or not substage_bg_ok:
        rep.add(
            "ERROR",
            "P10-2B-L1-STAGE-GRID-MISMATCH",
            "2B L1 阶段行和子阶段行必须用同色背景承接箭头裁切,"
            "避免露出白色条或白色三角。",
            line_no_of(html, l1_match.start()),
        )


# ============================================================
# 入口
# ============================================================

def _load_visual_css(rep: Report) -> str:
    chunks: list[str] = []
    for name in ("_design-tokens.css", "_components.css"):
        path = rep.html_path.parent / name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _compact_css(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _css_has_decl(css: str, selector: str, prop: str, value: str) -> bool:
    pattern = re.compile(re.escape(selector) + r"\s*\{(?P<body>.*?)\}", re.S)
    wanted = _compact_css(f"{prop}:{value}")
    return any(wanted in _compact_css(m.group("body")) for m in pattern.finditer(css))


def _parse_inline_style(style: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for chunk in style.split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _check_2c_palette_packs(html: str, rep: Report) -> None:
    system = load_visual_system()
    packs = system["themes"]["2c"]["palette_packs"]
    matches = re.findall(
        r'<section\b(?=[^>]*class="[^"]*\blayout-2c-(?:portrait|detail|journey)\b[^"]*")'
        r'(?=[^>]*\bid="([^"]+)")(?=[^>]*\bstyle="([^"]*)")[^>]*>',
        html,
    )
    styled_ids = {section_id for section_id, _style in matches}
    all_ids = set(re.findall(
        r'<section\b(?=[^>]*class="[^"]*\blayout-2c-(?:portrait|detail|journey)\b[^"]*")'
        r'(?=[^>]*\bid="([^"]+)")[^>]*>',
        html,
    ))
    for section_id in sorted(all_ids - styled_ids):
        rep.add(
            "ERROR",
            "VSTYLE-2C-PALETTE-PACK-MISSING",
            f"2C section '{section_id}' must include the complete renderer-generated palette pack",
        )

    persona_styles: dict[str, set[str]] = {}
    for section_id, style_text in matches:
        declarations = _parse_inline_style(style_text)
        style_name = declarations.get("--color-toc-style", "")
        pack = packs.get(style_name)
        if not pack:
            rep.add(
                "ERROR",
                "VSTYLE-2C-PALETTE-STYLE-UNKNOWN",
                f"2C section '{section_id}' uses an unknown palette style: {style_name or '(missing)'}",
            )
            continue
        expected = pack["values"]
        for token, expected_value in expected.items():
            actual = declarations.get(token)
            if _compact_css(actual or "") != _compact_css(expected_value):
                rep.add(
                    "ERROR",
                    "VSTYLE-2C-PALETTE-VALUE-MISMATCH",
                    f"2C section '{section_id}' must set {token} to {expected_value}; got {actual!r}",
                )
        if declarations.get("--color-toc-aux-bg") == declarations.get("--color-toc-primary"):
            rep.add(
                "ERROR",
                "VSTYLE-2C-TOUCHPOINT-PRIMARY-COLOR",
                f"2C section '{section_id}' maps the auxiliary tag background to the primary color",
            )
        persona_id = re.sub(r"-(?:detail(?:-\d+)?|journey|core)$", "", section_id)
        persona_styles.setdefault(persona_id, set()).add(style_name)

    for persona_id, styles in persona_styles.items():
        if len(styles) > 1:
            rep.add(
                "ERROR",
                "VSTYLE-2C-PALETTE-STYLE-MISMATCH",
                f"2C persona '{persona_id}' uses multiple palette packs: {', '.join(sorted(styles))}",
            )


def _check_2c_font_floor(css: str, html: str, rep: Report) -> None:
    class_prefixes: list[str] = []
    if "layout-2c-journey" in html:
        class_prefixes.extend([".journey-", ".emotion-label"])
    if "layout-distribution-multi" in html:
        class_prefixes.extend([".distribution-", ".snake-"])
    if not class_prefixes:
        return

    for block in re.finditer(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", css, re.S):
        selector = block.group("selector").strip()
        if not any(prefix in selector for prefix in class_prefixes):
            continue
        for match in re.finditer(r"font-size\s*:\s*([^;]+)", block.group("body"), re.I):
            value = match.group(1).strip()
            pixels = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)px(?:\s*!important)?", value, re.I)
            too_small = bool(pixels and float(pixels.group(1)) < 12)
            unguarded_small_token = _compact_css(value) in {
                "var(--text-xs)",
                "var(--text-sm)",
            }
            if too_small or unguarded_small_token:
                rep.add(
                    "ERROR",
                    "VSTYLE-2C-FONT-BELOW-MIN",
                    f"2C journey/distribution text must be at least 12px: {selector} uses {value}",
                )

    for match in re.finditer(r"style=\"[^\"]*font-size\s*:\s*([0-9.]+)px", html, re.I):
        if float(match.group(1)) < 12:
            rep.add(
                "ERROR",
                "VSTYLE-2C-FONT-BELOW-MIN",
                f"2C inline text size is below 12px: {match.group(1)}px",
                line_no_of(html, match.start()),
            )


def _check_workflow_visual_spec(rep: Report, project_dir: Path | None) -> None:
    if project_dir is None:
        return
    project_dir = Path(project_dir)
    process_dir = project_dir if project_dir.name == "过程稿" else project_dir / "过程稿"
    if not process_dir.is_dir():
        return
    alignment_path = process_dir / "03-field-alignment.json"
    report_path = process_dir / "05-report.json"
    if not alignment_path.is_file() or not report_path.is_file():
        rep.add(
            "ERROR",
            "VSTYLE-VISUAL-SPEC-MISSING",
            "workflow HTML validation requires both 03-field-alignment.json and 05-report.json",
        )
        return
    try:
        alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
        report_json = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        rep.add("ERROR", "VSTYLE-VISUAL-SPEC-MISSING", f"cannot read workflow visual_spec: {exc}")
        return
    alignment_spec = alignment.get("visual_spec")
    report_spec = (report_json.get("metadata") or {}).get("visual_spec")
    if not isinstance(alignment_spec, dict) or not isinstance(report_spec, dict):
        rep.add(
            "ERROR",
            "VSTYLE-VISUAL-SPEC-MISSING",
            "03-field-alignment.json and 05-report.json must both contain visual_spec",
        )
        return
    for key in ("template_id", "palette_id", "persona_palette_map"):
        if key in alignment_spec and alignment_spec.get(key) != report_spec.get(key):
            rep.add(
                "ERROR",
                "VSTYLE-VISUAL-SPEC-MISMATCH",
                f"workflow visual_spec.{key} differs between 03 and 05",
            )


def check_visual_style_contract(html: str, rep: Report) -> None:
    """Protect the visual rules in steps/visual-style-guide.md."""
    system = load_visual_system()
    css = _load_visual_css(rep)
    if "_components.css" in html and "_design-tokens.css" in html and not css:
        rep.add("ERROR", "VSTYLE-NO-LOCAL-CSS",
                "report.html links CSS but local _design-tokens.css/_components.css are missing next to the report")
        return

    compact = _compact_css(css)

    if "layout-2b-grid-detail" in html:
        detail_css = [
            (".persona-slide.layout-2b-grid-detail.active", "display", "grid"),
            (".persona-slide.layout-2b-grid-detail.active", "grid-template-rows", "auto minmax(0,1fr)"),
            (".persona-slide.layout-2b-grid-detail .modules-panel", "grid-auto-rows", "auto"),
            (".persona-slide.layout-2b-grid-detail .modules-panel", "align-content", "center"),
            (".persona-slide.layout-2b-grid-detail .modules-panel > .grid-module", "background", "#fbfcfe"),
            (".persona-slide.layout-2b-grid-detail .generic-list-item:not(:last-child)::after", "content", "none"),
        ]
        for selector, prop, value in detail_css:
            if not _css_has_decl(css, selector, prop, value):
                rep.add("ERROR", "VSTYLE-2B-DETAIL-BALANCE", f"2B detail layout contract failed: {selector} must include {prop}: {value}")

    if 'data-theme="2c"' in html and 'data-density="low"' not in html:
        rep.add("ERROR", "VSTYLE-2C-DENSITY",
                '2C reports must use data-density="low"')

    if 'data-theme="2c"' in html:
        required_2c_tokens = {
            **system["themes"]["2c"]["tokens"],
            "--palette-2c-purple-primary": "#9664ff",
            "--palette-2c-purple-aux": "#fff0be",
            "--palette-2c-red-orange-primary": "#f05a28",
            "--palette-2c-green-gray-primary": "#82b4b4",
            "--palette-2c-yellow-orange-primary": "#ffb41e",
            "--palette-2c-blue-yellow-primary": "#5a8cfa",
            "--palette-2c-cyan-gold-primary": "#285a82",
        }
        for token, value in required_2c_tokens.items():
            if _compact_css(f"{token}:{value}") not in compact:
                rep.add("ERROR", "VSTYLE-2C-TOKEN-MISSING",
                        f"2C palette token missing or wrong: {token} must be {value.upper()}")

        required_2c_semantic_tokens = {
            "--color-toc-primary": "var(--color-accent)",
            "--color-toc-secondary": "color-mix(in srgb, var(--color-toc-primary) 36%, #FFFFFF)",
            "--color-toc-surface": "color-mix(in srgb, var(--color-toc-primary) 10%, #FFFFFF)",
            "--color-toc-bg": "var(--color-toc-surface)",
            "--color-toc-soft": "color-mix(in srgb, var(--color-toc-primary) 14%, #FFFFFF)",
            "--color-toc-tint": "color-mix(in srgb, var(--color-toc-primary) 8%, #FFFFFF)",
            "--color-toc-alert": "var(--color-warning)",
            "--color-toc-aux": "var(--color-toc-secondary)",
            "--color-toc-aux-bg": "var(--color-toc-aux)",
            "--color-toc-aux-text": "var(--color-text-primary)",
            "--color-toc-focus": "var(--color-toc-primary)",
            "--color-toc-focus-soft": "var(--color-toc-soft)",
            "--color-toc-focus-tint": "var(--color-toc-tint)",
            "--color-toc-icon": "var(--color-toc-primary)",
            "--color-toc-icon-bg": "var(--color-toc-soft)",
            "--color-toc-on-focus": "#FFFFFF",
        }
        for token, value in required_2c_semantic_tokens.items():
            if _compact_css(f"{token}:{value}") not in compact:
                rep.add("ERROR", "VSTYLE-2C-SEMANTIC-TOKEN-MISSING",
                        f"2C semantic color token missing or wrong: {token} must be {value}")

        _check_2c_palette_packs(html, rep)
        _check_2c_font_floor(css, html, rep)

        if "layout-2c-portrait" in html:
            portrait_css = [
                (".identity-card", "background", "var(--color-toc-surface, var(--color-bg-illust))"),
                (".section-block", "border-left", "3px solid var(--color-toc-primary, var(--color-accent))"),
                (".section-block-title", "color", "var(--color-text-primary)"),
                (".section-block-title", "background", "var(--color-toc-soft, var(--color-accent-soft))"),
                (".section-block-body strong", "color", "var(--color-toc-primary, var(--color-accent))"),
                (".persona-quote-pull", "background", "var(--color-toc-surface, var(--color-bg-quote-pull))"),
                (".persona-quote-pull", "border-left", "4px solid var(--color-toc-primary, var(--color-accent))"),
                (".persona-quote-pull::before", "color", "var(--color-toc-primary, var(--color-accent))"),
            ]
            for selector, prop, value in portrait_css:
                if not _css_has_decl(css, selector, prop, value):
                    rep.add("ERROR", "VSTYLE-2C-PORTRAIT-COLOR",
                            f"2C portrait cards must use TO C semantic color tokens: {selector} must include {prop}: {value}")
            nav_required = [
                ".nav-btn.active",
                "--nav-color",
                "syncNavPalette",
                "--color-toc-primary",
                "--color-toc-soft",
            ]
            missing_nav_bits = [bit for bit in nav_required if bit not in html]
            if missing_nav_bits:
                rep.add("ERROR", "VSTYLE-2C-NAV-PALETTE-SYNC",
                        "2C multi-persona nav must sync active tab colors from the target persona palette: "
                        + ", ".join(missing_nav_bits))
            section_styles = re.findall(r'<section\b[^>]*class="[^"]*\blayout-2c-(?:portrait|detail|journey)\b[^"]*"[^>]*style="([^"]*)"', html)
            for style in section_styles:
                required_palette_vars = [
                    "--color-toc-style:",
                    "--color-toc-primary:",
                    "--color-toc-secondary:",
                    "--color-toc-surface:",
                    "--color-toc-bg:",
                    "--color-toc-soft:",
                    "--color-toc-alert:",
                    "--color-toc-aux:",
                    "--color-toc-aux-bg:",
                    "--color-toc-aux-text:",
                ]
                if "--color-accent:" in style:
                    missing_palette_vars = [v for v in required_palette_vars if v not in style]
                    if missing_palette_vars:
                        rep.add("ERROR", "VSTYLE-2C-PALETTE-PACK-MISSING",
                                "2C persona/detail/journey sections must set a complete TO C palette pack with --color-accent: "
                                + ", ".join(missing_palette_vars))
            section_style_matches = re.findall(
                r'<section\b(?=[^>]*class="[^"]*\blayout-2c-(?:portrait|detail|journey)\b[^"]*")'
                r'(?=[^>]*\bid="([^"]+)")(?=[^>]*\bstyle="([^"]*)")[^>]*>',
                html,
            )
            persona_palette_styles: dict[str, set[str]] = {}
            for section_id, style in section_style_matches:
                style_match = re.search(r"--color-toc-style:\s*([^;]+)", style)
                if not style_match:
                    continue
                persona_id = re.sub(r"-(?:detail|journey)$", "", section_id)
                persona_palette_styles.setdefault(persona_id, set()).add(style_match.group(1).strip())
            for persona_id, styles in persona_palette_styles.items():
                if len(styles) > 1:
                    rep.add("ERROR", "VSTYLE-2C-PALETTE-STYLE-MISMATCH",
                            f"2C persona '{persona_id}' must use one TO C palette style across portrait/detail/journey: "
                            + ", ".join(sorted(styles)))
            style_palette_families = {
                "purple-default": {"purple"},
                "red-orange": {"red-orange"},
                "green-gray": {"green-gray"},
                "yellow-orange": {"yellow-orange"},
                "blue-yellow": {"blue-yellow"},
                "cyan-gold": {"cyan-gold"},
            }
            for section_id, style in section_style_matches:
                style_match = re.search(r"--color-toc-style:\s*([^;]+)", style)
                if not style_match:
                    continue
                style_name = style_match.group(1).strip()
                allowed_families = style_palette_families.get(style_name)
                if not allowed_families:
                    rep.add("ERROR", "VSTYLE-2C-PALETTE-STYLE-UNKNOWN",
                            f"2C section '{section_id}' uses an unknown TO C palette style: {style_name}")
                    continue
                used_families = set(re.findall(r"var\(--palette-2c-([a-z]+(?:-[a-z]+)*)-[a-z]+\)", style))
                mixed_families = sorted(used_families - allowed_families)
                if mixed_families:
                    rep.add("ERROR", "VSTYLE-2C-PALETTE-CROSS-MIX",
                            f"2C section '{section_id}' must only use colors from its declared palette '{style_name}': "
                            + ", ".join(mixed_families))

        if "layout-distribution-multi" in html:
            required_bits = {
                "distribution-legend": "2C complex distribution must include a legend",
                "snake-line": "2C complex distribution must include snake lines",
                "snake-point": "2C complex distribution must include snake points",
                "data-evidence=": "2C complex distribution points must keep evidence hover",
            }
            for bit, message in required_bits.items():
                if bit not in html:
                    rep.add("ERROR", "VSTYLE-2C-DISTRIBUTION", message)
            distribution_css = [
                (".snake-point-level-label", "font-size", "max(12px,var(--text-sm))", "VSTYLE-2C-DISTRIBUTION-FONT-MIN"),
                (".snake-level-name", "font-size", "12px", "VSTYLE-2C-DISTRIBUTION-FONT-MIN"),
                (".distribution-legend-count", "font-size", "max(12px,var(--text-xs))", "VSTYLE-2C-DISTRIBUTION-FONT-MIN"),
                (".distribution-footer", "font-size", "max(12px,var(--text-sm))", "VSTYLE-2C-DISTRIBUTION-FONT-MIN"),
                (".distribution-footer-hint", "font-size", "max(12px,var(--text-xs))", "VSTYLE-2C-DISTRIBUTION-FONT-MIN"),
            ]
            for selector, prop, value, code in distribution_css:
                if not _css_has_decl(css, selector, prop, value):
                    rep.add("ERROR", code,
                            f"2C distribution text must keep a 12px minimum: {selector} must include {prop}: {value}")

        if "layout-2c-journey" in html:
            journey_css = [
                (".journey-cell", "font-size", "max(12px,var(--text-sm))"),
                (".journey-stage-header", "color", "var(--color-text-primary)"),
                (".journey-stage-header", "background", "var(--color-toc-surface, var(--color-bg-card-soft))"),
                (".journey-stage-header", "border-bottom", "2px solid var(--color-toc-primary, var(--color-accent))"),
                (".journey-stage-number", "color", "var(--color-toc-primary, var(--color-accent))"),
                (".journey-dimension-label", "font-size", "12px"),
                (".journey-dimension-label", "color", "var(--color-text-primary)"),
                (".journey-dimension-label", "background", "var(--color-toc-surface, var(--color-bg-card-soft))"),
                (".journey-cell-keyword", "font-size", "max(12px,var(--text-xs))"),
                (".journey-cell-keyword", "color", "var(--color-text-primary)"),
                (".journey-cell-summary", "font-size", "12px"),
                (".journey-pain-highlight", "background", "color-mix(in srgb, var(--color-toc-alert, var(--color-accent)) 12%, var(--color-bg-card))"),
                (".journey-pain-highlight", "border-left", "3px solid var(--color-toc-alert, var(--color-accent))"),
                (".journey-pain-highlight .journey-cell-keyword", "background", "var(--color-toc-alert, var(--color-accent))"),
                (".journey-pain-highlight .journey-cell-keyword", "color", "var(--color-text-inverse)"),
                (".journey-pain-opportunity-tag", "font-size", "max(12px,var(--text-xs))"),
                (".journey-pain-opportunity-tag", "color", "var(--color-toc-alert, var(--color-accent))"),
                (".journey-cell-touchpoint", "font-size", "max(12px,var(--text-xs))"),
                (".journey-cell-touchpoint .touchpoint-tag", "font-size", "max(12px,var(--text-xs))"),
                (".emotion-label", "font-size", "max(12px,var(--text-xs))"),
                (".emotion-label .label-text", "font-size", "12px"),
                (".journey-emotion-row", "min-height", "176px"),
                (".journey-emotion-row", "padding", "40px var(--space-4)"),
                (".journey-emotion-points-overlay", "top", "40px"),
                (".journey-emotion-points-overlay", "bottom", "40px"),
                (".emotion-label.above", "bottom", "14px"),
                (".emotion-label.below", "top", "14px"),
                (".journey-emotion-dimension-label", "display", "grid"),
                (".journey-emotion-dimension-label", "place-items", "center"),
            ]
            for selector, prop, value in journey_css:
                if not _css_has_decl(css, selector, prop, value):
                    rep.add("ERROR", "VSTYLE-2C-JOURNEY-CONTRACT",
                            f"2C journey CSS contract failed: {selector} must include {prop}: {value}")
            if "journey-emotion-dimension-label" not in html:
                rep.add("ERROR", "VSTYLE-2C-EMOTION-LABEL-ALIGN", "2C journey emotion dimension label must use the centered journey-emotion-dimension-label class")
            if not re.search(r'class="journey-emotion-svg"\s+viewBox="0 0 500 (?:80|100)"', html):
                rep.add("ERROR", "VSTYLE-2C-EMOTION-SAFE-AREA", "2C emotion curve must use a registered 80 or 100 unit viewBox with the CSS safe area")
            touchpoint_aux_css = [
                (".journey-cell-touchpoint .touchpoint-tag", "background", "var(--color-toc-aux-bg,var(--color-toc-aux,var(--color-border-subtle)))"),
                (".journey-cell-touchpoint .touchpoint-tag", "color", "var(--color-toc-aux-text,var(--color-text-primary))"),
            ]
            for selector, prop, value in touchpoint_aux_css:
                if not _css_has_decl(css, selector, prop, value):
                    rep.add("ERROR", "VSTYLE-2C-TOUCHPOINT-AUX-COLOR",
                            f"2C journey touchpoint/tool/evidence tags must use the palette auxiliary color: {selector} must include {prop}: {value}")

    is_2b_like = 'data-theme="2b"' in html or 'data-theme="2d"' in html
    if is_2b_like:
        required_2b_tokens = system["themes"]["2b"]["tokens"]
        for token, value in required_2b_tokens.items():
            if _compact_css(f"{token}:{value}") not in compact:
                rep.add("ERROR", "VSTYLE-2B-TOKEN-MISSING",
                        f"2B visual token missing or wrong: {token} must be {value.upper()}")

    if is_2b_like and "layout-2b-journey" in html:
        required_css = [
            (".l1-stage-tag", "font-size", "14px", "VSTYLE-L1-STAGE-SIZE"),
            (".l1-substage-bar", "font-size", "12px", "VSTYLE-L1-SUBSTAGE-SIZE"),
            (".l1-role-text", "font-size", "12px", "VSTYLE-L1-ROLE-SIZE"),
            (".l1-node-label", "font-size", "12px", "VSTYLE-L1-NODE-SIZE"),
            (".tob-l2-uml-hybrid .tob-stage-tag", "font-size", "14px", "VSTYLE-L2-STAGE-SIZE"),
            (".tob-l2-uml-hybrid .tob-stage-tag", "border-right", "0", "VSTYLE-L2-STAGE-WEDGE"),
            (".tob-l2-uml-hybrid .tob-substage-cell.l1-substage-bar", "font-size", "12px!important", "VSTYLE-L2-SUBSTAGE-SIZE"),
            (".tob-l2-uml-hybrid .tob-substage-cell.l1-substage-bar", "border-right", "0", "VSTYLE-L2-SUBSTAGE-WEDGE"),
            (".tob-l2-uml-hybrid .tob-tools-tag", "font-size", "12px!important", "VSTYLE-L2-TOOLS-SIZE"),
            (".tob-l2-uml-hybrid .tob-l2-uml-cell", "border-bottom", "0", "VSTYLE-L2-UML-BORDER"),
            (".tob-l2-uml-hybrid .tob-l2-uml-cell", "border-right", "0", "VSTYLE-L2-UML-BORDER"),
        ]
        for selector, prop, value, code in required_css:
            if not _css_has_decl(css, selector, prop, value):
                rep.add("ERROR", code,
                        f"CSS contract missing: {selector} must include {prop}: {value}")


ALL_CHECKS = [
    ("骨架", check_skeleton),
    ("section boundaries", check_section_boundaries),
    ("accent token", check_accent_tokens),
    ("tooltip script", check_tooltip_script),
    ("data-evidence 格式", check_data_evidence_format),
    ("矩阵结构", check_matrix),
    ("画像/旅程 nav-pair", check_nav_pair),
    ("旅程情绪节点", check_journey_emotion),
    ("section-block 三层", check_section_block),
    ("协作字段名锁定", check_collab_fields),
    ("中文标点", check_chinese_punctuation),
    ("旅程文案差异化", check_journey_emotion_copy),
    ("tab 数量", check_tab_count),
    ("画像 subtitle 重复", check_persona_subtitle_repeat),
    ("证据复用", check_evidence_duplication),
    ("2B L1 role rail", check_2b_l1_role_rail),
    ("2B L1 stage grid", check_2b_l1_stage_grid),
    ("visual style contract", check_visual_style_contract),
]


def strip_inline_blocks(html: str) -> str:
    """把 <style>...</style> 和 <script>...</script> 内容替换成等长空白,
    保留行号、不影响 attribute / 类名扫描。"""
    def blank_keep_newlines(match: re.Match) -> str:
        text = match.group(0)
        return "".join(c if c == "\n" else " " for c in text)
    out = re.sub(r"<style\b[^>]*>.*?</style>", blank_keep_newlines,
                 html, flags=re.IGNORECASE | re.DOTALL)
    out = re.sub(r"<script\b[^>]*>.*?</script>", blank_keep_newlines,
                 out, flags=re.IGNORECASE | re.DOTALL)
    return out


def run_validation(html_path: Path, project_dir: Path | None) -> Report:
    raw_html = html_path.read_text(encoding="utf-8")
    # 大部分 check 跑在剥离 <style>/<script> 之后的版本,避免 CSS/JS 文本里
    # 出现 data-evidence="" 这类字符串被误判
    html = strip_inline_blocks(raw_html)
    rep = Report(html_path=html_path)
    for name, fn in ALL_CHECKS:
        # 这些 check 必须看完整 HTML(因为要确认 script 存在与否)
        target = raw_html if name in {"tooltip script", "骨架", "visual style contract"} else html
        try:
            fn(target, rep)
        except Exception as e:  # noqa: BLE001
            rep.add("WARNING", "VALIDATOR-CRASH",
                    f"check {fn.__name__} 自己抛异常,跳过:{type(e).__name__}: {e}")
    check_avatar_usage(raw_html, rep, project_dir)
    _check_privacy_leaks(raw_html, rep, project_dir)
    _check_workflow_visual_spec(rep, project_dir)
    return rep


def _check_privacy_leaks(html: str, rep: Report, project_dir: Path | None) -> None:
    try:
        from scripts.privacy_guard import validate_privacy_in_html
    except ImportError:
        from privacy_guard import validate_privacy_in_html
    for item in validate_privacy_in_html(html, project_dir):
        rep.add(
            item["level"],
            item["code"],
            item["message"],
            snippet=item["message"][:140],
        )


def print_human_report(rep: Report) -> None:
    print(f"\n=== HTML 体检报告:{rep.html_path} ===\n")
    if not rep.issues:
        print("✓ 全部通过,可交付。")
        return

    if rep.errors:
        print(f"❌ {len(rep.errors)} 个 ERROR(阻塞交付):\n")
        for i in rep.errors:
            print(i.format())
            print()
    if rep.warnings:
        print(f"⚠  {len(rep.warnings)} 个 WARNING(建议处理):\n")
        for i in rep.warnings:
            print(i.format())
            print()


def main() -> int:
    parser = argparse.ArgumentParser(description="user-persona-v8 HTML 体检")
    parser.add_argument("html", help="最终 report.html 路径")
    parser.add_argument("--project-dir", default=None,
                        help="项目运行目录(用来检查 画像头像素材/);可选")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 而非人类可读报告")
    args = parser.parse_args()

    html_path = Path(args.html).resolve()
    if not html_path.exists():
        print(f"错误:HTML 文件不存在 {html_path}", file=sys.stderr)
        return 2

    project_dir = Path(args.project_dir).resolve() if args.project_dir else None
    rep = run_validation(html_path, project_dir)

    if args.json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human_report(rep)

    return 0 if not rep.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
