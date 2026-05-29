"""C 阶段 review 脚本:客观验收 Codex 实现的 8 个 assemble + render_report.py。

用法:
    cd C:/Users/HUAWEI/.claude/skills/user-persona-v8
    python scripts/tools/review_codex_layouts.py

输出:
    [OK] / [FAIL] 标签 + 每条检查的结果 + 末尾汇总。

设计原则:
- 不依赖 Codex 自己写的测试(他可能漏 case 或测错)。
- 直接构造最小合法 / 非法 input 喂 assemble + render_report,断言关键不变量。
- 每条检查独立运行,一条失败不影响后面继续跑。
- 失败时打印具体 input、期望、实际,帮助主对话定位是契约错还是 Codex 错。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # skill 根
SKILL_SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS.parent))  # 让 import scripts.components.* 工作
sys.path.insert(0, str(ROOT))

GOLDEN_DIR = SKILL_SCRIPTS / "components" / "tests" / "golden_samples"


# ============================================================
# 工具函数
# ============================================================

PASS: list[str] = []
FAIL: list[tuple[str, str]] = []


def check(name: str, fn):
    """跑单条检查,捕获所有异常,记录 PASS/FAIL。"""
    try:
        fn()
        PASS.append(name)
        print(f"[OK]   {name}")
    except AssertionError as e:
        FAIL.append((name, f"AssertionError: {e}"))
        print(f"[FAIL] {name}")
        print(f"       └─ {e}")
    except Exception as e:
        tb = traceback.format_exc(limit=3).strip().replace("\n", "\n       ")
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name}")
        print(f"       └─ {type(e).__name__}: {e}")
        print(f"       └─ {tb}")


def base_metadata(theme: str = "2b", density: str = "high", persona_count: int = 1) -> dict:
    return {
        "report_title": "测试报告 — review 脚本",
        "theme": theme,
        "density": density,
        "source_count": 5,
        "persona_count": persona_count,
        "generated_at": "2026-05-25",
    }


# ============================================================
# Section 1: 8 个 assemble 实现存在性
# ============================================================

def check_no_notimplemented():
    """8 个 assemble 不能再抛 NotImplementedError。"""
    from scripts.components.layouts import assemble as A

    fns = [
        ("assemble_layout_2b_grid", A.assemble_layout_2b_grid),
        ("assemble_layout_2b_grid_detail", A.assemble_layout_2b_grid_detail),
        ("assemble_layout_2b_journey", A.assemble_layout_2b_journey),
        ("assemble_layout_2c_portrait", A.assemble_layout_2c_portrait),
        ("assemble_layout_2c_detail", A.assemble_layout_2c_detail),
        ("assemble_layout_2c_journey", A.assemble_layout_2c_journey),
        ("assemble_layout_matrix_2d", A.assemble_layout_matrix_2d),
        ("assemble_layout_distribution_multi", A.assemble_layout_distribution_multi),
    ]
    for name, fn in fns:
        try:
            fn({}, {})
        except NotImplementedError:
            raise AssertionError(f"{name} 仍未实现(抛 NotImplementedError)")
        except Exception:
            pass  # 其它异常是预期的(我们传了空 dict)


# ============================================================
# Section 2: 单元契约 — 每个 layout 的 valid / invalid case
# ============================================================

# --- 真实合法 props 从 B 阶段 gallery_data 取(已经被 schema + renderer 双验) ---

_GALLERY_PATH = SKILL_SCRIPTS / "components" / "tests" / "gallery_data.json"
_GALLERY_DATA = json.loads(_GALLERY_PATH.read_text(encoding="utf-8"))

# 把 type → 第一个合法 props 缓存
_GALLERY_PROPS: dict[str, dict] = {}
for _group in _GALLERY_DATA.values():
    for _item in _group["items"]:
        _GALLERY_PROPS.setdefault(_item["type"], _item["props"])


def _gprops(t: str) -> dict:
    """取 B 阶段验过的合法 props(深拷贝避免污染)。"""
    import copy
    if t not in _GALLERY_PROPS:
        raise KeyError(f"gallery_data 没有 type={t} 的样本,需要补 mock")
    return copy.deepcopy(_GALLERY_PROPS[t])


def _comp(t: str, props: dict | None = None) -> dict:
    return {"type": t, "props": props if props is not None else _gprops(t)}


# --- 8 个 layout 的 valid case 工厂 ---

def _persona_2b_grid_minimal():
    return {
        "id": "persona-1", "name": "测试派", "layout": "layout-2b-grid",
        "components": [
            _comp("identity_panel"),
            _comp("resp_rings"),
            _comp("painpoint_list"),
        ],
    }

def _persona_2b_grid_overflow():
    """7 个 body 组件 + identity_panel,故意触发溢出。"""
    return {
        "id": "persona-1", "name": "溢出派", "layout": "layout-2b-grid",
        "components": [
            _comp("identity_panel"),
            _comp("resp_rings"),
            _comp("collab_flow"),
            _comp("painpoint_list"),
            _comp("painpoint_list"),
            _comp("titled_list"),
            _comp("titled_list"),
            _comp("generic_text"),
        ],
    }

def _persona_2b_grid_detail():
    return {
        "id": "persona-1-detail", "name": "测试派", "layout": "layout-2b-grid-detail",
        "components": [_comp("resp_rings"), _comp("painpoint_list")],
    }

def _persona_2b_journey_l1():
    return {
        "id": "journey-l1", "name": "全景旅程", "layout": "layout-2b-journey",
        "components": [_comp("tob_journey_l1")],
    }

def _persona_2b_journey_l2():
    return {
        "id": "persona-1-journey", "name": "单角色旅程", "layout": "layout-2b-journey",
        "components": [_comp("tob_journey_l2")],
    }

def _persona_2c_portrait():
    return {
        "id": "persona-1", "name": "测试派", "layout": "layout-2c-portrait",
        "accent": "mist-blue",
        "components": [
            _comp("identity_card"),
            _comp("persona_quote_pull"),
            _comp("section_blocks_grid"),
        ],
    }

def _persona_2c_detail():
    return {
        "id": "persona-1-detail", "name": "测试派", "layout": "layout-2c-detail",
        "accent": "mist-blue",
        "components": [
            _comp("detail_headline"),
            _comp("mockup_list"),
            _comp("detail_analysis"),
        ],
    }

def _persona_2c_journey():
    return {
        "id": "persona-1-journey", "name": "测试派", "layout": "layout-2c-journey",
        "accent": "mist-blue",
        "components": [_comp("journey_2c")],
    }

def _persona_matrix():
    return {
        "id": "matrix", "name": "矩阵首页", "layout": "layout-matrix-2d",
        "components": [
            _comp("matrix_guidance_strip"),
            _comp("matrix_2d"),
        ],
    }

def _persona_distribution():
    return {
        "id": "distribution", "name": "分布首页", "layout": "layout-distribution-multi",
        "components": [_comp("distribution_multi")],
    }


# --- 通用 valid 检查模板 ---

def _check_valid_assemble(layout_name, persona_factory, assembler_attr, expected_class_substr, expected_slide_count=1):
    """跑 valid input,断言返回 list[str] + 含期望 class。"""
    from scripts.components.layouts import assemble as A
    fn = getattr(A, assembler_attr)
    persona = persona_factory()
    md = base_metadata(theme="2c" if "2c" in layout_name else "2b")
    result = fn(persona, md)
    assert isinstance(result, list), f"{assembler_attr} 应返回 list,实际 {type(result).__name__}"
    assert len(result) == expected_slide_count, f"{assembler_attr} valid case 应返回 {expected_slide_count} 个 slide,实际 {len(result)}"
    for i, slide in enumerate(result):
        assert isinstance(slide, str), f"{assembler_attr} 返回的第 {i} 个 slide 应是 str"
        assert expected_class_substr in slide, f"{assembler_attr} 第 {i} 个 slide 应含 class {expected_class_substr!r}"


def _check_invalid_assemble(layout_name, assembler_attr, persona_factory_or_dict, expect_msg_substr=None):
    """跑 invalid input,断言抛 ValueError。"""
    from scripts.components.layouts import assemble as A
    fn = getattr(A, assembler_attr)
    persona = persona_factory_or_dict() if callable(persona_factory_or_dict) else persona_factory_or_dict
    md = base_metadata()
    try:
        fn(persona, md)
    except ValueError as e:
        msg = str(e)
        assert layout_name in msg.lower() or layout_name.replace("-", "_") in msg.lower(), \
            f"ValueError 消息应含 layout 名 {layout_name!r},实际 {msg!r}"
        if expect_msg_substr:
            assert expect_msg_substr in msg, f"ValueError 消息应含 {expect_msg_substr!r},实际 {msg!r}"
        return
    raise AssertionError(f"{assembler_attr} 应抛 ValueError 但没抛")


# --- 具体 layout 的 check 函数(批量调度) ---

LAYOUT_CASES = [
    # (layout_name, assembler_attr, valid_factory, class_substr, slide_count, invalid_cases)
    ("layout-2b-grid", "assemble_layout_2b_grid", _persona_2b_grid_minimal, "layout-2b-grid", 1),
    ("layout-2b-grid-detail", "assemble_layout_2b_grid_detail", _persona_2b_grid_detail, "layout-2b-grid-detail", 1),
    ("layout-2b-journey", "assemble_layout_2b_journey", _persona_2b_journey_l1, "is-l1", 1),
    ("layout-2c-portrait", "assemble_layout_2c_portrait", _persona_2c_portrait, "layout-2c-portrait", 1),
    ("layout-2c-detail", "assemble_layout_2c_detail", _persona_2c_detail, "layout-2c-detail", 1),
    ("layout-2c-journey", "assemble_layout_2c_journey", _persona_2c_journey, "layout-2c-journey", 1),
    ("layout-matrix-2d", "assemble_layout_matrix_2d", _persona_matrix, "layout-matrix-2d", 1),
    ("layout-distribution-multi", "assemble_layout_distribution_multi", _persona_distribution, "layout-distribution-multi", 1),
]


def check_valid_inputs():
    """逐个 layout 跑 valid case。"""
    for layout_name, attr, factory, class_substr, n in LAYOUT_CASES:
        check(
            f"{layout_name} valid 输入返回 {n} 个 slide 含 {class_substr!r}",
            lambda layout_name=layout_name, attr=attr, factory=factory, class_substr=class_substr, n=n:
                _check_valid_assemble(layout_name, factory, attr, class_substr, n)
        )


def check_missing_required():
    """缺必需 type 抛 ValueError。"""
    # 2b-grid 删 identity_panel
    def case_2b_grid():
        p = _persona_2b_grid_minimal()
        p["components"] = [c for c in p["components"] if c["type"] != "identity_panel"]
        return p
    check("layout-2b-grid 缺 identity_panel 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2b-grid", "assemble_layout_2b_grid", case_2b_grid))

    # 2c-portrait 删 identity_card
    def case_2c_portrait():
        p = _persona_2c_portrait()
        p["components"] = [c for c in p["components"] if c["type"] != "identity_card"]
        return p
    check("layout-2c-portrait 缺 identity_card 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2c-portrait", "assemble_layout_2c_portrait", case_2c_portrait))

    # 2c-detail 删 detail_headline
    def case_2c_detail():
        p = _persona_2c_detail()
        p["components"] = [c for c in p["components"] if c["type"] != "detail_headline"]
        return p
    check("layout-2c-detail 缺 detail_headline 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2c-detail", "assemble_layout_2c_detail", case_2c_detail))

    # matrix 删 matrix_2d
    def case_matrix():
        p = _persona_matrix()
        p["components"] = [c for c in p["components"] if c["type"] != "matrix_2d"]
        return p
    check("layout-matrix-2d 缺 matrix_2d 抛 ValueError",
          lambda: _check_invalid_assemble("layout-matrix-2d", "assemble_layout_matrix_2d", case_matrix))


def check_illegal_type():
    """塞不允许的 type 抛 ValueError。"""
    # 2c-portrait 塞 painpoint_list(2B 的 type)
    def case():
        p = _persona_2c_portrait()
        p["components"].append(_comp("painpoint_list"))
        return p
    check("layout-2c-portrait 塞 painpoint_list 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2c-portrait", "assemble_layout_2c_portrait", case))

    # 2b-journey 塞 identity_panel
    def case2():
        p = _persona_2b_journey_l1()
        p["components"].append(_comp("identity_panel"))
        return p
    check("layout-2b-journey 塞 identity_panel 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2b-journey", "assemble_layout_2b_journey", case2))


def check_2c_accent_required():
    """2C 主题缺 accent 必报错或注入默认值前置(契约要求必填)。"""
    def case():
        p = _persona_2c_portrait()
        del p["accent"]
        return p
    check("layout-2c-portrait 缺 accent 抛 ValueError",
          lambda: _check_invalid_assemble("layout-2c-portrait", "assemble_layout_2c_portrait", case))


def check_2c_accent_inline_present():
    """2C 主题 valid 输入的 HTML 必须含 --color-accent: var(--accent-XXX)。"""
    from scripts.components.layouts import assemble as A
    p = _persona_2c_portrait()
    result = A.assemble_layout_2c_portrait(p, base_metadata(theme="2c"))
    html = result[0]
    assert "--color-accent" in html, f"2c-portrait HTML 应含 --color-accent, 实际:\n{html[:300]}"
    assert "--accent-mist-blue" in html, f"2c-portrait HTML 应含 --accent-mist-blue, 实际:\n{html[:300]}"


def check_2b_grid_dual_page():
    """2b-grid 溢出时返回 2 个 slide + metadata 标 mid。"""
    from scripts.components.layouts import assemble as A
    p = _persona_2b_grid_overflow()
    md = base_metadata()
    result = A.assemble_layout_2b_grid(p, md)
    assert len(result) == 2, f"溢出应返回 2 个 slide, 实际 {len(result)}"
    assert "layout-2b-grid-detail" in result[1], f"第 2 个 slide 应是 layout-2b-grid-detail, 实际:\n{result[1][:300]}"
    assert md.get("_internal_density_override") == "mid", \
        f"溢出应在 metadata 设置 _internal_density_override=mid, 实际:{md.get('_internal_density_override')}"


def check_grid_solver_split_no_hardcoded_3():
    """检查 grid_solver._dual_page_split 实现层不再硬编码 components[:3](注释里出现 OK)。"""
    import inspect
    from scripts.components.layouts import grid_solver
    src = inspect.getsource(grid_solver._dual_page_split)
    # 把注释/docstring 全部剥掉,只看可执行代码
    code_only = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
    code_only = re.sub(r"^\s*#.*$", "", code_only, flags=re.MULTILINE)
    assert "components[:3]" not in code_only, \
        "grid_solver._dual_page_split 实现仍硬编码 components[:3],需按 row 估算切分"


# ============================================================
# Section 3: render_report.py 端到端
# ============================================================

def _wrap_persona(persona_dict, theme="2b", density="high"):
    return {
        "metadata": base_metadata(theme=theme, density=density),
        "personas": [persona_dict],
    }


def _run_render(input_json: dict) -> tuple[str, Path]:
    """跑 render_report,返回 (html_str, output_dir)。"""
    from scripts.components.render_report import render_report

    tmp = Path(tempfile.mkdtemp(prefix="c-review-"))
    out_path = tmp / "report.html"
    html = render_report(input_json, tmp)
    if not out_path.exists():
        out_path.write_text(html, encoding="utf-8")
    return html, tmp


def check_render_report_module_exists():
    """render_report.py 模块存在,可 import。"""
    try:
        from scripts.components import render_report as rr
        assert hasattr(rr, "render_report"), "render_report 模块应导出 render_report 函数"
    except ImportError as e:
        raise AssertionError(f"render_report.py 无法 import: {e}")


def check_render_single_2c_portrait():
    """单画像 2c-portrait 端到端,输出含期望 class、无 nav。"""
    p = _persona_2c_portrait()
    html, _ = _run_render(_wrap_persona(p, theme="2c", density="low"))
    assert 'class="persona-slide active layout-2c-portrait"' in html or 'persona-slide active' in html, \
        "首个 slide 应有 .active class"
    assert "layout-2c-portrait" in html
    assert "demo-nav-area" not in html, "单画像不应渲染 nav"


def check_render_multi_persona_nav():
    """多画像应渲染 nav。"""
    p1 = _persona_2c_portrait()
    p1["id"] = "persona-1"
    p2 = _persona_2c_portrait()
    p2["id"] = "persona-2"
    p2["name"] = "测试派2"
    p2["accent"] = "moss-green"
    input_json = {
        "metadata": base_metadata(theme="2c", density="low", persona_count=2),
        "personas": [p1, p2],
    }
    html, _ = _run_render(input_json)
    assert "persona-slide" in html
    # 检查 nav 渲染:可能是 .demo-nav-area 容器或 .nav-btn
    assert "nav-btn" in html or "demo-nav-area" in html, "多画像应渲染 nav"


def check_render_nav_pair_journey():
    """persona-1 + persona-1-journey 应配对为 pair。"""
    p1 = _persona_2c_portrait()
    p1["id"] = "persona-1"
    p2 = _persona_2c_journey()
    p2["id"] = "persona-1-journey"
    input_json = {
        "metadata": base_metadata(theme="2c", density="low", persona_count=2),
        "personas": [p1, p2],
    }
    html, _ = _run_render(input_json)
    assert "nav-pair" in html, "persona-N + persona-N-journey 应配对成 .nav-pair"


def check_render_dual_page_density():
    """触发 2b-grid 双页,最终 HTML 的 data-density 应为 mid。"""
    p = _persona_2b_grid_overflow()
    input_json = _wrap_persona(p, theme="2b", density="high")
    html, _ = _run_render(input_json)
    assert 'data-density="mid"' in html, \
        f"双页应把 data-density 切到 mid, 实际:{[l for l in html.split() if 'data-density' in l][:3]}"
    # 应该有 2 个 slide(原画像 + detail)
    slide_count = html.count('class="persona-slide')
    assert slide_count >= 2, f"双页应输出 ≥2 个 slide,实际 {slide_count}"


def check_render_css_copy():
    """输出目录应含 _design-tokens.css + _components.css。"""
    p = _persona_2c_portrait()
    _, out_dir = _run_render(_wrap_persona(p, theme="2c", density="low"))
    assert (out_dir / "_design-tokens.css").exists(), "_design-tokens.css 未随包"
    assert (out_dir / "_components.css").exists(), "_components.css 未随包"


def check_render_slots_filled():
    """所有 {{XXX}} slot 必须被填,残留 slot = bug。"""
    p = _persona_2c_portrait()
    html, _ = _run_render(_wrap_persona(p, theme="2c", density="low"))
    import re
    leftover = re.findall(r"\{\{[^}]+\}\}", html)
    assert not leftover, f"HTML 含未填充 slot: {leftover}"


def check_render_first_slide_active():
    """多画像时,首个 slide 必须 .active,其它不能 .active。"""
    p1 = _persona_2c_portrait()
    p1["id"] = "persona-1"
    p2 = _persona_2c_portrait()
    p2["id"] = "persona-2"
    p2["name"] = "测试派 2"
    p2["accent"] = "warm-orange"
    input_json = {
        "metadata": base_metadata(theme="2c", density="low", persona_count=2),
        "personas": [p1, p2],
    }
    html, _ = _run_render(input_json)
    active_count = html.count("persona-slide active")
    assert active_count == 1, f"多画像时 .active 应恰好 1 个,实际 {active_count}"


# ============================================================
# Section 4: golden samples 端到端(B 阶段 6 份)
# ============================================================

def check_validator_importable():
    from scripts.components.validate import validate_report_json  # noqa
    from scripts.components.validate import format_issues_for_human  # noqa


def _legal_report() -> dict:
    p1 = _persona_2c_portrait()
    p1["id"] = "persona-1"
    p2 = _persona_2c_portrait()
    p2["id"] = "persona-2"
    p2["accent"] = "warm-orange"
    return {"metadata": base_metadata(theme="2c", density="low", persona_count=2),
            "personas": [p1, p2]}


def check_validator_legal_passes():
    from scripts.components.validate import validate_report_json
    issues = validate_report_json(_legal_report())
    errors = [i for i in issues if i["level"] == "ERROR"]
    assert not errors, f"合法 input 应通过,实际 {len(errors)} 个 ERROR: {errors[:3]}"


def check_validator_illegal_blocked():
    """3 个 block 的 section_blocks_grid 应被 oneOf 拦截。"""
    from scripts.components.validate import validate_report_json
    report = _legal_report()
    # 把 persona-1 的 section_blocks_grid 凑成 3 个 block
    sbg = next(c for c in report["personas"][0]["components"] if c["type"] == "section_blocks_grid")
    import copy
    sbg["props"]["blocks"] = [copy.deepcopy(sbg["props"]["blocks"][0]) for _ in range(3)]

    issues = validate_report_json(report)
    errors = [i for i in issues if i["level"] == "ERROR"]
    assert errors, "3 个 block 的 section_blocks_grid 应被拦截"
    # 错误应定位到具体 path
    paths = [e["path"] for e in errors]
    assert any("section_blocks_grid" in e.get("message", "") or "blocks" in p
               for e, p in zip(errors, paths)), \
        f"错误应定位到 section_blocks_grid.blocks,实际 paths: {paths[:3]}"


def check_validator_render_raises():
    """render_report 收到非法 input 应抛 ValueError(经事前校验)。"""
    from scripts.components.render_report import render_report
    report = _legal_report()
    sbg = next(c for c in report["personas"][0]["components"] if c["type"] == "section_blocks_grid")
    import copy
    sbg["props"]["blocks"] = [copy.deepcopy(sbg["props"]["blocks"][0]) for _ in range(3)]

    tmp = Path(tempfile.mkdtemp(prefix="c-review-bad-"))
    try:
        render_report(report, tmp, validate=True)
    except ValueError as e:
        msg = str(e)
        assert "校验失败" in msg or "ERROR" in msg, f"ValueError 消息应含校验失败提示,实际: {msg[:200]}"
        return
    raise AssertionError("非法 input 应被 render_report 抛 ValueError 拦截")


def check_validate_html_zero_errors_toc():
    """根因检查:跑 toC 多画像 render_report 后,validate_html 必须 0 ERROR。

    这条防"渲染过但 P7 体检 N 个 ERROR"假绿。Codex review 2026-05-25 发现此问题。
    """
    _assert_zero_errors_on_render(_build_toc_multi_input(), "toC 多画像")


def check_validate_html_zero_errors_tob():
    """toB layout-2b-grid 端到端,涉及 collab_flow / resp_rings / painpoint_list 等所有 body 组件。"""
    _assert_zero_errors_on_render(_build_tob_full_input(), "toB 全组件")


def check_validate_html_zero_errors_dual_page():
    """触发 2b-grid 双页拆分,体检应能识别 layout-2b-grid-detail(白名单要含)。"""
    p = _persona_2b_grid_overflow()
    input_json = _wrap_persona(p, theme="2b", density="high")
    _assert_zero_errors_on_render(input_json, "2b-grid 双页")


def _build_toc_multi_input() -> dict:
    p1 = _persona_2c_portrait()
    p1["id"] = "persona-1"
    p2 = _persona_2c_journey()
    p2["id"] = "persona-1-journey"
    return {"metadata": base_metadata(theme="2c", density="low", persona_count=2),
            "personas": [p1, p2]}


def _build_tob_full_input() -> dict:
    p = {
        "id": "persona-1", "name": "调度员", "layout": "layout-2b-grid",
        "components": [
            _comp("identity_panel"),
            _comp("resp_rings"),
            _comp("collab_flow"),
            _comp("titled_list"),
            _comp("painpoint_list"),
        ],
    }
    return {"metadata": base_metadata(theme="2b", density="high", persona_count=1),
            "personas": [p]}


def check_render_report_raises_on_html_error():
    """根因防回归(Codex review 2026-05-25 P1):
    如果 validate_html 跑出 ERROR,render_report 必须 raise,不能只 WARN。

    构造方法:在 tmp 目录预写一个故意带 banned label 的 HTML 作为对照,
    然后跑 render_report 用一个合法 input,但插桩让 validate_html 找到一个会失败的产物。

    更稳妥的策略:直接 monkey-patch validate_html 的 subprocess 行为不可行(开销大)。
    退而求其次:验证 _try_html_validate 在 retcode != 0 时确实 raise RuntimeError。
    """
    from scripts.components.render_report import _try_html_validate
    import tempfile
    # 写一个故意带 P7 banned label 的 HTML 到 tmp,直接喂给 _try_html_validate
    tmp = Path(tempfile.mkdtemp(prefix="c-review-htmlraise-"))
    bad_html = tmp / "bad.html"
    bad_html.write_text(
        '<!DOCTYPE html><html data-theme="2b" data-density="high"><body>'
        '<section class="persona-slide active layout-2b-grid" id="persona-1">'
        '<div class="collab-flow">'
        '<div class="flow-cell"><div class="flow-cell-label">上游</div><div class="flow-cell-value">x</div></div>'
        '</div></section></body></html>',
        encoding="utf-8",
    )
    try:
        _try_html_validate(bad_html)
    except RuntimeError as e:
        assert "validate_html 体检失败" in str(e), f"RuntimeError 消息应说明体检失败,实际:{e}"
        return
    raise AssertionError("带 banned label 的 HTML 应触发 _try_html_validate raise RuntimeError")


def _assert_zero_errors_on_render(input_json: dict, case_label: str):
    """跑 render_report → validate_html(subprocess) → 断言 0 ERROR(WARNING 不阻塞)。"""
    from scripts.components.render_report import render_report
    import subprocess
    tmp = Path(tempfile.mkdtemp(prefix="c-review-html-"))
    html_path = tmp / "report.html"
    render_report(input_json, tmp, validate=False)  # 关掉顶层 validate_html(我们这里手动跑拿结构化结果)

    result = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "validate_html.py"), str(html_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    err_lines = [l for l in (result.stdout or "").splitlines() if l.startswith("[ERROR]")]
    if err_lines:
        head = "\n".join(err_lines[:8])
        raise AssertionError(
            f"{case_label}: validate_html 发现 {len(err_lines)} 个 ERROR,首 8 条:\n{head}"
        )


def check_golden_samples_render():
    """B 阶段 6 个 golden samples 至少能被 render_report 直接吃下去(若 sample 本身就是完整 report.json),
    否则用对应单组件 wrap 成 report.json 再喂。"""
    samples = [f.name for f in GOLDEN_DIR.glob("*.json")]
    assert len(samples) >= 6, f"golden_samples 目录应有 ≥6 个 JSON,实际 {len(samples)}"

    # 这里只做存在性检查;实际渲染端到端由上面 check_render_* 覆盖。
    # 因为 golden samples 是单组件 props 级别,不是完整 report.json。


# ============================================================
# 主入口
# ============================================================

def main():
    print("=" * 70)
    print("C 阶段 review — Codex 实现验收")
    print("=" * 70)

    print("\n--- 1. assemble 函数实现存在性 ---")
    check("8 个 assemble 不再抛 NotImplementedError", check_no_notimplemented)
    check("grid_solver._dual_page_split 不再硬编码 components[:3]",
          check_grid_solver_split_no_hardcoded_3)

    print("\n--- 2. 每个 layout valid 输入返回正确 slide ---")
    check_valid_inputs()

    print("\n--- 3. 缺必需组件抛 ValueError ---")
    check_missing_required()

    print("\n--- 4. 不允许的 type 抛 ValueError ---")
    check_illegal_type()

    print("\n--- 5. 2C accent 注入 ---")
    check("layout-2c-portrait 缺 accent 抛 ValueError", check_2c_accent_required)
    check("layout-2c-portrait HTML 含 --color-accent 与 --accent-mist-blue",
          check_2c_accent_inline_present)

    print("\n--- 6. 2b-grid 双页机制 ---")
    check("layout-2b-grid 溢出返回 2 slide + metadata 切 mid", check_2b_grid_dual_page)

    print("\n--- 7. render_report.py 端到端 ---")
    check("render_report 模块可 import", check_render_report_module_exists)
    check("单画像 2c-portrait 端到端 + 无 nav", check_render_single_2c_portrait)
    check("多画像端到端 + 含 nav", check_render_multi_persona_nav)
    check("persona-1 + persona-1-journey 配对成 nav-pair", check_render_nav_pair_journey)
    check("2b-grid 溢出后最终 HTML data-density=mid", check_render_dual_page_density)
    check("输出目录含 _design-tokens.css + _components.css", check_render_css_copy)
    check("无残留 {{slot}}", check_render_slots_filled)
    check("多画像时首个 slide 唯一 .active", check_render_first_slide_active)

    print("\n--- 8. golden samples 数量 ---")
    check("golden_samples 目录有 ≥6 份", check_golden_samples_render)

    print("\n--- 9. 事前 schema 校验(F 阶段) ---")
    check("validate_components_json 可 import", check_validator_importable)
    check("合法 input 通过校验", check_validator_legal_passes)
    check("非法 input(3 个 block)被拦截", check_validator_illegal_blocked)
    check("非法 input 触发 render_report 抛 ValueError", check_validator_render_raises)

    print("\n--- 10. 端到端 HTML 体检(P7 validate_html 0 ERROR)---")
    check("toC 多画像 render → validate_html 0 ERROR", check_validate_html_zero_errors_toc)
    check("toB 全组件 render → validate_html 0 ERROR", check_validate_html_zero_errors_tob)
    check("2b-grid 双页 render → validate_html 0 ERROR", check_validate_html_zero_errors_dual_page)
    check("render_report 体检 ERROR 时必须 raise(--skip-validate 才放行)",
          check_render_report_raises_on_html_error)

    # 汇总
    print("\n" + "=" * 70)
    print(f"汇总: {len(PASS)} PASS / {len(FAIL)} FAIL")
    print("=" * 70)
    if FAIL:
        print("\nFAIL 详情:")
        for name, msg in FAIL:
            print(f"  [{name}]")
            print(f"     {msg}")
        sys.exit(1)
    else:
        print("[ALL PASS] C 阶段实现验收通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
