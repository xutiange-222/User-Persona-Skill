# Layout Assemble 契约表(C 阶段)

> 主对话产物。C 阶段实现的 8 个 `assemble_*` 函数,**严格按本表的「必需 / 允许 / 数量 / 顺序」校验输入**。
> 校验不过 → 抛 `ValueError` 含 layout 名 + 具体缺失/多余/数量错信息。
> 校验通过 → 按拼装策略包外壳并组合内部组件 HTML,返回 `list[str]`(长度 1,layout-2b-grid 触发双页时长度 2)。

---

## 0. 公共约定

### 0.1 assemble 函数签名(8 个函数统一)

```python
def assemble_layout_XXX(persona: dict, metadata: dict) -> list[str]:
    """
    返回 list[str](长度 1 或 2)。

    persona: {id, name, layout, accent?, subtitle_for_nav?, components}
    metadata: 顶层 metadata dict(用来读 theme/density 等)

    返回 list:
      - 一般 layout 返回 [single_slide_html]
      - layout-2b-grid 触发双页时,返回 [first_slide_html, second_slide_html]
        第二个 slide 的 class 是 "persona-slide layout-2b-grid-detail"
        第二个 slide 的 id 是 "{原 id}-detail"(若原 id 已是 -core,改 -detail;否则追加 -detail)

    校验失败:抛 ValueError(f"layout-XXX: <具体说明>")
    """
```

**关键**:assemble 永远返回 list,不返回 str。顶层 `render_report.py` 把所有 slide flatten 后拼到 `{{main_content}}`。

### 0.2 校验通用模式(每个 assemble 开头都跑)

```python
components = persona["components"]
actual_types = [c["type"] for c in components]
type_counter = Counter(actual_types)

# 1. 必需 type 全部存在
missing = REQUIRED_TYPES - set(actual_types)
if missing:
    raise ValueError(f"layout-XXX 缺少必需组件: {sorted(missing)}")

# 2. 不允许的 type 不能出现
illegal = set(actual_types) - ALLOWED_TYPES
if illegal:
    raise ValueError(f"layout-XXX 不允许的组件: {sorted(illegal)}")

# 3. 数量约束(各 type 出现次数)
for t, (lo, hi) in COUNT_RANGES.items():
    if not (lo <= type_counter.get(t, 0) <= hi):
        raise ValueError(f"layout-XXX 组件 {t} 数量必须在 [{lo}, {hi}], 实际 {type_counter.get(t, 0)}")

# 4. (可选)顺序检查 — 用 REQUIRED_ORDER 列表存「必须按这个顺序出现」的 type 序列
```

### 0.3 accent 注入

- 2C 主题(layout-2c-portrait / layout-2c-detail / layout-2c-journey):必读 `persona["accent"]`,渲染 `style="--color-accent: var(--accent-{accent})"`。缺失抛 ValueError。
- 2B/2D 主题(layout-2b-grid / layout-2b-grid-detail / layout-2b-journey):忽略 accent,不渲染 inline style。
- matrix-2d / distribution-multi:不渲染 accent inline(综合页,各象限/各画像有自己的 accent 在子 slide)。

### 0.4 HTML 转义

所有 LLM 文本走 `from html import escape`,attr 用 `escape(s, quote=True)`。已在 `_utils.py`。assemble 包外壳时:`persona["id"]` `persona["name"]` 都要 escape。

---

## 1. layout-2b-grid(toB/toD 单画像,可能拆双页)

| 字段 | 值 |
|---|---|
| **必需 type** | `identity_panel`(恰好 1 个) |
| **允许 type** | `identity_panel`, `resp_rings`, `collab_flow`, `scenario_grid`, `ai_scenario_grid`, `painpoint_list`, `titled_list`, `generic_text`, `generic_bullet`, `generic_kv` |
| **数量约束** | `identity_panel`: 1..1;其它 body 组件:各 0..3;body 组件总数:1..10 |
| **顺序约束** | `identity_panel` 必须 LLM 给的第一个;后续 body 组件按 LLM 顺序作为「优先级」喂给 grid_solver |
| **accent** | 不渲染 inline(2B 主题) |
| **slide id** | `persona["id"]`(LLM 给的) |
| **slide class** | `persona-slide layout-2b-grid` |

### 拼装策略

```python
def assemble_layout_2b_grid(persona, metadata):
    校验通过后:
    body_components = [c for c in components if c["type"] != "identity_panel"]
    identity = next(c for c in components if c["type"] == "identity_panel")

    placements, overflow = solve_grid(body_components, RENDERER_REGISTRY)

    identity_html = render_component(identity)  # 走 registry

    if not overflow:
        # 单页
        body_html = render_grid_placements(placements, page=1)
        slide = f'''
        <section class="persona-slide layout-2b-grid" id="{esc(pid)}">
          <div class="identity-panel">{identity_html}</div>
          <div class="modules-panel">{body_html}</div>
        </section>
        '''
        return [slide]
    else:
        # 双页
        page1_placements = [p for p in placements if p.page == 1]
        page2_placements = [p for p in placements if p.page == 2]
        page1_body = render_grid_placements(page1_placements, page=1)
        page2_body = render_grid_placements(page2_placements, page=2)

        slide1 = f'''
        <section class="persona-slide layout-2b-grid" id="{esc(pid)}-core">
          <div class="identity-panel">{identity_html}</div>
          <div class="modules-panel">{page1_body}</div>
        </section>
        '''
        slide2 = f'''
        <section class="persona-slide layout-2b-grid-detail" id="{esc(pid)}-detail">
          <div class="detail-page-banner">{esc(persona["name"])} · 工作细节</div>
          <div class="modules-panel detail-modules">{page2_body}</div>
        </section>
        '''
        # 通过 metadata 副作用回传"本报告需要切 density=mid"信号
        metadata["_internal_density_override"] = "mid"
        return [slide1, slide2]
```

### render_grid_placements 辅助(放 assemble.py 内)

```python
def render_grid_placements(placements, page: int) -> str:
    """把 GridPlacement 列表渲染为 .grid-module 序列(grid-column inline 标注位置)"""
    parts = []
    for p in placements:
        inner = render_component({"type": p.component_type, "props": p.component_props})
        parts.append(
            f'<div class="grid-module grid-module-{p.component_type.replace("_", "-")}" '
            f'style="grid-column: {p.col_start} / span {p.col_span};">'
            f'{inner}</div>'
        )
    return "".join(parts)
```

> **注**:`grid-row` 不写 inline,让 CSS grid 自然流式排列;solver 只保证「同行宽度=12」,行高交给 `align-content: space-evenly`。

### 双页规则(关键)

- **触发**:`solve_grid()` 返回 `overflow=True`
- **第一页**:放 grid_solver 算出 page=1 的所有 placement
- **第二页**:放 page=2 的所有 placement
- **density 切换**:在 `metadata` 里写入 `_internal_density_override = "mid"`,由 render_report.py 在填 `{{density}}` slot 时优先用这个值
- **id 命名规则**:
  - 原 id 不含后缀 → 第一页 `{id}-core`,第二页 `{id}-detail`
  - 原 id 已是 `persona-N` → 第一页 `persona-N-core`,第二页 `persona-N-detail`
- **nav 配对**:由 render_report.py 顶层算,assemble 不管

---

## 2. layout-2b-grid-detail(双页第二页,LLM 不直接选)

| 字段 | 值 |
|---|---|
| **必需 type** | 无(允许 body 组件任意子集) |
| **允许 type** | 同 2b-grid 但**去掉 identity_panel** |
| **数量约束** | body 组件总数:1..10;`identity_panel`:必须 0 个 |
| **顺序约束** | LLM 顺序作为 grid_solver 优先级 |
| **accent** | 不渲染 |
| **slide id** | `persona["id"]`(LLM 给的) |
| **slide class** | `persona-slide layout-2b-grid-detail` |

### 拼装策略

```python
def assemble_layout_2b_grid_detail(persona, metadata):
    校验通过后:
    placements, overflow = solve_grid(components, RENDERER_REGISTRY)  # 无 max_rows 限制
    if overflow:
        raise ValueError("layout-2b-grid-detail 不允许再溢出")

    body_html = render_grid_placements(placements, page=1)
    slide = f'''
    <section class="persona-slide layout-2b-grid-detail" id="{esc(pid)}">
      <div class="detail-page-banner">{esc(persona["name"])} · 工作细节</div>
      <div class="modules-panel detail-modules">{body_html}</div>
    </section>
    '''
    return [slide]
```

**注**:这个 layout 路径理论上**只在 LLM 显式指定时走**(罕见,通常由 2b-grid 自动拆双页生成)。LLM 显式指定也允许,因为字段对齐阶段可能用户已经决定第二页内容。

---

## 3. layout-2b-journey(toB/toD 旅程,二选一)

| 字段 | 值 |
|---|---|
| **必需 type** | `tob_journey_l1` OR `tob_journey_l2`(二选一,恰好 1 个) |
| **允许 type** | `tob_journey_l1`, `tob_journey_l2` |
| **数量约束** | `tob_journey_l1` + `tob_journey_l2` 合计 == 1 |
| **顺序约束** | 不适用(只有 1 个组件) |
| **accent** | 不渲染(2B 主题) |
| **slide id** | `persona["id"]`(LLM 给的,通常 `journey-l1` 或 `persona-N-journey`) |
| **slide class** | `persona-slide layout-2b-journey is-l1`(若 l1)/ `is-l2`(若 l2) |

### 拼装策略

```python
def assemble_layout_2b_journey(persona, metadata):
    校验通过后:
    comp = components[0]
    modifier = "is-l1" if comp["type"] == "tob_journey_l1" else "is-l2"
    inner = render_component(comp)
    slide = f'''
    <section class="persona-slide layout-2b-journey {modifier}" id="{esc(pid)}">
      {inner}
    </section>
    '''
    return [slide]
```

### L2 hybrid 行序(有 `focuses` 时)

Rail / Main 自上而下对齐:

1. 阶段
2. 子阶段
3. **工具/触点**(`tools_touchpoints`,可选;缺省仍渲染空行)
4. 工作流程(UML)
5. 关注点 / 痛点

---

## 4. layout-2c-portrait(toC 单画像主页)

| 字段 | 值 |
|---|---|
| **必需 type** | `identity_card`, `persona_quote_pull`, `section_blocks_grid`(三者各 1) |
| **允许 type** | 同上 3 个,无其它 |
| **数量约束** | 三者各 1..1 |
| **顺序约束** | **固定:identity_card → persona_quote_pull → section_blocks_grid**(LLM 顺序任意,assemble 重排) |
| **accent** | 必填,渲染 inline `style="--color-accent: var(--accent-{accent})"` |
| **slide id** | `persona["id"]` |
| **slide class** | `persona-slide layout-2c-portrait` |

### 拼装策略

```python
def assemble_layout_2c_portrait(persona, metadata):
    校验通过后,按固定 type 顺序取组件:
    type_to_comp = {c["type"]: c for c in components}
    identity_html = render_component(type_to_comp["identity_card"])
    quote_html    = render_component(type_to_comp["persona_quote_pull"])
    grid_html     = render_component(type_to_comp["section_blocks_grid"])

    accent_style = f'style="--color-accent: var(--accent-{esc_attr(accent)});"'
    slide = f'''
    <section class="persona-slide layout-2c-portrait" id="{esc(pid)}" {accent_style}>
      {identity_html}
      {quote_html}
      {grid_html}
    </section>
    '''
    return [slide]
```

---

## 5. layout-2c-detail(toC 专题详情)

| 字段 | 值 |
|---|---|
| **必需 type** | `detail_headline`, `mockup_list`, `detail_analysis`(三者各 1) |
| **允许 type** | 上述 3 个 + `detail_illust_corner`(0..1) + `persona_quote_pull`(0..1) |
| **数量约束** | headline 1..1, mockup_list 1..1, detail_analysis 1..1, illust_corner 0..1, quote_pull 0..1 |
| **顺序约束** | **固定**:headline → quote_pull(若有,headline 下方) → (mockup_list + analysis 并列 in `.l2c-body`) → illust_corner(若有,position:absolute 角落) |
| **accent** | 必填(同 2c-portrait) |
| **slide id** | `persona["id"]` |
| **slide class** | `persona-slide layout-2c-detail` |

### 拼装策略

```python
def assemble_layout_2c_detail(persona, metadata):
    校验通过后:
    type_to_comp = {c["type"]: c for c in components}
    headline_html = render_component(type_to_comp["detail_headline"])
    mockup_html   = render_component(type_to_comp["mockup_list"])
    analysis_html = render_component(type_to_comp["detail_analysis"])
    quote_html    = render_component(type_to_comp["persona_quote_pull"]) if "persona_quote_pull" in type_to_comp else ""
    illust_html   = render_component(type_to_comp["detail_illust_corner"]) if "detail_illust_corner" in type_to_comp else ""

    accent_style = f'style="--color-accent: var(--accent-{esc_attr(accent)});"'
    slide = f'''
    <section class="persona-slide layout-2c-detail" id="{esc(pid)}" {accent_style}>
      {headline_html}
      {quote_html}
      <div class="l2c-body">
        {mockup_html}
        {analysis_html}
      </div>
      {illust_html}
    </section>
    '''
    return [slide]
```

---

## 6. layout-2c-journey(toC 旅程)

| 字段 | 值 |
|---|---|
| **必需 type** | `journey_2c`(恰好 1 个) |
| **允许 type** | `journey_2c` |
| **数量约束** | 1..1 |
| **顺序约束** | 不适用 |
| **accent** | 必填(2C 主题) |
| **slide id** | `persona["id"]` |
| **slide class** | `persona-slide layout-2c-journey` |

### 拼装策略

```python
def assemble_layout_2c_journey(persona, metadata):
    校验通过后:
    inner = render_component(components[0])
    accent_style = f'style="--color-accent: var(--accent-{esc_attr(accent)});"'
    slide = f'''
    <section class="persona-slide layout-2c-journey" id="{esc(pid)}" {accent_style}>
      {inner}
    </section>
    '''
    return [slide]
```

---

## 7. layout-matrix-2d(R4 2D 矩阵首页)

| 字段 | 值 |
|---|---|
| **必需 type** | `matrix_guidance_strip`, `matrix_2d`(各 1) |
| **允许 type** | 上述 2 个 |
| **数量约束** | guidance_strip 1..1, matrix_2d 1..1 |
| **顺序约束** | **固定**:guidance_strip → matrix_2d |
| **accent** | 不渲染(综合首页) |
| **slide id** | `persona["id"]`(通常 `matrix`) |
| **slide class** | `persona-slide layout-matrix-2d` |

### 拼装策略

```python
def assemble_layout_matrix_2d(persona, metadata):
    校验通过后,按 type 顺序取组件:
    type_to_comp = {c["type"]: c for c in components}
    strip_html  = render_component(type_to_comp["matrix_guidance_strip"])
    matrix_html = render_component(type_to_comp["matrix_2d"])

    slide = f'''
    <section class="persona-slide layout-matrix-2d" id="{esc(pid)}">
      {strip_html}
      {matrix_html}
    </section>
    '''
    return [slide]
```

---

## 8. layout-distribution-multi(R5 多维分布首页)

| 字段 | 值 |
|---|---|
| **必需 type** | `distribution_multi`(恰好 1 个) |
| **允许 type** | `distribution_multi` |
| **数量约束** | 1..1 |
| **顺序约束** | 不适用 |
| **accent** | 不渲染 |
| **slide id** | `persona["id"]`(通常 `distribution`) |
| **slide class** | `persona-slide layout-distribution-multi` |

### 拼装策略

```python
def assemble_layout_distribution_multi(persona, metadata):
    校验通过后:
    inner = render_component(components[0])
    slide = f'''
    <section class="persona-slide layout-distribution-multi" id="{esc(pid)}">
      {inner}
    </section>
    '''
    return [slide]
```

---

## 9. 顶层 render_report.py 流程

```python
def render_report(input_json: dict, output_dir: Path) -> str:
    """主入口。流程:
    1. 跑顶层 schema 校验(validate_components_json.py)
    2. 跑每个组件 props 的 schema 校验
    3. 对每个 persona 调对应 assembler,收集 slide HTML 列表
    4. 检测是否有任一 persona 触发了双页(metadata._internal_density_override)
       → 是 → 切 density = 'mid'(覆盖 metadata.density)
    5. flatten 所有 slide,首个加 .active 类
    6. 算 persona_nav:
       - 按 id 命名扫描,自动配对 nav-pair / nav-trio
       - 单画像时不渲染 nav
    7. 填 _base.html 的 slot
    8. copy _design-tokens.css + _components.css 到 output_dir
    9. 写 report.html 到 output_dir
    10. 跑 validate_html.py 体检
    """
```

### 9.1 双页 density 切换

```python
density = metadata["density"]
if any persona triggered dual-page:
    density = "mid"
```

### 9.2 首个 slide 加 .active

```python
slides_flat = [s for asm_result in all_assemble_results for s in asm_result]
slides_flat[0] = slides_flat[0].replace(
    'class="persona-slide ', 'class="persona-slide active ', 1
)
```

### 9.3 persona_nav 自动配对算法

```python
def build_nav(personas):
    """
    输入 personas 数组,按 id 后缀自动归组成 trio / pair / single,产 nav_trio props 喂给
    shared.render_nav_trio。

    分组规则(按 id 前缀分桶,后缀决定 mode):
      - persona-N 单独存在(无 -journey/-detail/-core)→ single
      - persona-N + persona-N-journey 配对 → pair(persona + journey)
      - persona-N-core + persona-N-detail → pair(persona + detail,文字"› 细节")
      - persona-N-core + persona-N-detail + persona-N-journey → trio
      - persona-N + persona-N-detail + persona-N-journey → trio(用 persona-N 作为 persona 锚)
      - journey-l1 独立,不进 trio/pair,作为 single
      - persona-qN(矩阵象限子画像)独立 single
      - matrix / distribution → 不进 nav(它们是顶层 layout 容器)

    首个 nav 标记 active
    """
    # 实现要点:
    # 1. 扫所有 id,按前缀(去掉 -journey/-detail/-detail-K/-core)分桶
    # 2. 每桶内决定 mode
    # 3. mode=trio 时按 persona_label / detail_label / journey_label 喂给 render_nav_trio
    # 4. 单画像总数(去掉 matrix/distribution 这种容器)== 1 时返回空字符串
```

### 9.4 _base.html slot 填充

| slot | 来源 |
|---|---|
| `{{theme}}` | metadata.theme |
| `{{density}}` | density(可能被双页覆盖为 mid) |
| `{{accent_inline}}` | 2C 主题:每个 persona 自己的 slide 内 inline,顶层填空字符串。2B/2D:填空 |
| `{{title}}` | metadata.page_title or metadata.report_title |
| `{{report_title}}` | metadata.report_title |
| `{{report_meta_info}}` | `f"{persona_count} 个画像 · 来源 {source_count} 份访谈 · {generated_at}"` |
| `{{persona_nav}}` | build_nav() 的产出,单画像填空 |
| `{{main_content}}` | flatten 后 slides 拼接 |

填完后做 `re.sub(r"\{\{[^}]+\}\}", "", out)` 兜底清除残留占位符。

### 9.5 CSS 随包

```python
# 写 report.html 的同时,把 _design-tokens.css 和 _components.css 复制到 output_dir
# 走 shutil.copy2,目标文件名保持原样(_base.html 用 href="_design-tokens.css")
SKILL_TEMPLATES = Path(__file__).parent.parent.parent / "assets" / "templates"
shutil.copy2(SKILL_TEMPLATES / "_design-tokens.css", output_dir / "_design-tokens.css")
shutil.copy2(SKILL_TEMPLATES / "_components.css", output_dir / "_components.css")
```

### 9.6 接入 P7 validate_html

```python
from scripts.validate_html import validate_html_file
issues = validate_html_file(output_dir / "report.html")
errors = [i for i in issues if i["level"] == "ERROR"]
if errors:
    print(f"⚠ validate_html 发现 {len(errors)} 个 ERROR:", file=sys.stderr)
    for e in errors:
        print(f"  - [{e['code']}] {e['message']}", file=sys.stderr)
    # 不抛异常,只 warn(因为有些 ERROR 可能是 CSS 失败导致,不阻塞产出)
```

### 9.7 接入 B 阶段 schema 校验

```python
from scripts.validate_components_json import validate_report_json
issues = validate_report_json(input_json)
errors = [i for i in issues if i["level"] == "ERROR"]
if errors:
    raise ValueError(
        f"组件 JSON 校验失败 {len(errors)} 个 ERROR:\n" +
        "\n".join(f"  [{e['code']}] {e['path']}: {e['message']}" for e in errors)
    )
```

---

## 10. CLI

```python
# scripts/components/render_report.py 的 __main__

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="components JSON 路径")
    parser.add_argument("--output", required=True, help="输出 HTML 路径(目录会用来放 CSS)")
    parser.add_argument("--skip-validate", action="store_true", help="跳过 schema + HTML 校验(debug 用)")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    input_json = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html = render_report(input_json, out_dir, validate=not args.skip_validate)
    out_path.write_text(html, encoding="utf-8")
    print(f"[OK] {out_path}")
```

---

## 11. 验收清单(给 review 脚本对照)

- [ ] 8 个 `assemble_*` 函数都不抛 NotImplementedError
- [ ] 每个 assemble 在 valid input 下:返回 list,长度 ≥1,所有元素含 `<section class="persona-slide layout-XXX"`
- [ ] 每个 assemble 在 invalid input 下:抛 ValueError 且消息含 layout 名
- [ ] 2c-portrait / 2c-detail / 2c-journey 在 valid input 下:HTML 含 `--color-accent: var(--accent-`
- [ ] 2b-grid 在「3 个组件 + 单页能装下」:返回长度 1
- [ ] 2b-grid 在「8 个组件溢出」:返回长度 2,且第二个 slide class 含 `layout-2b-grid-detail`,且 metadata 有 `_internal_density_override="mid"`
- [ ] render_report.py 接 B 阶段 6 个 golden samples JSON 全部输出非空 HTML
- [ ] render_report.py 触发双页 case 时,输出 `data-density="mid"`
- [ ] render_report.py 多画像 case 时,输出含 `.persona-nav` 且首个 slide 含 `.active`
- [ ] render_report.py 单画像 case 时,输出**不含** `.persona-nav`(slot 填空)
- [ ] render_report.py 输出目录里有 `_design-tokens.css` + `_components.css`
- [ ] grid_solver._dual_page_split 的硬编码 `components[:3]` bug 修复(改成"按 solver 估算实际溢出点切")
