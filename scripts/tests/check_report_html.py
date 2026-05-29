#!/usr/bin/env python3
"""Check final report HTML structure contracts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from quality_common import Issue, emit_result, find_delivery_dirs, journey_sections, normalized_similarity, read_text, strip_html

try:
    from path_utils import resolve_process_dir
except Exception:  # pragma: no cover
    resolve_process_dir = None

ALLOWED_LAYOUTS = (
    "layout-2b-grid",
    "layout-2b-journey",
    "layout-2c-portrait",
    "layout-2c-detail",
    "layout-2c-journey",
    "layout-matrix-2d",
    "layout-distribution-multi",
)


def resolve_report(args) -> tuple[Path, Path | None]:
    if args.input:
        path = Path(args.input).resolve()
        return path, path.parent
    if args.delivery_dir:
        delivery = Path(args.delivery_dir).resolve()
        return delivery / "report.html", delivery
    workdir = Path(args.workdir).resolve()
    process_dir = resolve_process_dir(workdir) if resolve_process_dir else workdir
    run_dir = process_dir.parent if process_dir.name == "过程稿" else process_dir
    deliveries = find_delivery_dirs(run_dir)
    if deliveries:
        return deliveries[0] / "report.html", deliveries[0]
    return process_dir / "report.html", process_dir


def check_skeleton(html: str, errors: list[Issue], warnings: list[Issue]) -> None:
    if "data-theme=" not in html or "data-density=" not in html:
        errors.append(Issue("html.skeleton", "最终 HTML 必须包含 data-theme 和 data-density。", "report.html"))
    if not any(layout in html for layout in ALLOWED_LAYOUTS):
        errors.append(Issue("html.layout_missing", "最终 HTML 未发现允许的 layout 类。", "report.html"))
    if "{{" in html and "}}" in html:
        errors.append(Issue("html.unrendered_slot", "最终 HTML 仍包含未替换的模板 slot。", "report.html"))
    if "onclick=" in html:
        errors.append(Issue("html.onclick_nav", "最终 HTML 导航仍使用 onclick,应使用 data-target。", "report.html"))
    if "line-clamp" in html or "text-overflow: ellipsis" in html:
        errors.append(Issue("html.truncation_css", "最终 HTML 包含截断 CSS。", "report.html"))
    if re.search(r">\s*受访者\d+\s*<", html):
        errors.append(Issue("html.generic_respondent", "可见文本出现受访者编号。", "report.html"))
    if re.search(r"\bU\d+[_-][\u4e00-\u9fff]{2,4}\b", strip_html(html)):
        errors.append(Issue("html.full_name_source", "可见文本出现 U编号_真实姓名 source。", "report.html"))


def check_nav_and_targets(html: str, errors: list[Issue]) -> None:
    ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    targets = re.findall(r'data-target=["\']([^"\']+)["\']', html)
    for target in targets:
        if target not in ids:
            errors.append(Issue("html.target_missing", f"data-target={target} 找不到对应 section id。", "report.html"))

    has_journey = bool(re.search(r'id=["\'][^"\']+-journey["\']', html)) or "layout-2c-journey" in html
    if has_journey:
        if ".nav-pair" not in html and 'class="nav-pair' not in html and "class='nav-pair" not in html:
            errors.append(Issue("html.nav_pair_missing", "存在旅程页时必须有 .nav-pair。", "report.html"))
        if "nav-btn-journey" not in html:
            errors.append(Issue("html.nav_journey_missing", "存在旅程页时必须有 .nav-btn-journey。", "report.html"))
        journey_buttons = re.findall(r'<button\b[^>]*class=["\'][^"\']*nav-btn-journey[^"\']*["\'][^>]*>([\s\S]*?)</button>', html, flags=re.I)
        for text in journey_buttons:
            if strip_html(text) != "› 旅程":
                errors.append(Issue("html.nav_journey_text", "旅程按钮文案必须固定为 › 旅程。", "report.html"))


def check_matrix(html: str, errors: list[Issue]) -> None:
    if "layout-matrix-2d" not in html:
        return
    labels = re.findall(r'<button\b[^>]*class=["\'][^"\']*matrix-quadrant-label[^"\']*["\'][^>]*data-target=["\'][^"\']+["\'][^>]*>', html, flags=re.I)
    if not labels:
        errors.append(Issue("html.matrix_quadrant_button", "矩阵象限标签必须是 button.matrix-quadrant-label 并带 data-target。", "report.html"))
    dots = re.findall(r'class=["\'][^"\']*matrix-respondent-dot[^"\']*["\'][^>]*', html, flags=re.I)
    svg_dots = re.findall(r'class=["\'][^"\']*respondent[^"\']*["\'][^>]*data-evidence=', html, flags=re.I)
    if not dots and not svg_dots:
        errors.append(Issue("html.matrix_dot_missing", "矩阵页缺少带 data-evidence 的受访者点位。", "report.html"))
    label_tags = re.findall(r'class=["\']([^"\']*\brespondent-label\b[^"\']*)["\']', html, flags=re.I)
    if label_tags and not all("label-" in tag for tag in label_tags):
        errors.append(Issue("html.respondent_label_direction", "每个 respondent-label 必须带 label-* 避让类。", "report.html"))
    if not label_tags and "respondent-label-text" not in html:
        errors.append(Issue("html.respondent_label_missing", "矩阵页缺少受访者可读标签。", "report.html"))


def check_journey_similarity(html: str, errors: list[Issue]) -> None:
    sections = journey_sections(html)
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            ratio = normalized_similarity(sections[i], sections[j])
            if ratio > 0.70:
                errors.append(Issue(
                    "html.journey_duplicate",
                    f"旅程页 {i + 1} 与 {j + 1} 正文相似度 {ratio:.0%},超过 70%。",
                    "report.html",
                ))


def check_2b_journey_contract(html: str, errors: list[Issue]) -> None:
    if "layout-2b-journey" not in html:
        return
    if "is-highlight" in html:
        errors.append(Issue("html.2b_journey_highlight", "2B 旅程工作流单元格必须统一使用浅蓝样式,不能有深蓝高亮单元格。", "report.html"))
    if "tob-pain-banner" in html:
        errors.append(Issue("html.2b_journey_pain_row", "2B 单角色旅程不能有独立痛点行,痛点必须合并到关注点行。", "report.html"))
    if re.search(r'layout-2b-journey[^"\']*is-l2', html) and "关注点 / 痛点" not in html:
        errors.append(Issue("html.2b_journey_focus_pain_label", "2B 单角色旅程行标题必须是 关注点 / 痛点。", "report.html"))
    flow_pills = re.findall(
        r'<span\b[^>]*class=["\'][^"\']*\btob-flow-pill\b[^"\']*["\'][^>]*data-evidence=["\']([^"\']*)["\']',
        html,
        flags=re.I,
    )
    if flow_pills and any(not value.strip() for value in flow_pills):
        errors.append(Issue("html.2b_journey_flow_evidence", "2B 旅程工作流单元格必须带用户原声 hover 证据。", "report.html"))


def check_delivery_paths(html: str, report_path: Path, delivery_dir: Path | None, errors: list[Issue]) -> None:
    if "过程稿/" in html or "过程稿\\" in html:
        errors.append(Issue("html.process_path_ref", "最终 HTML 引用了过程稿目录。", str(report_path)))
    if re.search(r'[A-Za-z]:\\|file://|/home/claude/|/tmp/', html):
        errors.append(Issue("html.absolute_path_ref", "最终 HTML 引用了本机绝对路径或临时路径。", str(report_path)))
    if delivery_dir and delivery_dir.name.startswith("最终交付件-") and report_path.parent != delivery_dir:
        errors.append(Issue("delivery.report_location", "report.html 必须位于最终交付件目录根部。", str(report_path)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="report.html 路径")
    parser.add_argument("--delivery-dir", help="最终交付件目录")
    parser.add_argument("--workdir", default=".", help="项目运行目录或过程稿目录")
    args = parser.parse_args()

    report_path, delivery_dir = resolve_report(args)
    if not report_path.exists():
        return emit_result(
            check_name="report_html",
            errors=[Issue("html.not_found", "未找到 report.html。", str(report_path))],
            next_step="先渲染最终 HTML,或传入 --input/--delivery-dir。",
        )
    html = read_text(report_path)
    errors: list[Issue] = []
    warnings: list[Issue] = []
    check_skeleton(html, errors, warnings)
    check_nav_and_targets(html, errors)
    check_matrix(html, errors)
    check_journey_similarity(html, errors)
    check_2b_journey_contract(html, errors)
    check_delivery_paths(html, report_path, delivery_dir, errors)
    return emit_result(
        check_name="report_html",
        errors=errors,
        warnings=warnings,
        next_step="修复 HTML 结构、导航、矩阵、旅程或交付路径后重跑。",
        extra={"report": str(report_path)},
    )


if __name__ == "__main__":
    raise SystemExit(main())
