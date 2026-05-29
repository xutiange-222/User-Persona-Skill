#!/usr/bin/env python3
"""P8 组件化顶层渲染入口(C 阶段)。

工作流:
  1. 读 components JSON
  2. (可选)跑 schema 校验
  3. 对每个 persona 调对应 assembler,收集 slide HTML
  4. 若任一 persona 触发了双页(2b-grid 溢出),把 density 切到 mid
  5. 首个 slide 加 .active class
  6. build_nav 算 nav HTML
  7. 填 _base.html 的 slot
  8. 把 _design-tokens.css + _components.css 复制到输出目录
  9. 写 report.html
  10. (可选)跑 P7 validate_html 体检(warn 不阻塞)

CLI:
  python scripts/components/render_report.py --input <input.json> --output <out.html>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# 让脚本直接跑(__name__ == "__main__")时也能 import 同包
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent  # skill 根
if __package__ in (None, ""):
    sys.path.insert(0, str(_REPO_ROOT))
    from scripts.components.layouts.assemble import ASSEMBLERS
    from scripts.components.layouts.nav import build_nav
else:
    from .layouts.assemble import ASSEMBLERS
    from .layouts.nav import build_nav


# ============================================================
# 资源定位
# ============================================================

# skill 根 = scripts/components/.. /..
SKILL_ROOT = _SCRIPT_DIR.parent.parent
BASE_TEMPLATE_PATH = SKILL_ROOT / "assets" / "templates" / "_base.html"
DESIGN_TOKENS_PATH = SKILL_ROOT / "assets" / "templates" / "_design-tokens.css"
COMPONENTS_CSS_PATH = SKILL_ROOT / "assets" / "templates" / "_components.css"


# ============================================================
# 主入口
# ============================================================


def render_report(input_json: dict, output_dir: Path, validate: bool = True) -> str:
    """渲染完整 report.html 字符串。

    Args:
        input_json: 顶层 components JSON dict(符合 schemas/report.json)
        output_dir: 输出目录(用来 copy CSS 文件,以及供 validate_html 体检)
        validate: True 时,跑 schema 校验(若 validate_components_json 可用)+ 末尾 HTML 体检

    Returns:
        完整 report.html 字符串(已写到 output_dir/report.html)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = dict(input_json["metadata"])  # 浅拷贝,避免改原对象
    personas = input_json["personas"]

    # 1. schema 校验(可选,F 阶段产物;尚未实现就跳过)
    if validate:
        _try_schema_validate(input_json)
        _try_field_alignment_gate(output_dir)

    # 2. 调 assembler,收集所有 slide
    all_slides: list[str] = []
    for persona in personas:
        layout = persona["layout"]
        if layout not in ASSEMBLERS:
            raise ValueError(f"未注册的 layout: {layout}")
        assembler = ASSEMBLERS[layout]
        slides = assembler(persona, metadata)
        if not isinstance(slides, list):
            raise TypeError(f"{layout} assembler 必须返回 list,实际 {type(slides).__name__}")
        all_slides.extend(slides)

    # 3. 双页 density 切换
    density = metadata.get("_internal_density_override") or metadata["density"]

    # 4. 首个 slide 加 .active
    if all_slides:
        all_slides[0] = _inject_active_class(all_slides[0])

    # 5. nav
    # build_nav 以 persona id 为单位组装;双页拆出的 -core/-detail 是 assemble 内部命名,
    # 不出现在 personas 数组里 — 但我们要让 nav 也能配对它们。
    # 解决方案:nav 看 personas 数组里的 id;若某 persona layout 是 2b-grid 且触发了双页
    # (slide 数=2),把 -detail 这个 id 也"补"进 nav 计算(参与 trio/pair)。
    nav_personas = _expand_nav_personas(personas, all_slides)
    nav_html = build_nav(nav_personas, active_id=nav_personas[0]["id"] if nav_personas else None)

    # 6. 填 slot
    template = BASE_TEMPLATE_PATH.read_text(encoding="utf-8")
    # 关键:_base.html 顶部注释里有 slot 名(说明文档),不能被当成真的 slot 替换
    # 先剥掉 HTML 注释内所有 {{...}} 字面字符,再做 replace
    out = _strip_mustache_in_comments(template)
    out = out.replace("{{theme}}", metadata["theme"])
    out = out.replace("{{density}}", density)
    out = out.replace("{{accent_inline}}", "")  # 各 slide 内 inline,顶层填空
    page_title = metadata.get("page_title") or metadata["report_title"]
    out = out.replace("{{title}}", page_title)
    out = out.replace("{{report_title}}", metadata["report_title"])
    out = out.replace("{{report_meta_info}}", _format_meta_info(metadata))
    out = out.replace("{{persona_nav}}", nav_html)
    out = out.replace("{{main_content}}", "\n".join(all_slides))
    # 兜底清残留(仅文档内未列出的 slot)
    out = re.sub(r"\{\{[^}]+\}\}", "", out)

    # 7. 写文件 + CSS 随包 + 头像随包
    report_path = output_dir / "report.html"
    report_path.write_text(out, encoding="utf-8")
    _copy_css(output_dir)
    _stage_avatars(input_json, out, output_dir)

    # 8. P7 体检(warn 不阻塞)
    if validate:
        _try_html_validate(report_path)

    return out


# ============================================================
# 辅助
# ============================================================


def _strip_mustache_in_comments(template: str) -> str:
    """剥掉 HTML 注释内的 {{...}} 字面字符,避免文档说明里的 slot 名被误替换。"""
    def _scrub(m: re.Match) -> str:
        return re.sub(r"\{\{[^}]+\}\}", "[slot]", m.group(0))
    return re.sub(r"<!--[\s\S]*?-->", _scrub, template)


def _inject_active_class(slide_html: str) -> str:
    """把 <section class="persona-slide layout-XXX" ...> 改成含 active 的版本。"""
    return slide_html.replace(
        'class="persona-slide ',
        'class="persona-slide active ',
        1,
    )


def _expand_nav_personas(personas: list[dict], all_slides: list[str]) -> list[dict]:
    """如果某个 2b-grid 拆了双页,nav 应该展示成 nav-pair(画像 + 细节)。

    扫 all_slides 找 -core / -detail id,把它们补回 nav personas 数组。
    """
    # 提取所有 slide id
    slide_ids = re.findall(r'<section class="persona-slide(?:\s+\w+)*[^"]*" id="([^"]+)"', " ".join(all_slides))

    expanded = []
    for p in personas:
        pid = p["id"]
        # 这个 persona 是否被拆双页?(slide 里出现 pid-core 而不出现 pid)
        core_id = f"{pid}-core"
        detail_id = f"{pid}-detail"
        if core_id in slide_ids and detail_id in slide_ids and pid not in slide_ids:
            # 拆双页了:补 core / detail 两个 entry,删原 entry
            expanded.append({"id": core_id, "name": p["name"], "layout": p["layout"]})
            expanded.append({"id": detail_id, "name": p["name"], "layout": "layout-2b-grid-detail"})
        else:
            expanded.append(p)
    return expanded


def _format_meta_info(metadata: dict) -> str:
    parts = []
    pc = metadata.get("persona_count")
    if pc:
        parts.append(f"{pc} 个画像")
    sc = metadata.get("source_count")
    if sc:
        parts.append(f"来源 {sc} 份访谈")
    ts = metadata.get("generated_at")
    if ts:
        parts.append(str(ts))
    return " · ".join(parts)


def _copy_css(output_dir: Path) -> None:
    for src in (DESIGN_TOKENS_PATH, COMPONENTS_CSS_PATH):
        if src.exists():
            shutil.copy2(src, output_dir / src.name)


def _stage_avatars(input_json: dict, html: str, output_dir: Path) -> None:
    """把解析到的头像复制进交付件 assets/画像头像素材/。"""
    try:
        from scripts.avatar_assets import (
            collect_avatar_filenames_from_html,
            collect_avatar_filenames_from_json,
            stage_avatars_to_delivery,
        )
    except ImportError:
        return

    filenames = collect_avatar_filenames_from_json(input_json)
    filenames |= collect_avatar_filenames_from_html(html)
    for persona in input_json.get("personas", []):
        if persona.get("name"):
            filenames.add(f"{persona['name']}.png")
    copied = stage_avatars_to_delivery(output_dir, filenames)
    if copied:
        rel = (output_dir / "assets" / "画像头像素材").relative_to(output_dir)
        print(f"[OK] staged {len(copied)} avatar(s) → {rel}", file=sys.stderr)


def _try_field_alignment_gate(output_dir: Path) -> None:
    """若项目目录存在 03-field-alignment.json,渲染前必须通过字段对齐硬门禁。"""
    try:
        from scripts.validate_field_alignment import (
            find_field_alignment_file,
            validate_field_alignment,
        )
    except ImportError:
        return

    project = os.environ.get("PROJECT_DIR")
    search_roots = [Path(output_dir)]
    if project:
        search_roots.insert(0, Path(project))

    alignment_path = None
    for root in search_roots:
        alignment_path = find_field_alignment_file(root)
        if alignment_path:
            break

    if not alignment_path:
        return

    data = json.loads(alignment_path.read_text(encoding="utf-8"))
    errors = validate_field_alignment(data)
    if errors:
        head = "\n".join(f"  - {e}" for e in errors[:8])
        raise RuntimeError(
            f"03-field-alignment.json 未通过硬门禁({alignment_path}):\n{head}\n"
            f"须回到 steps/field-alignment.md Step 1 展示字段池并获用户确认后再渲染。"
            f"调试可用 --skip-validate 绕过(产物不可交付)。"
        )


def _try_schema_validate(input_json: dict) -> None:
    """跑 F 阶段的 validate_components_json(P8 事前校验)。"""
    try:
        from scripts.components.validate import validate_report_json, format_issues_for_human
    except ImportError as e:
        # 兜底:F 阶段产物不可用时仍允许跑,但 warn 一次
        print(f"[WARN] validate_components_json 不可用,跳过事前校验:{e}", file=sys.stderr)
        return

    issues = validate_report_json(input_json)
    errors = [i for i in issues if i.get("level") == "ERROR"]
    if errors:
        raise ValueError(
            f"组件 JSON 校验失败,{len(errors)} 个 ERROR:\n{format_issues_for_human(errors)}"
        )


def _try_html_validate(report_path: Path) -> None:
    """跑 P7 validate_html(若可用),ERROR 阻塞渲染。

    Codex review 2026-05-25 P1:体检 ERROR 只 WARN 会让带 ERROR 的产物流出。
    现在:retcode != 0 → 直接 raise,保留 --skip-validate 逃生口给主路径调用方控制。
    """
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "validate_html.py"), str(report_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            # 只取 ERROR 行做简洁报错(完整输出 stderr 仍打印一遍方便调试)
            err_lines = [l for l in stdout.splitlines() if l.startswith("[ERROR]")]
            head = "\n".join(err_lines[:8]) if err_lines else stdout[:500]
            print(f"[validate_html stdout]\n{stdout}", file=sys.stderr)
            if stderr:
                print(f"[validate_html stderr]\n{stderr}", file=sys.stderr)
            raise RuntimeError(
                f"validate_html 体检失败(retcode={result.returncode}),"
                f"{len(err_lines)} 个 ERROR(显示前 8):\n{head}\n"
                f"修法:回去改 05-report.json 源数据或对应 renderer,不要直接改 report.html。"
                f"调试时可用 --skip-validate 绕过(产物不可交付)。"
            )
    except FileNotFoundError as e:
        print(f"[WARN] validate_html.py 不可用,跳过 HTML 体检:{e}", file=sys.stderr)
    except RuntimeError:
        raise  # 上面 retcode != 0 的真错,继续往上抛
    except Exception as e:
        print(f"[WARN] validate_html 调用失败:{e}(跳过)", file=sys.stderr)


# ============================================================
# CLI
# ============================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="P8 组件化报告渲染入口")
    parser.add_argument("--input", required=True, help="components JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 report.html 路径(目录用来放 CSS)")
    parser.add_argument(
        "--project-dir",
        help="项目运行目录(含 画像头像素材/;未指定时尝试从 --output 路径推断)",
    )
    parser.add_argument("--skip-validate", action="store_true", help="跳过 schema + HTML 校验")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_dir = out_path.parent

    if args.project_dir:
        os.environ["PROJECT_DIR"] = str(Path(args.project_dir).resolve())
    else:
        try:
            from scripts.avatar_assets import infer_project_dir

            inferred = infer_project_dir(out_dir)
            if inferred:
                os.environ.setdefault("PROJECT_DIR", str(inferred))
        except ImportError:
            pass

    input_json = json.loads(in_path.read_text(encoding="utf-8"))
    html = render_report(input_json, out_dir, validate=not args.skip_validate)
    # render_report 已经写到 out_dir/report.html;如果 user 指定的输出名不是 report.html,再 copy 一份
    default_path = out_dir / "report.html"
    if out_path.resolve() != default_path.resolve():
        out_path.write_text(html, encoding="utf-8")
    print(f"[OK] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
