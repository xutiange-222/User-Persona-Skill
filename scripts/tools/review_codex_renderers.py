#!/usr/bin/env python3
"""
检查 Codex 阶段 B 产出:24 个 renderer + grid_solver + gallery 工具 + 测试 + CSS 改动。

用法:
    python scripts/tools/review_codex_renderers.py

输出 PASS/FAIL 列表 + 推荐下一步。

退出码:
    0 = 全 PASS
    1 = 有 FAIL
"""

from __future__ import annotations

import io
import importlib
import subprocess
import sys
from pathlib import Path

# Windows GBK 兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SKILL_ROOT = Path(__file__).resolve().parents[2]
COMP_ROOT = SKILL_ROOT / "scripts" / "components"

# 24 个 LLM 顶层 type（report.json enum；section_block 仅作 grid 子项）
ALL_TYPES = [
    "identity_panel", "resp_rings", "collab_flow",
    "scenario_grid", "ai_scenario_grid", "painpoint_list", "titled_list",
    "generic_text", "generic_bullet", "generic_kv",
    "tob_journey_l1", "tob_journey_l2",
    "identity_card", "persona_quote_pull", "section_blocks_grid", "section_block",
    "detail_headline", "mockup_list", "detail_analysis", "detail_illust_corner",
    "journey_2c",
    "matrix_guidance_strip", "matrix_2d",
    "distribution_multi",
]

GRID_BODY_TYPES = {
    "resp_rings", "collab_flow",
    "scenario_grid", "ai_scenario_grid", "painpoint_list",
    "titled_list", "generic_text", "generic_bullet", "generic_kv",
}

EXPECTED_FILES = [
    "scripts/components/registry.py",
    "scripts/components/render_report.py",
    "scripts/components/validate.py",
    "scripts/components/renderers/_utils.py",
    "scripts/components/renderers/tob_grid.py",
    "scripts/components/renderers/tob_journey.py",
    "scripts/components/renderers/toc.py",
    "scripts/components/renderers/toc_journey.py",
    "scripts/components/renderers/matrix.py",
    "scripts/components/renderers/distribution.py",
    "scripts/components/layouts/assemble.py",
    "scripts/components/layouts/layout_rules.py",
    "scripts/components/layouts/grid_module.py",
    "scripts/components/layouts/grid_solver.py",
    "scripts/components/layouts/nav.py",
    "scripts/components/tests/gallery_data.json",
    "scripts/components/tests/test_renderers_smoke.py",
    "scripts/components/tests/build_gallery.py",
    "scripts/components/tests/gallery_template.html",
]


def check_files() -> list[str]:
    errors = []
    for rel in EXPECTED_FILES:
        if not (SKILL_ROOT / rel).exists():
            errors.append(f"缺文件: {rel}")
    legacy = [
        "scripts/render_html.py",
        "scripts/components/renderers/shared.py",
        "scripts/components/renderers/toc_portrait.py",
        "scripts/components/renderers/toc_detail.py",
    ]
    for rel in legacy:
        if (SKILL_ROOT / rel).exists():
            errors.append(f"遗留文件应删除: {rel}")
    return errors


def check_registry() -> list[str]:
    errors = []
    reg_path = COMP_ROOT / "registry.py"
    if not reg_path.exists():
        return ["registry.py 不存在,跳过"]
    src = reg_path.read_text(encoding="utf-8")
    for t in ALL_TYPES:
        if f'"{t}"' not in src and f"'{t}'" not in src:
            errors.append(f"registry.py 没注册 type: {t}")
    return errors


def check_renderers_importable() -> list[str]:
    """尝试 import 每个 renderer 函数,看是否能找到"""
    errors = []
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        from components.registry import COMPONENT_REGISTRY  # noqa: WPS433
    except Exception as e:
        return [f"import components.registry 失败: {e}"]

    for t in ALL_TYPES:
        if t not in COMPONENT_REGISTRY:
            errors.append(f"COMPONENT_REGISTRY 缺 {t}")
            continue
        fn = COMPONENT_REGISTRY[t]
        if not callable(fn):
            errors.append(f"{t} 注册的不是可调用对象: {type(fn)}")
    return errors


def check_grid_body_estimators() -> list[str]:
    """10 个 grid body 组件必须有 estimate_rows + min_cols"""
    errors = []
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        from components.renderers import tob_grid
    except Exception as e:
        return [f"import tob_grid 失败: {e}"]

    for t in GRID_BODY_TYPES:
        if not hasattr(tob_grid, f"estimate_rows_{t}"):
            errors.append(f"tob_grid 缺 estimate_rows_{t}")
        if not hasattr(tob_grid, f"min_cols_{t}"):
            errors.append(f"tob_grid 缺 min_cols_{t}")
    return errors


def check_css_additions() -> list[str]:
    css_path = SKILL_ROOT / "assets" / "templates" / "_components.css"
    if not css_path.exists():
        return ["_components.css 不存在"]
    src = css_path.read_text(encoding="utf-8")
    must_have = [
        ".tob-substage-arrow",
        ".matrix-empty-quadrant",
        ".snake-point-level-label",
        ".detail-page-banner",
        ".layout-2b-grid-detail",
        ".section-blocks-grid",
        ".scenario-card.is-ai",
        "P8",  # 段落注释标记
    ]
    errors = []
    for token in must_have:
        if token not in src:
            errors.append(f"_components.css 缺 P8 新样式: {token}")
    return errors


def check_gallery_built() -> list[str]:
    errors = []
    for name in ("gallery-2b.html", "gallery-2c.html"):
        path = SKILL_ROOT / "docs" / "reference" / "gallery" / name
        if not path.exists():
            errors.append(f"gallery 文件未生成: {name}(用户跑 build_gallery.py 后才出)")
    return errors


def run_pytest() -> tuple[int, int, str]:
    """跑 pytest,返回 (pass, fail, summary)"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "scripts/components/tests/", "-v", "--tb=short"],
            cwd=SKILL_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        out = result.stdout + result.stderr
        # 解析 pytest 输出
        import re
        m = re.search(r"(\d+) passed", out)
        passed = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) failed", out)
        failed = int(m.group(1)) if m else 0
        # 取最后 5 行作为摘要
        summary = "\n".join(out.strip().splitlines()[-5:])
        return passed, failed, summary
    except FileNotFoundError:
        return 0, 0, "pytest 未安装,跳过"
    except Exception as e:
        return 0, 0, f"pytest 跑失败: {e}"


def main():
    print("=" * 70)
    print("B 阶段 review:25 个 renderer + grid_solver + gallery + CSS + 测试")
    print(f"目录: {SKILL_ROOT}")
    print("=" * 70)

    sections = [
        ("文件存在性", check_files),
        ("registry 注册完整", check_registry),
        ("renderer 可导入", check_renderers_importable),
        ("grid body 组件有 estimate_rows + min_cols", check_grid_body_estimators),
        ("CSS P8 新样式追加", check_css_additions),
        ("gallery HTML 已生成", check_gallery_built),
    ]

    total_errors = 0
    for label, fn in sections:
        try:
            errs = fn()
        except Exception as e:
            errs = [f"检查异常: {e}"]
        status = "PASS" if not errs else "FAIL"
        print(f"[{status}] {label}")
        for e in errs:
            print(f"     - {e}")
        total_errors += len(errs)

    print("-" * 70)
    print("跑 pytest...")
    p, f, summary = run_pytest()
    pytest_status = "PASS" if f == 0 and p > 0 else "FAIL"
    print(f"[{pytest_status}] pytest: {p} passed, {f} failed")
    print(f"     {summary}")
    if f > 0 or p == 0:
        total_errors += max(f, 1)

    print("=" * 70)
    if total_errors == 0:
        print("[OK] 全部通过!可以告诉主对话进 C 阶段")
        print("    下一步:用户在浏览器双击打开 docs/reference/gallery/gallery-2b.html 和 gallery-2c.html 视觉 review")
        return 0
    else:
        print(f"[X] {total_errors} 个问题,把上面输出复制给 Codex 修复后重跑")
        return 1


if __name__ == "__main__":
    sys.exit(main())
