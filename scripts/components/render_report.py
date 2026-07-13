#!/usr/bin/env python3
"""P8 组件化顶层渲染入口(C 阶段)。

工作流:
  1. 读 components JSON
  2. 工作流 05-report.json 强制跑完整 checkpoint 门禁
  3. 跑 schema 与字段对齐校验
  3. 对每个 persona 调对应 assembler,收集 slide HTML
  4. 若任一 persona 触发了双页(2b-grid 溢出),把 density 切到 mid
  5. 首个 slide 加 .active class
  6. build_nav 算 nav HTML
  7. 填 _base.html 的 slot
  8. 把 _design-tokens.css + _components.css 复制到输出目录
  9. 写 report.html
  11. 跑 P7 validate_html 体检(ERROR 阻塞)

CLI:
  python scripts/components/render_report.py --input <项目>/过程稿/05-report.json \
      --output <项目>/最终交付件-<标识>/report.html --project-dir <项目>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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

try:
    from scripts.path_utils import PROCESS_DIR_NAME, resolve_process_dir
except ImportError:
    PROCESS_DIR_NAME = "过程稿"
    resolve_process_dir = None  # type: ignore


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


def _resolve_dirs(input_path: Path | None, output_dir: Path) -> tuple[Path | None, Path | None]:
    """从 05-report.json 路径推断过程稿目录与项目运行目录。"""
    process_dir: Path | None = None
    project_dir: Path | None = None
    if input_path is not None:
        inp = Path(input_path).resolve()
        if inp.parent.name == PROCESS_DIR_NAME:
            process_dir = inp.parent
            project_dir = process_dir.parent
        elif resolve_process_dir is not None:
            process_dir = resolve_process_dir(inp.parent)
            if process_dir.name == PROCESS_DIR_NAME:
                project_dir = process_dir.parent
    if project_dir is None and output_dir is not None:
        out = Path(output_dir).resolve()
        if out.parent.name == PROCESS_DIR_NAME:
            process_dir = process_dir or out.parent
            project_dir = out.parent.parent
        elif (out.parent / "过程稿").is_dir():
            project_dir = out.parent
            process_dir = process_dir or (project_dir / "过程稿")
    return process_dir, project_dir


def render_report(
    input_json: dict,
    output_dir: Path,
    validate: bool = True,
    input_path: Path | None = None,
) -> str:
    """渲染完整 report.html 字符串。

    Args:
        input_json: 顶层 components JSON dict(符合 schemas/report.json)
        output_dir: 输出目录(用来 copy CSS 文件,以及供 validate_html 体检)
        validate: True 时,跑 schema 校验(若 validate_components_json 可用)+ 末尾 HTML 体检

    Returns:
        完整 report.html 字符串(已写到 output_dir/report.html)
    """
    output_dir = Path(output_dir)

    process_dir, project_dir = _resolve_dirs(input_path, output_dir)

    # 工作流渲染必须存在 00-05 全部 MD/JSON 配对与一一对应的抽取产物。
    _try_checkpoint_pairing_gate(process_dir, input_path)
    _try_journey_checkpoint_gate(process_dir, input_json)

    raw_input_json = input_json
    if process_dir is not None:
        from scripts.resolve_content_refs import resolve_report_content_refs
        input_json = resolve_report_content_refs(raw_input_json, process_dir)
        from scripts.avatar_assets import apply_default_avatar_assignments
        alignment = json.loads((process_dir / "03-field-alignment.json").read_text(encoding="utf-8")) if (process_dir / "03-field-alignment.json").is_file() else {}
        if (alignment.get("visual_assets") or {}).get("avatar_use_default") is True:
            apply_default_avatar_assignments(input_json, process_dir)

    metadata = dict(input_json["metadata"])  # 浅拷贝,避免改原对象
    personas = input_json["personas"]

    # 1. schema 与字段对齐校验
    if validate:
        _try_schema_validate(raw_input_json, process_dir)
        _try_field_alignment_gate(process_dir or output_dir)

    # JSON 门禁通过后才允许创建临时渲染目录。
    output_dir.parent.mkdir(parents=True, exist_ok=True)

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

    if process_dir is not None:
        planned_page_count = metadata.get("page_count")
        if planned_page_count != len(all_slides):
            raise ValueError(
                f"05 page plan mismatch: metadata.page_count={planned_page_count!r}, "
                f"but assemblers produced {len(all_slides)} pages. Return to 05-report.md, "
                "show the final page list to the user, and confirm any module removal or merge."
            )

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

    # 6. 填 slot。每个真实 slot 必须恰好出现一次，模板漂移立即阻塞。
    template = BASE_TEMPLATE_PATH.read_text(encoding="utf-8")
    out = _strip_mustache_in_comments(template)
    page_title = metadata.get("page_title") or metadata["report_title"]
    replacements = {
        "theme": metadata["theme"],
        "density": density,
        "accent_inline": "",
        "title": page_title,
        "report_title": metadata["report_title"],
        "report_meta_info": _format_meta_info(metadata),
        "persona_nav": nav_html,
        "main_content": "\n".join(all_slides),
    }
    for name, value in replacements.items():
        out = _replace_single_slot(out, name, value)
    unresolved = re.findall(r"\{\{[^}]+\}\}", out)
    if unresolved:
        raise ValueError(f"_base.html 存在未注册 slot: {sorted(set(unresolved))}")

    # 7. 在同级临时目录完成 HTML、CSS、素材和 P7 校验。成功后再发布，
    # 防止失败产物覆盖上一版有效交付件。
    staging_dir = Path(tempfile.mkdtemp(prefix=".persona-render-", dir=output_dir.parent))
    try:
        report_path = staging_dir / "report.html"
        report_path.write_text(out, encoding="utf-8")
        _copy_css(staging_dir)
        _stage_avatars(input_json, out, staging_dir)
        _write_delivery_notes(staging_dir, metadata, process_dir)
        if validate:
            try:
                _try_html_validate(report_path, project_dir)
            except Exception as exc:
                preview_dir = output_dir.with_name(f"预览-待修复-{uuid.uuid4().hex[:8]}")
                (staging_dir / "预览问题.txt").write_text(
                    "该目录是渲染器保留的诊断预览，不是最终交付件。\n\n" + str(exc),
                    encoding="utf-8",
                )
                os.replace(staging_dir, preview_dir)
                raise RuntimeError(f"HTML 视觉门禁未通过；已保留可查看预览：{preview_dir}\n{exc}") from exc
        backup_dir: Path | None = None
        if output_dir.exists():
            backup_dir = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
            os.replace(output_dir, backup_dir)
        try:
            os.replace(staging_dir, output_dir)
        except Exception:
            if backup_dir is not None and backup_dir.exists() and not output_dir.exists():
                os.replace(backup_dir, output_dir)
            raise
        else:
            if backup_dir is not None:
                shutil.rmtree(backup_dir, ignore_errors=True)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return out


# ============================================================
# 辅助
# ============================================================


def _strip_mustache_in_comments(template: str) -> str:
    """剥掉 HTML 注释内的 {{...}} 字面字符,避免文档说明里的 slot 名被误替换。"""
    def _scrub(m: re.Match) -> str:
        return re.sub(r"\{\{[^}]+\}\}", "[slot]", m.group(0))
    return re.sub(r"<!--[\s\S]*?-->", _scrub, template)


def _replace_single_slot(template: str, name: str, value: str) -> str:
    slot = "{{" + name + "}}"
    count = template.count(slot)
    if count != 1:
        raise ValueError(f"_base.html slot {slot} 必须恰好出现 1 次，实际 {count} 次")
    return template.replace(slot, str(value), 1)


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
        parts.append(f"{sc} 份独立主访谈")
    summary = metadata.get("source_summary") or {}
    supplemental = summary.get("unique_supplemental_sources")
    if isinstance(supplemental, int) and supplemental:
        parts.append(f"{supplemental} 份补充材料")
    ts = metadata.get("generated_at")
    if ts:
        parts.append(str(ts))
    return " · ".join(parts)


def _copy_css(output_dir: Path) -> None:
    for src in (DESIGN_TOKENS_PATH, COMPONENTS_CSS_PATH):
        if src.exists():
            shutil.copy2(src, output_dir / src.name)


def _write_delivery_notes(output_dir: Path, metadata: dict, process_dir: Path | None) -> None:
    """Write a deterministic handoff note for the generated delivery directory."""
    visual_assets: dict = {}
    if process_dir is not None:
        alignment = process_dir / "03-field-alignment.json"
        if alignment.is_file():
            try:
                visual_assets = json.loads(alignment.read_text(encoding="utf-8")).get("visual_assets") or {}
            except (OSError, json.JSONDecodeError):
                visual_assets = {}
    if visual_assets.get("avatar_provided"):
        avatar_strategy = "使用项目中经用户授权的自定义头像"
    elif visual_assets.get("avatar_use_default"):
        avatar_strategy = "使用 skill 内置非真人默认头像"
    else:
        avatar_strategy = "本报告未确认头像素材"
    screenshots = "启用" if (
        visual_assets.get("screenshots_enabled") or visual_assets.get("scenario_screenshots_enabled")
    ) else "未启用"
    lines = [
        "# 交付件说明",
        "",
        f"- 报告：{metadata.get('report_title', '')}",
        f"- 独立主访谈：{metadata.get('source_count', '')}",
        f"- 独立补充材料：{(metadata.get('source_summary') or {}).get('unique_supplemental_sources', 0)}",
        f"- 分析分配次数：{(metadata.get('source_summary') or {}).get('analysis_assignment_count', '')}",
        f"- 画像数：{metadata.get('persona_count', '')}",
        f"- 生成时间：{metadata.get('generated_at', '')}",
        "",
        "## 视觉素材",
        "",
        f"- 头像：{avatar_strategy}",
        f"- 场景或旅程截图：{screenshots}",
        "- 默认头像库：`assets/default-avatars/`",
        "- 如需替换素材，请更新项目目录中的授权素材并重新渲染。",
        "",
        "## 续跑与修改",
        "",
        "- 系统续跑真值为 `过程稿/05-report.json` 及其前序检查点。",
        "- 不要直接修改 `report.html`、CSS 或生成后的 assets。",
        "- 修改研究目标、字段、画像或旅程后，从最早受影响的检查点重新确认。",
        "",
    ]
    assignments = metadata.get("_internal_avatar_assignments") or {}
    if assignments:
        lines.insert(lines.index(f"- 场景或旅程截图：{screenshots}"), "- 默认头像分配：" + "；".join(f"{name} → {filename}" for name, filename in assignments.items()))
    (output_dir / "交付件说明.md").write_text("\n".join(lines), encoding="utf-8")


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
    except ImportError as exc:
        raise RuntimeError(
            "validate_field_alignment.py 不可用，拒绝渲染可交付报告"
        ) from exc

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
    errors = validate_field_alignment(data, require_assets_ready=True)
    if errors:
        head = "\n".join(f"  - {e}" for e in errors[:8])
        raise RuntimeError(
            f"03-field-alignment.json 未通过硬门禁({alignment_path}):\n{head}\n"
            f"须回到 steps/field-alignment.md Step 1 展示字段池并获用户确认后再渲染。"
        )


def _try_checkpoint_pairing_gate(process_dir: Path | None, input_path: Path | None) -> None:
    """When rendering a workflow report, require paired MD/JSON checkpoints."""
    is_workflow_report = input_path is not None and Path(input_path).name == "05-report.json"
    if process_dir is None or not process_dir.exists():
        if is_workflow_report:
            raise RuntimeError(
                "cannot locate the process directory for workflow 05-report.json; rendering is blocked"
            )
        return

    is_named_process_dir = process_dir.name == "过程稿"
    should_gate = is_named_process_dir or is_workflow_report
    if not should_gate:
        return

    try:
        from scripts.validate_checkpoint_pairing import validate_checkpoint_pairing
    except ImportError as exc:
        raise RuntimeError(
            f"validate_checkpoint_pairing unavailable; refusing to render workflow report from {process_dir}. "
            "Install or restore scripts/validate_checkpoint_pairing.py before delivery."
        ) from exc

    errors = validate_checkpoint_pairing(process_dir, require_complete=True)
    if errors:
        head = "\n".join(
            f"  - {item.get('code')}: {item.get('path')} | {item.get('message')}"
            for item in errors[:8]
        )
        raise RuntimeError(
            f"checkpoint pairing failed for {process_dir}; rendering is blocked:\n{head}\n"
            f"Fix: add the missing .md/.json checkpoints and processed/extracted artifacts, then rerun render_report.py."
        )


def _try_schema_validate(input_json: dict, process_dir: Path | None = None) -> None:
    """跑 F 阶段的 validate_components_json(P8 事前校验 + P0-PRIVACY)。"""
    try:
        from scripts.components.validate import validate_report_json, format_issues_for_human
    except ImportError as e:
        raise RuntimeError(
            f"validate_components_json 不可用，拒绝渲染可交付报告: {e}"
        ) from e

    issues = validate_report_json(input_json, process_dir)
    errors = [i for i in issues if i.get("level") == "ERROR"]
    if errors:
        raise ValueError(
            f"组件 JSON 校验失败,{len(errors)} 个 ERROR:\n{format_issues_for_human(errors)}"
        )


def _try_journey_checkpoint_gate(process_dir: Path | None, input_json: dict) -> None:
    """Keep every rendered journey identical to the user-confirmed 04 checkpoint."""
    if process_dir is None:
        return
    try:
        from scripts.validate_journey_checkpoint import validate_journey_checkpoint
    except ImportError as exc:
        raise RuntimeError(
            "validate_journey_checkpoint unavailable; refusing to render workflow report."
        ) from exc
    errors = validate_journey_checkpoint(process_dir)
    if errors:
        head = "\n".join(
            f"  - {item.get('code')}: {item.get('path')} | {item.get('message')}"
            for item in errors[:8]
        )
        raise RuntimeError(
            "journey checkpoint validation failed; rendering is blocked:\n"
            f"{head}\nFix 04-journeys.md/json and rebuild 05-report.json."
        )


def _try_html_validate(report_path: Path, project_dir: Path | None = None) -> None:
    """跑 P7 validate_html(若可用),ERROR 阻塞渲染。

    Codex review 2026-05-25 P1:体检 ERROR 只 WARN 会让带 ERROR 的产物流出。
    retcode != 0 时直接阻塞发布。
    """
    try:
        import subprocess
        cmd = [sys.executable, str(SKILL_ROOT / "scripts" / "validate_html.py"), str(report_path)]
        if project_dir is not None:
            cmd.extend(["--project-dir", str(project_dir)])
        result = subprocess.run(
            cmd,
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
            )
    except FileNotFoundError as e:
        raise RuntimeError(f"validate_html.py 不可用，拒绝交付: {e}") from e
    except RuntimeError:
        raise  # 上面 retcode != 0 的真错,继续往上抛
    except Exception as e:
        raise RuntimeError(f"validate_html 调用失败，拒绝交付: {e}") from e


# ============================================================
# CLI
# ============================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="P8 组件化报告渲染入口")
    parser.add_argument("--input", required=True, help="components JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 report.html 路径(目录用来放 CSS)")
    parser.add_argument(
        "--project-dir",
        required=True,
        help="项目运行目录(含 过程稿/、画像头像素材/ 和最终交付件-*/)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_dir = out_path.parent
    project_dir = Path(args.project_dir).resolve()
    expected_input = project_dir / PROCESS_DIR_NAME / "05-report.json"
    if in_path.resolve() != expected_input.resolve():
        parser.error("公开渲染入口只接受 <项目>/过程稿/05-report.json，禁止复制或改名后绕过工作流门禁")
    if out_path.name != "report.html":
        parser.error("--output 必须以 report.html 结尾")
    if out_dir.parent.resolve() != project_dir or not out_dir.name.startswith("最终交付件-"):
        parser.error("--output 必须位于 <项目>/最终交付件-<标识>/report.html，确保恢复检查能识别交付状态")

    os.environ["PROJECT_DIR"] = str(project_dir)

    input_json = json.loads(in_path.read_text(encoding="utf-8"))
    render_report(
        input_json,
        out_dir,
        validate=True,
        input_path=in_path,
    )
    print(f"[OK] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
