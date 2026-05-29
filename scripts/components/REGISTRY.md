# 组件注册表(P8 组件化盘点结果)

> V9 组件化盘点。渲染唯一入口:`scripts/components/render_report.py`。详细历史见 `docs/reference/`。
>
> **组件清单以 `schemas/report.json` 的 `component_type` enum 为准(当前 24 个顶层 type)。**
>
> 用法:LLM 在产 `05-report.json` 时,只能从下表挑组件 `type`,props 字段必须严格匹配 `schemas/<type>.json`。

---

## 0. 顶层契约(report.json 顶层结构)

```jsonc
{
  "metadata": {
    "report_title": "...",
    "theme": "2b|2c|2d",
    "density": "high|mid|low",
    "source_count": 5,
    "persona_count": 3,
    "generated_at": "2026-05-22 14:07"
  },
  "personas": [
    {
      "id": "persona-1",                // 见 visual-system.md id 命名约定
      "name": "深听场景派",
      "layout": "layout-2c-portrait",   // 8 选 1,见下方枚举
      "accent": "mist-blue",            // 2C 时必填,其它主题忽略
      "components": [
        { "type": "identity_card", "props": { ... } },
        { "type": "persona_quote_pull", "props": { ... } },
        { "type": "section_blocks_grid", "props": { "blocks": [ ... ] } }
      ]
    }
  ]
}
```

### 0.1 layout 枚举(8 个)

| layout | 用途 | 触发条件 |
|---|---|---|
| `layout-2b-grid` | toB/toD 单画像单页 | 默认 |
| `layout-2b-grid-detail` | **新增** — toB/toD 双页第二页(整页详细信息,无左侧画像卡) | 单页 12×3 网格估算溢出时,solver 自动启用第二页 |
| `layout-2b-journey` | toB/toD 用户旅程图(.is-l1 全景 / .is-l2 单角色) | 多角色 + 用户确认要旅程 |
| `layout-2c-portrait` | toC 单画像主页 | 默认 |
| `layout-2c-detail` | toC 专题详情页(双页第二页) | 主画像页装不下某条强观点时触发 |
| `layout-2c-journey` | toC 用户旅程图 | toC + 研究目标涉及旅程 |
| `layout-matrix-2d` | R4 2D 矩阵首页 | R4 范式 |
| `layout-distribution-multi` | R5 多维分布图首页 | R5 范式 |

### 0.2 layout-2b-grid-detail(双页兜底,P8 新增)

**问题**:弱模型 + 大信息量场景下,单页 `layout-2b-grid` 12×3 网格塞不下,如果只能 reject 回字段对齐,用户体验差。

**解法**:layout solver 估算到溢出时,**自动切换为双页**:
- 第 1 页:仍是 `layout-2b-grid`(左身份卡 + 右栏放优先级最高的 3-4 个组件)
- 第 2 页:**`layout-2b-grid-detail`**(**整页 12 列大网格,无左身份卡**,放剩余组件)

**视觉**(两页都更舒展):
- **两页都把 `data-density` 切到 `mid`**(从默认 high),而不是只改第二页。第一页右栏组件少了,如果维持 high 密度,字小行紧反而显得空旷;切 mid 后整体视觉一致
- 行间距:两页都用 `--space-grid-row: var(--space-7)`(原 high 是 `var(--space-3)`)
- 字号:走 mid 主题对应的 text token(`_design-tokens.css` 已有 high/mid/low 三档 token,切 density 自动生效,**不需要新加 CSS**)
- 第 2 页顶部小条 banner 写「画像名 · 工作细节」(`.detail-page-banner`)
- 第 2 页主体是 12 列宽 × 自适应行数的 grid

> 关键:**density 切换不引入新 CSS**,沿用 design tokens 已有的 high/mid/low 三档机制。Python 在 render_report 时检测「这个画像是双页」就把 `<html data-density>` 改成 mid。

**id + nav 文字命名**:`persona-N-core` / `persona-N-detail`,nav 走 nav-pair(画像名 · 核心 + › 细节)

**触发逻辑**(Layout solver 内):
```
单页估算 → 总行数 ≤ 3 → 用 layout-2b-grid 单页(保持 high 密度)
                ↓
              > 3 → 拆双页 + 切 mid 密度:
                     第 1 页(grid)放 ① ② + 1 个最重要的 body 组件
                     第 2 页(grid-detail)放剩余 body 组件
                     <html data-density> = mid(两页都生效)
```

LLM 不需要主动选 detail layout,也不写 density;只列组件 → solver 决定要不要拆 + Python 决定改不改 density。

---

## 1. 共享基础设施(跨 layout,**不是** LLM 可选 type)

| 名称 | 用途 | 渲染位置 |
|---|---|---|
| `report_meta_bar` | 顶部主标题 + 元信息条 | `render_report.py` → `_base.html` slot `{{report_title}}` / `{{report_meta_info}}` |
| `persona_nav` | 多画像 tab(nav-pair / nav-trio) | `layouts/nav.py` → `_base.html` slot `{{persona_nav}}` |
| `persona_illust` | 2C 头像/插画占位 | `renderers/_utils.render_illust()` |
| `tooltip_runtime` | 全局 hover 气泡 | `_base.html` 内置 JS,无 JSON type |

> 说明:`tooltip_runtime` 不是 LLM 可选组件,它是 `_base.html` 的固有部分,组件化阶段不动。

### 1.1 persona_nav 组合契约(硬规则)

LLM 不直接产 `<button>`,只产 `personas` 数组(每个 persona 有 `id` + `name`)。`render_report.py` 顶层组装时:

- 当数组里出现配对 id (`persona-N` + `persona-N-journey`,或 `persona-N-core` + `persona-N-detail`),**必须自动包成 `.nav-pair` 连体按钮**:左半画像名(`.nav-btn-persona`),右半 `› 旅程` / `› 细节`(`.nav-btn-journey`)
- 禁止把 `内行深听派` 和 `内行深听派旅程` 输出成两个独立同等胶囊按钮(P0 真实失败)
- L1 全景旅程 `journey-l1` 是独立 tab,不进 nav-pair(它不绑定任何单画像)
- 单画像双页 `persona-N-core` + `persona-N-detail` 同样走 nav-pair,右半文字 `› 细节`

LLM 不需要决策 nav-pair 怎么拼;只要 id 命名按 visual-system.md §3.2 规则,Python 自动包对。

---

## 2. layout-2b-grid 组件(toB/toD 单画像,放 renderers/tob_grid.py)

### 2.1 左栏 identity-panel(身份卡)

| 组件名 | 用途 | CSS class | 现有渲染 |
|---|---|---|---|
| `identity_panel` | 左栏整体容器(以下 5 个的拼装) | `.layout-2b-grid .identity-panel` | `render_identity_panel` |
| └ `persona_avatar` | 头像或占位 | `.avatar-wrap` `.persona-avatar` `.persona-avatar.placeholder` | 在 `render_identity_panel` 内联 |
| └ `identity_name` | 画像中文名 + 英文别名 | `.identity-name` `.name-line` | 同上 |
| └ `identity_desc` | 一段身份描述 | `.identity-desc` | 同上 |
| └ `identity_meta_rows` | key-value 行(可单列/双列) | `.identity-meta` `.meta-row` `.meta-row-pair` `.meta-label` `.meta-value` | 同上 |
| └ `one_sentence_need` | 引号一句话需求 + 来源 | `.one-sentence-need` `.osn-text` `.osn-source` | 同上 |

> 注:identity_panel 是 5 个子结构的固定组合,可设计为单一组件(props 含 5 个对象),不必拆 5 个。

### 2.2 右栏 modules-panel(12×3 grid 内的卡片)

#### 默认字段优先级(布局 solver 据此排序)

约定的字段优先级(从上到下,从左到右):

1. **核心工作职责**(`resp_rings`)
2. **上下游协同 + KPI**(`collab_flow`)
3. **高频任务**(`titled_list`,通常紧贴 resp_rings 或 collab_flow 下方)
4. **典型业务场景 / AI 场景**(`scenario_grid` / `ai_scenario_grid`)
5. **核心痛点**(`painpoint_list`,通常放在场景/业务系统之下)
6. **其他**(`titled_list` / 兜底 generic_*)

LLM 不写 `grid-column` / `grid-row`,只在 `components` 数组里**按优先级顺序**列出组件。Layout solver(见 §13)按优先级 + 估算高度自动算位置,保证 12 列网格无缺口、行间疏密均匀。

#### 组件清单

| 组件名 | 用途 | CSS class | 现有 COMPONENT_RENDERERS |
|---|---|---|---|
| `grid_module` | 单元卡片外壳(标题 + body),Python 自动包,**不暴露给 LLM** | `.grid-module` `.module-title` `.module-body` `.module-icon` | `render_component` 包外壳 |
| `resp_rings` | 职责占比环图(SVG) | `.resp-rings` `.ring-item` `.ring-svg` `.ring-track` `.ring-fill` `.ring-pct` `.ring-label` | ✓ |
| `collab_flow` | 上下游协同流 + KPI 块 | `.collab-flow` `.flow-cell` `.flow-cell-label` `.flow-cell-value` `.kpi-block` | ✓ |
| ~~`task_freq_list`~~ | 已删除:高频任务字段映射到 `titled_list` 兜底 | ~~`.task-freq-*`~~ 已删 | 删除 |
| `scenario_grid` | **典型业务场景**(两种形态自动切换,见下) | `.scenarios-grid-{1..4}` `.scenario-card` `.scenario-image` `.scenario-image-empty` `.scenario-placeholder-icons` `.scenario-caption strong` `.tool-icon-tag` | ✓(P8 重构,合并旧 system_grid 的工具/业务系统展示) |
| `ai_scenario_grid` | AI 工具/系统场景(访谈大量提到 AI 时启用) | 沿用 `.scenarios-grid-*` + `.scenario-card.is-ai` | ✓ |
| `painpoint_list` | 痛点列表(带 mention-badge) | `.painpoints-list` `.painpoint-item` `.pp-title` `.pp-detail` `.mention-badge` | ✓ |
| `titled_list` | 通用「标题+正文」列表(用于 experience_goals / 自定义字段) | `.generic-list` `.generic-list-item` `.gl-title` `.gl-detail` `.gl-insight` | ✓ (P8 拆出专属 class,不再复用 .painpoints-list) |
| `generic_text` | 兜底纯文本块 | `.generic-text-card` | ✓ |
| `generic_bullet` | 兜底 bullet 列表 | `.generic-bullet-list` `.generic-bullet-item` | ✓ |
| `generic_kv` | 兜底 key-value 表 | `.generic-kv-card` `.kv-row` `.kv-key` `.kv-value` | ✓ |

#### scenario_grid 两种形态(P8 重构)

> 替代旧的 `system_grid` + `scenario_grid` 两个独立组件。系统/工具名直接收纳到 scenario_grid 的标签层。

**统一标题**:`典型业务场景`(在 grid_module 外壳的 title 槽里)

**形态 A — 有截图**(用户在 `<项目运行目录>/界面截图/` 放了对应场景的图):
```
┌─ scenario_card ─┐ ┌─ scenario_card ─┐
│  [截图]          │ │  [截图]          │
│  场景描述(短)   │ │  场景描述        │
│  □工具A □系统B   │ │  □工具C          │
└──────────────────┘ └──────────────────┘
```

**形态 B — 无截图**(渲染前 Python 检查到没图,自动降级):
```
┌─ scenario_card ─┐ ┌─ scenario_card ─┐
│ 🗂️ 占位图标      │ │  🗂️              │
│ 场景描述(一句话)│ │  场景描述         │
│ □工具A □系统B    │ │ □工具C            │
└──────────────────┘ └──────────────────┘
```

- **2B 紧凑占位(2026-05-29)**:`layout-2b-grid` / `layout-2b-grid-detail` 下无截图卡片的 `.scenario-image` 取消 4:3 撑满,`max-height: 88px`,避免单卡占半行时挤压同页痛点/目标模块。
- **数据建议**:无截图时 `scenes` 优先 **2–3 条**(触发 `scenarios-grid-2/3`),单条 `scenarios-grid-1` 仍可用但卡片更宽。

**props 契约**:
```jsonc
{
  "type": "scenario_grid",
  "props": {
    "scenes": [
      {
        "caption": "调度排班",                      // 必填,场景描述
        "tools": ["调度大屏", "Excel"],             // 工具/业务系统标签,数组
        "screenshot": "scene-1.png"                 // 可选;Python 检查文件存在性,不存在自动转形态 B
      }
    ]
  }
}
```

LLM 永远填 `screenshot` 字段(如果访谈里能定位到对应截图),Python 在渲染时检查 `<项目运行目录>/界面截图/<filename>` 是否存在,不存在就用形态 B + 渲染时把这个场景加进"请用户补充截图"提示。

#### ai_scenario_grid

- 与 `scenario_grid` 同形;`.scenario-card.is-ai` **仅作语义标记**,卡片底色与 `tool-icon-tag` 与典型业务场景一致
- **工具标签/Caption 工具名(2026-05-29)**:`.scenario-card .tool-icon-tag` 统一 `color: var(--color-text-primary)`;caption 内 `.scenario-tool-names` 同为黑字(废弃 `.scenario-tools .tool-icon-tag` 的 accent 蓝字)
- 模块级区分:外壳标题仍为「AI 辅助场景」+ AI 图标(`grid-module-ai-scenario-grid`)
- props 字段与 scenario_grid 基本相同;`module_title` 可选,默认 "AI 辅助场景"
- LLM 决策规则:当 `04-personas.json` 的 `ai_assist_systems` 字段非空(或访谈大量提到 AI/大模型/智能助手),启用本组件;否则不启用

#### 删除项

- ~~`system_grid`~~ — 业务系统展示并入 `scenario_grid` 的 `tools` 标签
- ~~`fault_list`~~ — 故障场景列表是运维特有字段,通用画像不需要,改用 `titled_list` 兜底

#### LLM 自定义字段的兜底原则

用户在 `03-field-alignment.json` 里加一个新字段时,**LLM 不允许新建组件 type**。规则:

1. 字段是「标题+正文条目列表」→ 用 `titled_list`
2. 字段是「key-value 表(如设备清单)」→ 用 `generic_kv`
3. 字段是「纯文本一段话」→ 用 `generic_text`
4. 字段是「bullet 短句列表」→ 用 `generic_bullet`

LLM 在自定义字段对齐阶段必须告诉 Python "这个字段用哪个兜底组件",并通过 `--field-labels` 传中文显示名。

---

## 3. layout-2b-journey 组件(toB 旅程,放 renderers/tob_journey.py)

> 有两种修饰类:`.is-l1`(全景:角色 × 阶段) / `.is-l2`(单角色:阶段 × 工作流程+关注点/痛点)。同一套 CSS 类,通过 props 区分。

| 组件名 | 用途 | CSS class | 现有渲染 |
|---|---|---|---|
| `tob_banner` | 顶部深色 banner(标题+副标题) | `.tob-banner` `.tob-banner-main` `.tob-banner-title` `.tob-banner-subtitle` | `render_overall_2b_journey` / `render_persona_2b_journey` |
| `tob_rail` | 左侧分类列(阶段/子阶段/工具触点/工作流程/关注点) | `.tob-rail` `.tob-rail-cell` `.tob-rail-stages` `.tob-rail-substages` `.tob-rail-tools` `.tob-rail-role` `.tob-rail-dim` `.tob-rail-role-name` `.tob-rail-role-tag` | 同上 |
| `tob_stage_header` | 顶部阶段标签行 | `.tob-stage-tag` `.tob-stage-number` | `render_stage_header` |
| `tob_substage_row` | 子阶段行:方块 + 右尖三角组成 `▭▷`,顺序代表流程 | `.tob-substage-cell` `.tob-substage-arrow` | renderer 已对齐;旧 `.tob-substage-tag` 已删 |
| `tob_tools_row` | L2 hybrid 工具/触点标签行(每阶段 0-6 个 pill) | `.tob-tools-cell` `.tob-tools-tag` `.tob-tools-empty` | `_render_tools_touchpoint_cells` |
| `tob_flow_cell` | 流程胶囊(单 cell 一句话,**≤ 22 字**,data-evidence 挂在 `.tob-flow-pill` 上) | `.tob-flow-cell` `.tob-flow-cell.is-terminal` `.tob-flow-pill` `.tob-flow-pill.is-highlight` | `render_flow_cell` |
| ~~`tob_cross_role_arrow`~~ | **已废弃,不要用**。跨角色交接不再是独立组件,而是 `tob_journey_l1` 的 `nodes`/`edges` DSL 里一条「from/to 落在不同 lane」的普通 edge(详见 §3.2/§3.3)。schema 不收 `cross_role_arrows`/`flows`/`roles`,渲染器也不读 | —(对应 CSS overlay 已无 renderer 产出) | 删除 |
| `tob_focus_cell` | 关注点/痛点单元(L2 专属,每阶段一个)。**有截图时左侧渲染图,无截图时一句话简要描述** | `.tob-focus-cell` `.tob-focus-card` `.tob-focus-card.is-pain` `.tob-focus-card-title` `.tob-focus-card-body` `.tob-focus-card-mock` `.tob-focus-card.has-screenshot` | `render_focus_card` / `render_focus_pain_cell` |

> 注:`tob-pain-banner` 旧版底部痛点条已废弃(`SKILL.md` 约束规定痛点并入 `.tob-focus-card.is-pain`),不再做新组件。

### 3.0 节点密度门禁(2026-05-28 新增)

**问题**:LLM 在写 L1/L2 UML 旅程时容易偷懒,5 个角色 × 5 个阶段的报告里只放 6 个主线节点,完全不体现各角色在各子阶段的真实任务流(2026-05-28 真实失败:DevOps 5×5 报告只产 ~6 节点)。

**硬规则(L1)**:

```
节点数 < 角色数 × 子阶段总数 × 0.5  →  reject 回字段对齐
```

**硬规则(L2,2026-05-29 起)**:

```
节点数 < ceil(子阶段总数 × 1.2)  →  reject 回字段对齐
```

其中 `子阶段总数 = sum(len(stage.subStages) for stage in stages)`。

**例子**:
- 4 lanes × 3 stages × 3 substages/stage (L1) = 4×9×0.5 = **18 个节点** 最低
- 5 lanes × 5 stages × 3 substages/stage (L1) = 5×15×0.5 = **37 个节点** 最低
- 1 lane × 4 stages × 3 substages/stage (L2) = ceil(12×1.2) = **15 个节点** 最低
- 1 lane × 4 stages × 2 substages/stage (L2 DevOps 样例) = ceil(8×1.2) = **10 个节点** 最低

**执行点**:`_render_uml_journey` 在结构校验通过后立即检查,失败抛 `ValueError("信息密度不足 ...")`。L2 通过 `density_mode="l2"` 走独立阈值;L1 保持 `lanes × substages × 0.5`。

**L2 附加硬规则**:`tools_touchpoints` 若提供,长度必须与 `stages` 等长(错误码 `P8-L2-TOOLS-LEN`)。

**LLM 应对**:不要只放主线起止+决策点。每个 (lane, stage) cell 都应该有 1-2 个具体任务节点,体现该角色在该阶段做了什么。守门测试见 `scripts/components/tests/test_journey_density.py`。

### 3.0.2 L1/L2 共用工作流判断语义(2026-05-29 修订)

**问题**:菱形「是」走主线没问题,但「否」常画成回指主线上已有节点,没有「如果否会怎么办」的独立任务 — 与下方 focuses 重复且误导。

**L1 多角色与 L2 单角色统一规则**(`_workflow_decision_semantics_gate`):

| 规则 | 要求 |
|---|---|
| `decision.label` | 问句型判断;**禁止**与 `focuses[].title` 相同 |
| `branch:yes` | **必填**(或未标注的主线出边) — 指向主线下一任务 |
| `branch:no` | **可选** — 仅当图上有**独立补救节点**时才画(如「补充立项」「隔离故障点」「记录旁路 doc」) |
| 禁止的装饰性否 | 否分支**不能**回指菱形之前主线上已有的节点;若无补救任务 → **删掉否分支** |
| 「如果否」写哪 | 删掉的否逻辑写进 `focuses` 或 `steps/render-persona-page.md` 指引,不硬画在 UML |

**范例**:
- ✅ `范围清晰?` —是→ `拆分任务`; —否→ `补充立项`(独立节点 n13)
- ✅ `枚举转供？` —是→ `算满载过载`; —否→ `隔离故障点`(独立节点)
- ❌ `结论成立?` —否→ `联调验证`(主线上已有,应删掉否,把「不成立则重验」写 focuses)
- ❌ 只有「是」、无补救节点 — **允许**,不要为凑对称硬画「否」

范例 JSON:`golden_samples/tob_journey_l2.json`。测试:`test_l2_workflow_semantics.py`。

### 3.0.1 协同语义门禁(2026-05-29 新增)—— L1 必须是「跨角色协同 UML」,不是「N 条平行流水线」

**问题(2026-05-29 真实失败)**:DevOps 5 角色 × 5 阶段的 L1,密度门禁过了(37 节点),但渲染出来是「5 条互不相干的纵向流水线」—— 全是 `step` 节点、边只在自己泳道内、0 跨泳道交接、0 判断、0 产物。同一个渲染器,真值(电力调度员)却是一张「跨角色协同 UML 流程图」。差异 100% 来自 DSL 怎么写。

**密度门禁只保证「节点够多」,协同门禁保证「是不是真协同」。** 对**多角色全景 L1(lanes ≥ 3 且 stages ≥ 3)**强制下限(`_coop_semantics_gate`,缺任一即 reject 回字段对齐):

| 维度 | 硬下限(reject) | 真值水平(应努力达到) |
|---|---|---|
| 跨泳道边占比 | ≥ **15%** | 真值 46% |
| `decision` 节点 | ≥ **2** | 真值 5(每个关键分叉一个) |
| `doc` 节点 | ≥ **1** | 真值 8(**每个阶段都有产物沉淀**) |
| `dashed` 边 | ≥ **1** | 真值 11(异步通知/系统推送/旁路记录) |
| `branch:yes/no` | 清单要求(门禁不硬卡) | 每个 `decision` 的出边都标 |

> 门禁是「反退化下限」,标在 skill 自带合格样例之下;**把图拉到真值丰富度是这份清单的活,不是靠把门禁调到最严**(否则会误杀合格样例)。L2 单泳道 / 小流程(< 3 lane 或 < 3 stage)自动豁免。

**写 L1 DSL 的协同清单(逐条对照):**

1. **跨泳道边 = 角色交接**。每个角色不是一条独立竖线;真实业务里 A 把活交给 B(下令→执行、提需求→接需求、执行→审核、配置→保障)。这些交接就是一条 `{"from": A 泳道某节点, "to": B 泳道某节点}` 的 edge。没有交接边,这张图就只是 N 条平行流水线。**交接必须对应 persona `collaboration` 字段里的真实上下游,不能瞎连。**
2. **判断用 `decision` 菱形 + `branch`**。关键分叉写成问句型 `decision`。**「是」**标 `branch:yes` 走主线。**「否」**仅当图上有独立补救任务节点时才画 `branch:no`(如补全/退回/旁路 doc);若否逻辑只是说明性、没有对应任务 — **删掉否分支**,写进 `focuses`。**禁止**否分支回指主线上已有节点(L1/L2 同一规则,见 §3.0.2)。
3. **产物用 `doc` 波浪底**。每个阶段的交付物沉淀(PRD、测试报告、上线方案、监控看板、审计日志、操作记录)写成 `type:"doc"`。
4. **异步 / 系统推送用 `style:"dashed"`**。监控告警推送给人、流水线构建结果通知、自动归档这类非人工同步动作走虚线。
5. **同格错位用 `track:0/1`**。同一 (lane, stage) 里多个节点,用 `slot` 横向铺开(0-5 对齐子阶段列)、`track` 上下错位避免重叠。**渲染器**在**每个 (lane, stage) cell** 内检测横向 interval 重叠时,对 L1/L2 自动选最少节点下沉第二行(`_assign_tracks_for_cell`);`track` 仅作偏好提示。L2 单角色与 L1 多角色排布规则见 §3.3.1。
6. **完整范例照着写**:`scripts/components/tests/golden_samples/tob_journey_l1_coop.json`(电力调度员真值,34 节点 / 5 decision / 8 doc / 11 dashed / 18 跨泳道边)。

### 3.1 tob_substage_row 箭头形契约(P8 视觉升级)

旧版子阶段长这样(被误认成「工具标签」):

```
□ 需求输入   □ 范围确认   □ 项目准备
```

P8 新版必须长这样 ——**子阶段名字直接放在方块里,右尖三角是连接到下一个方块的指示**:

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│ 需求输入 │▷│ 范围确认 │▷│ 项目准备 │▷
└─────────┘  └─────────┘  └─────────┘
```

实际渲染等同(横向连接):

```
▭ 需求输入 ▷▭ 范围确认 ▷▭ 项目准备 ▷
```

- 每个 `.tob-substage-arrow` 是「一个浅色背景方块 + 右侧伪元素三角」的组合;**子阶段名字在方块内**,▷ 由 CSS `::after` 伪元素画
- 一个阶段下挂 2-4 个子阶段,横向并列,▷ 顺序读流程
- 最后一个方块的 ▷ 用 `.is-terminal` 修饰类隐藏(或换成端点)
- 方块背景 = `--color-bg-card-soft`(浅色,不和 stage_header 深蓝抢眼)
- 三角填充色 = `--color-primary-light`(浅蓝,呼应 flow_cell 间的细箭头)

> CSS 需要 B 阶段一起改:`.tob-substage-arrow` 替代旧 `.tob-substage-tag`(已登记到 §14 待联动清单)。

### 3.2 tob_flow_cell 文本上限 + 箭头风格(P8 视觉升级)

- 单个 flow_cell 必须 **≤ 22 个汉字 / 33 个字符**(schema 强约束),超出 reject
- 一个 cell = 一个原子任务,不允许把"配置代码仓、代码检查、分支策略和流水线规则"这种长复合句压进一个 cell
- cell 间箭头:从「粗深蓝填充三角」改为「细浅蓝线 + 末端小箭头」(`stroke-width:1.5`,`stroke:var(--color-primary-light)`,长度自适应)
> ⚠️ 注意:上面是旧 P7「flows 胶囊」模型的视觉规则。**P8 起 `tob_journey_l1`/`l2` 一律走 `nodes`/`edges` UML DSL**(schema 严格 `nodes`/`edges`,`additionalProperties:false`),跨角色交接就是一条「from/to 在不同 lane」的 edge,**没有独立的 cross_role_arrow 组件**。L1/L2 的真正契约见下面 §3.3。

### 3.3 tob_journey_l1 / l2 的真正契约:`nodes` / `edges` UML DSL(P8)

> 旧版本这里写的是 `flows` / `roles` / `cross_role_arrows` 模型 —— **那套已彻底废弃**:schema 不收(`additionalProperties:false`,只认 `banner_title`/`banner_subtitle`/`stages`/`lanes`/`nodes`/`edges`/`note`),渲染器(`_render_uml_journey`)也不读。照旧写会被 schema 直接拦下。下面是现在唯一正确的写法。

LLM 在 `05-report.json` 里给 `stages` / `lanes` / `nodes` / `edges`,Python 负责所有几何计算(节点坐标、track 错位、正交连线、分支标签)。

**`nodes[i]` 字段:**

| 字段 | 说明 |
|---|---|
| `id` | `^n[0-9]+$`(`n1`、`n2`…) |
| `lane` | 落在哪个角色泳道(= 某个 `lanes[].id`) |
| `stage` | 落在哪个阶段(= 某个 `stages[].id`) |
| `type` | `start` / `end`(圆角胶囊起止)· `step`(矩形,普通步骤)· `action`(圆角矩形,关键动作)· `decision`(菱形,判断)· `doc`(波浪底,产物) |
| `label` | ≤ 16 字 |
| `slot` | 0-5,横向定位(对齐该阶段的子阶段列;同 cell 内多节点 slot 不能重复) |
| `track` | 0/1,同 cell 内上下错位避免重叠 |

**`edges[i]` 字段:**

| 字段 | 说明 |
|---|---|
| `from` / `to` | 节点 id。**`from`/`to` 落在不同 lane = 跨角色交接(协同的核心)** |
| `branch` | `yes` / `no`,`decision` 出边标在这,渲染成「是 / 否」分支标签 |
| `style` | `solid`(默认) / `dashed`(异步通知 / 系统推送 / 旁路记录) |

**最小协同范例(节选自电力调度员真值):**

```jsonc
{
  "nodes": [
    {"id":"n3","lane":"dispatcher","stage":"alarm","type":"decision","label":"需停电?","slot":4,"track":1},
    {"id":"n4","lane":"system","stage":"alarm","type":"doc","label":"记录初判","slot":4,"track":1},
    {"id":"n5","lane":"dispatcher","stage":"isolate","type":"action","label":"申请停电","slot":1},
    {"id":"n6","lane":"dispatcher","stage":"isolate","type":"action","label":"下发调令","slot":3},
    {"id":"n18","lane":"field","stage":"isolate","type":"action","label":"执行倒闸","slot":1}
  ],
  "edges": [
    {"from":"n3","to":"n5","branch":"yes"},                 // 判断通过走主线
    {"from":"n3","to":"n4","branch":"no","style":"dashed"}, // 否则跨泳道记录(虚线旁路)
    {"from":"n6","to":"n18"}                                // 调度员下令 → 现场执行(跨泳道交接)
  ]
}
```

完整 34 节点真值:`scripts/components/tests/golden_samples/tob_journey_l1_coop.json`。协同要素的硬下限见 §3.0.1。

### 3.3.1 L2 单角色 vs L1 多角色:排布规则对照(2026-05-29)

**原则**:L2(`tob_journey_l2`)与 L1(`tob_journey_l1`)走**同一渲染器** `_render_uml_journey`;几何排布尽可能相同,**仅节点数量门禁与 L1 协同语义门禁不同**。

| 维度 | L1 多角色全景 | L2 单角色旅程 | 说明 |
|------|-------------|-------------|------|
| 渲染入口 | `density_mode="l1"` | `density_mode="l2"` | 同一函数 |
| `slot` 横向定位 | `x = cell_left + (slot+0.5)×(cell_w/N)` | **相同** | 按值定位,N=max(slot)+1 |
| `track` 上下错行 | 同 `(lane,stage)` cell 内 interval 重叠 → 最少下沉第二行 | **相同** | `_assign_tracks_for_cell` |
| 节点 `type` 尺寸 | `dense` / `wide_uml`(3×4 特例) | **相同**(`dense`) | 单泳道无 wide_uml 特例 |
| `edges` 连线 / `branch` / `dashed` | 正交路径 + 是/否标签 | **相同** | L2 通常无跨 lane 边,但 DSL 允许 |
| 阶段列 / 子阶段行 | `stages` + `subStages` | **相同** | L2 hybrid 外壳多「工具/关注点」行 |
| **节点密度下限** | `lanes × 子阶段总数 × 0.5` | **`ceil(子阶段总数 × 1.2)`** | **L2 独有** |
| **协同语义门禁** | lanes≥3 且 stages≥3 时强制 | **豁免** | **L1 独有**(单角色无需跨泳道协同图) |
| `tools_touchpoints` | 可选 | 若提供则 **len=stages** | **L2 hybrid 独有** |
| 泳道侧栏(SVG) | 有(`show_lane_rail=True`) | hybrid 内 UML 格无侧栏 | 外壳差异,不影响 cell 内算法 |

**LLM 写 L2 DSL 时**:除密度按 L2 阈值、单泳道 `lanes` 通常只有 1 条外,`nodes`/`edges`/`slot`/`track`/`type` 写法与 L1 **同一套**;发布阶段多节点挤在一起时,渲染器会自动双行错开(与多角色 L1 一致)。

### 3.4 tob_focus_cell 截图位 + fallback(P8 视觉升级)

- 关注点卡片**留一个截图槽**:`<项目运行目录>/界面截图/focus-<persona_id>-<stage_idx>.png`
- 渲染前 Python 检查文件存在性:
  - 存在 → 渲染 `.tob-focus-card.has-screenshot` + 截图占位换成 `<img>`
  - 不存在 → 渲染 `.tob-focus-card-mock.is-empty` + props.description 一句话描述(必填 fallback)
- 渲染完后把"未提供截图"的关注点列出来,提醒用户补图
- 痛点卡片 `is-pain` 不需要截图槽,仍走「标题 + body」二层

---

## 4. layout-2c-portrait 组件(toC 单画像主页,放 renderers/toc.py)

> 是拼贴 grid(身份卡 32% + 右侧 1fr 1fr 拼贴),不是分栏。
>
> **toC 的核心张力**:画像内容的「灵活性」(每个研究都有独特字段,如"画像指纹"/"对音质追求") vs 组件的「规范性」(避免敷衍内容、视觉乱)。下面的契约设计努力在两者间取平衡。

| 组件名 | 用途 | CSS class | 现有渲染 |
|---|---|---|---|
| `identity_card` | 左栏身份卡(头像+名字+副标+灵活 meta_tags) | `.identity-card` `.persona-illust` `.persona-illust-placeholder` `.persona-name-anchor` `.persona-subtitle` `.meta-tags-list` `.meta-tag-card` `.meta-tag-label` `.meta-tag-value` | 由 LLM 手写,未 Python 化 |
| `persona_quote_pull` | 大引号代表原话(右侧顶部跨 2 列,**≤50 字**) | `.persona-quote-pull` `.persona-quote-pull .quote-source` | 同上 |
| `section_blocks_grid` | section-block 的网格容器(4 / 5(+1 full_width) / 6 拼贴) | `.section-blocks-grid` `.section-blocks-grid.count-{4..6}` `.section-block.full-width` | 同上 |
| `section_block` | 三层段卡(标题 + 总结 + 正文,有内容深度 minLength) | `.section-block` `.section-block-title` `.section-block-summary` `.section-block-body` `.section-block.full-width` | 同上 |

### 4.1 identity_card 灵活 meta_tags 契约(解决「画像指纹」类灵活字段)

**问题(你提的)**:
1. 职业+年龄可以合并成一个 tag(空间紧时聪明的做法,如「医生 · 50+」)
2. 「画像指纹」(更好的叫法,用来概括画像核心调性,如「内行 · 内容 · 场景 · 高端」)是无法提前预判的字段

**解法**:identity_card 的 meta_tags 完全自由,LLM 决定有几个 tag、每个 tag 的 label 是什么、value 怎么表达。

**props 契约**:
```jsonc
{
  "type": "identity_card",
  "props": {
    "name": "深听场景派",                   // 画像名(必填,2-6 字)
    "subtitle": "价值清晰,已经把 HiRes...", // 副标(必填,≤30 字)
    "illust_path": "深听场景派.png",        // 可选;Python 检查文件存在,不存在用 placeholder
    "meta_tags": [                          // 数组,2-5 个,完全灵活
      { "label": "职业 / 年龄",  "value": "医生 · 50+" },        // 合并字段示例
      { "label": "画像指纹",     "value": "内行 · 内容 · 场景 · 高端" }, // 灵活新字段示例
      { "label": "设备",         "value": "SoundX 音响、华为手机" },
      { "label": "音乐角色",     "value": "倾听者、精神陪伴" }
    ]
  }
}
```

**LLM 决策权**:
- `meta_tags` 数量:**2-5 个**(schema 强约束,超出 reject)
- 每个 `label`:**完全自由文本**,长度 2-6 字(schema 约束)。可以是「职业 / 年龄」「画像指纹」「使用风格」任何 LLM 决定的字段名
- 每个 `value`:**完全自由文本**,长度 2-20 字。可以单值、可以 `·` 拼接多值、可以 `、` 拼接列表
- LLM 应该结合**研究目标**和**画像特征**决定哪些 label 上 identity_card(读者一眼能识别这个画像的关键特征即可)

**视觉规范由 CSS 保证**(LLM 不接触):
- meta_tag_card 尺寸固定(高度自适应)
- label 字号小、value 字号大、value 加粗
- 行间距、卡片间距固定
- 当 meta_tags ≥ 4 时自动 2 列拼贴(CSS grid),≤ 3 时单列

### 4.2 section_block 灵活 title + 内容深度保证

**问题(你提的)**:
- 字段名要贴合画像特征(如音乐画像里写「对音质的追求」而不是「行为习惯」)→ title 必须自由文本
- 但弱模型容易敷衍(图 2:4 个 section 体积大、内容浅、读起来像水)

**解法**:title 完全自由,但用 schema 的 minLength 强约束**内容深度**。

**props 契约**:
```jsonc
{
  "type": "section_block",
  "props": {
    "title": "对音质的追求",            // 自由文本,3-6 字
    "summary": "为什么挑剔 HiRes 音质", // 一句话总结,8-25 字
    "body": "...",                       // 展开正文,30-100 字(强约束 minLength: 30)
    "evidence_quotes": [                 // 必填,至少 2 条
      { "quote": "我能听出小提琴的木头味", "source": "黄医生" },
      { "quote": "普通音质我现在听不下去", "source": "丁先生" }
    ],
    "full_width": false                  // 默认 false;true 时跨整宽
  }
}
```

**schema 强约束**(防敷衍):
- `title.minLength: 3`,`maxLength: 6`
- `summary.minLength: 8`,`maxLength: 25`
- **`body.minLength: 30`**(**关键**:防止"做放松"这种 3 字水帖)
- `body.maxLength: 100`(防止写一大坨)
- **`evidence_quotes.minItems: 2`**(每个段卡至少 2 条证据,UXR 可信度)
- `body` 必须包含**具体动作/具体场景/具体程度词**(prompt 层约束,无法纯 schema 校验,但 R*.md 会强调)

**为什么这能防图 2 那种敷衍**:
- 旧路径 LLM 写 "做放松、沉思和审美提升" 就过了 → 新路径 body < 30 字直接 reject,LLM 必须补具体内容
- 没 evidence_quotes → reject
- 在 prompt 里要求"body 不能只是抽象描述,必须含至少一个具体场景或行为"

### 4.3 section_blocks_grid 数量约束(解决拼贴不齐)

```jsonc
{
  "type": "section_blocks_grid",
  "props": {
    "blocks": [ /* section_block 数组 */ ],   // 数量必须是 4 / 5 / 6,见下方约束
    "full_width_index": null                    // 兼容旧字段;新数据直接在 block 内写 full_width: true
  }
}
```

- `blocks.minItems: 4`,`maxItems: 6`(schema 用 `oneOf` 拦截 4/5/6 之外或 full_width 数量错配)
- 三种合法组合:**4 块(允许 0/1/2 个 full_width)** / **5 块(必须恰好 1 个 full_width)** / **6 块(不允许 full_width)**
- `full_width_index` 兼容旧字段:可选指定某个 block 用 `.full-width`(核心共识/痛点段跨整宽)
- 如果 LLM 给了 3 个或不符合上述组合 → schema reject + runtime 二次校验提示详细规则

---

## 5. layout-2c-detail 组件(toC 专题详情 = toC 双页第二页,放 renderers/toc.py)

> **layout-2c-detail 是什么**:toC 的「双页第二页」,针对单画像的某条核心观点/期望做深入展开。
>
> **触发条件**(硬约束):
> 1. 主画像页 `layout-2c-portrait` 装不下时才触发(信息溢出,或某条观点强到必须单独展开)
> 2. **第二页左侧没有 identity_card**(不重复画像卡;读者已经在第一页看过)
> 3. 一个画像可以挂 1-N 张 detail 页(每张针对一个核心观点),nav 走 nav-pair(`画像名` + `› 专题 1`)
> 4. tab 总数上限按 visual-system.md §3.2 控制

| 组件名 | 用途 | CSS class | 现有渲染 |
|---|---|---|---|
| `detail_headline` | 顶部超大标题(画像核心观点,**≤30 字**) | `.l2c-headline` | 由 LLM 手写 |
| `detail_body` | 主体网格(左 mockup + 右 analysis)布局容器,不暴露给 LLM | `.l2c-body` | 同上 |
| `mockup_list` | 产品截图列表(用户截图槽 + 占位 fallback) | `.mockup-list` `.mockup-frame` `.mockup-frame::before` `.mockup-caption` `.mockup-img` | 同上 |
| `detail_analysis` | 右侧 2-3 段访谈解读(每段 body **≤220 字**) | `.l2c-analysis-section` `.l2c-analysis-title` `.l2c-analysis-body` | 同上 |
| `detail_illust_corner` | 角落头像(仅在用户提供 illust_path 文件存在时渲染;无图返回空字符串) | `.l2c-corner`(渲染为 `<img>`) | 同上 |

### 5.1 detail_illust_corner 渲染契约(P8 最终决策)

只渲染图片,不再用任何文字徽记 fallback。原因:文字徽记和真值样板一致性差,且没有用户头像时强行渲染单字会破坏 detail 页的安静风格。

```
有 illust_path 且 <项目运行目录>/画像头像素材/<filename> 存在 → 渲染 <img class="l2c-corner">
否则                                                            → 不渲染(返回空字符串)
```

> 历史三级 fallback(detail-corner.png → 头像 → 文字)已废弃。下方旧文档仅作历史保留。

<details>
<summary>历史 fallback(已废弃,不要遵循)</summary>

```
priority 1:  <项目运行目录>/画像头像素材/<画像名>-detail-corner.png   (用户专门给 detail 页准备的角落图)
       ↓ 不存在
priority 2:  <项目运行目录>/画像头像素材/<画像名>.png                  (复用画像头像)
       ↓ 不存在
priority 3:  不渲染 .l2c-corner                                         (空着,不占位)
```

LLM 不接触这个决策,Python 渲染时按顺序探测文件存在性。

</details>

### 5.2 mockup_list 截图槽与 tob_focus_cell 统一约定

- LLM 在 props 里给 `screenshot`(文件名)和 `caption`(说明文字)
- 命名规范:**所有截图槽字段统一叫 `screenshot`**(scenario_grid / mockup_list / tob_focus_cell / journey_cell_touchpoint 都用这个名)
- Python 检查 `<项目运行目录>/界面截图/<filename>`:
  - 存在 → 渲染 `<div class="mockup-frame mockup-frame--has-img"><img class="mockup-img">`；CSS **固定帧高** `--mockup-frame-height`,图 **`height:100%; width:auto; object-fit:contain`**(同行 mockup 等高、宽按比例、不裁切)
  - 不存在 → 渲染 `.mockup-frame::before` 占位图标 + caption + 提醒用户补图
- **素材**:每张单屏截图单独文件;源图宽高可不同,**不得**依赖渲染器裁合成条

### 5.3 内容深度约束

- `detail_headline.maxLength: 30`(中文 1 行不折)
- `detail_analysis_section.title.maxLength: 8`
- `detail_analysis_section.body.minLength: 50`,`maxLength: 220`(每段不水也不堆)
- `detail_analysis.sections.minItems: 2`,`maxItems: 3`

---

## 6. layout-2c-journey 组件(toC 旅程,放 renderers/toc_journey.py)

> **关键约束**:LLM 永远不输出 SVG 字符串;LLM 永远不输出 emoji 字符。SVG path 和 emoji 表情**全部由 Python 算 / Python 查表**。这能彻底消灭"情绪曲线超界"和"Codex 没 emoji 能力"两个问题。

整张 toC 旅程作为**一个容器组件 `journey_2c`**(props 含 stages + dimensions + cells + emotion 二维数据),内部由 Python 拆成下面这些子结构渲染。LLM 只填一个 `journey_2c`,不分别填 7 个小组件。

| 组件名(LLM 视角) | 用途 | CSS class | 现有渲染 |
|---|---|---|---|
| `journey_2c` | **整张旅程容器**(LLM 只填这一个) | 见下方所有子 class | 由 LLM 手写,P8 改 Python |

| 内部子结构(Python 渲染细节,LLM 不接触) | CSS class |
|---|---|
| journey_header | `.journey-header` `.journey-title` `.journey-subtitle` |
| journey_grid | `.journey-grid` (`--journey-stages` 控制列数) |
| journey_stage_header | `.journey-cell.journey-stage-header` `.journey-stage-number` |
| journey_dimension_label | `.journey-cell.journey-dimension-label` |
| journey_cell | `.journey-cell` `.journey-cell-keyword` `.journey-cell-summary` `.journey-cell-touchpoint` `.touchpoint-tag` |
| journey_pain_highlight | `.journey-pain-highlight` `.journey-pain-opportunity-tag` |
| journey_emotion_row | `.journey-emotion-row` `.journey-emotion-svg` `.emotion-area` 等 |

### 6.1 journey_2c props 契约

```jsonc
{
  "type": "journey_2c",
  "props": {
    "title": "用户旅程 — 深听场景派",
    "subtitle": "阶段:发现 / 试听 / 开通 / 使用 / 续费",
    "illust_path": "深听场景派.png",
    "stages": ["发现", "试听", "开通", "使用", "续费"],   // 4-6 个
    "dimensions": ["思考", "行为", "触点", "痛点"],       // 包含"情绪"则自动加情绪曲线行
    "cells": [
      [
        // dimension 0 (思考)
        { "keyword": "好奇音质", "summary": "听说 HiRes 是高品质,想验证一下" },
        { "keyword": "...", "summary": "..." }
      ],
      [ /* dimension 1 (行为) */ ],
      [ /* dimension 2 (触点) */ ],
      [
        // dimension 3 (痛点)— Python 检查 frequency 自动应用 highlight
        { "keyword": "曲库少", "summary": "找不到熟悉曲目", "frequency": "5/5" }
      ]
    ],
    "emotion": [
      // 5 个阶段每个一个情绪标签 + 高低
      { "label": "略好奇", "level": "high",   "mood": "curious" },
      { "label": "困惑",   "level": "low",    "mood": "confused" },
      { "label": "满意",   "level": "high",   "mood": "happy" },
      { "label": "稳定",   "level": "middle", "mood": "calm" },
      { "label": "纠结",   "level": "low",    "mood": "frustrated" }
    ]
  }
}
```

### 6.2 SVG 情绪曲线由 Python 算,LLM 永不接触(解决你的「超界」担忧)

旧路径 LLM 写 SVG 字符串 `<path d="M 0 40 Q 100 10, 200 50 T 400 30 T 500 60">` 经常超 viewBox。

新路径:
- LLM 只给每阶段的 `level: "high" | "middle" | "low"`(3 档,枚举)
- Python 按 viewBox 500×80,把 high=20、middle=40、low=60 映射成 y 坐标
- Python 用 `Q ... T ...` 算平滑曲线 path,**保证所有点在 [0, viewBox] 范围内**
- 渲染单元测试覆盖边界 case(所有 high / 所有 low / 交替),所有 case 不超界

### 6.3 emoji 内置图片库(解决 Codex 无 emoji 能力)

**问题(你提的)**:codex 没法调用 emoji 字符,即使弱模型支持,各模型的 emoji 映射也不统一。

**解法**:`assets/icons/emoji/` 内置 **33 个** PNG/SVG 表情图(每个 32×32px,文件大小约 2-4KB,33 个合计 <120KB,可忽略)。LLM 给语义名,Python 查表渲染。

#### 33 个内置 emoji 图(分 6 类,**不限定一个表情只能用于一种情绪**)

```
assets/icons/emoji/
─── 笑脸 / 愉悦类 (8) ───
├── smile.png            🙂   微笑(轻度愉悦,日常)
├── smile_blush.png      😊   带腮红微笑(温暖,被照顾感)
├── grin.png             😀   咧嘴笑(明显高兴)
├── laughing.png         😄   大笑(很愉快)
├── content.png          😌   满意闭眼(心满意足)
├── relaxed.png          ☺️   放松(轻舒展)
├── proud.png            😎   墨镜自得(自豪 / 满足身份)
├── star_struck.png      🤩   星星眼(超喜欢 / 惊艳)
─── 困惑 / 思考类 (5) ───
├── thinking.png         🤔   手托下巴(思考决策)
├── confused.png         😕   皱眉(没搞懂)
├── raised_eyebrow.png   🤨   挑眉(怀疑 / 评估)
├── neutral.png          😐   平静脸(不置可否 / 等待)
├── hmm.png              🙄   翻白眼(不耐烦轻度)
─── 消极 / 负面类 (7) ───
├── frowning.png         😦   皱眉张嘴(担忧)
├── disappointed.png     😞   失望低头(预期落空)
├── frustrated.png       😩   龇牙皱眉(沮丧 / 卡住)
├── persevere.png        😣   咬牙坚持(挣扎)
├── tired.png            😪   倦怠(疲惫 / 提不起劲)
├── sad.png              🙁   不开心(轻度负面)
├── crying.png           😢   流泪(明确难过)
─── 惊讶 / 强反应类 (3) ───
├── surprised.png        😯   小惊讶(意料之外)
├── shocked.png          😲   大惊(强反应)
├── exclamation.png      ❗   感叹号(关键瞬间 / 突发)
─── 兴奋 / 积极类 (4) ───
├── excited.png          🤩   兴奋(高能量,搭高 level)
├── celebrate.png        🎉   庆祝(节点完成)
├── fire.png             🔥   火(热门 / 强烈)
├── heart_eyes.png       😍   心眼(被打动)
─── 物品 / 隐喻类 (6) ───
├── headphone.png        🎧   耳机(沉浸听 / 稳定使用)
├── light_bulb.png       💡   灯泡(机会点 / 顿悟,给 pain_opportunity_tag 用)
├── target.png           🎯   靶心(目标达成 / 决心)
├── thumbs_up.png        👍   赞(认可)
├── thumbs_down.png      👎   反对(否定)
└── question.png         ❓   问号(疑问 / 不确定)
```

#### LLM 决策契约(不限定一对一)

LLM 在 props 里给 `emoji` 字段,**取 33 个枚举之一**(schema 强约束):

```jsonc
"emotion": [
  { "stage_label": "好奇", "level": "high",   "emoji": "thinking" },     // 思考类
  { "stage_label": "困惑", "level": "low",    "emoji": "confused" },     // 困惑类
  { "stage_label": "满意", "level": "high",   "emoji": "content" },      // 愉悦类
  { "stage_label": "稳定", "level": "middle", "emoji": "headphone" },    // 物品隐喻
  { "stage_label": "纠结", "level": "low",    "emoji": "persevere" }     // 消极类
]
```

**LLM 自由配对**:
- 同一情绪可以选不同 emoji(「满意」可以选 `content` 也可以选 `proud` 也可以选 `smile_blush`,看画像调性)
- 同一 emoji 可以用于不同语境(`headphone` 既是「沉浸听」也是「日常稳定使用」)
- LLM 根据画像气质 + 阶段叙事自由选,Schema 只校验是否在 33 枚举内

#### 兜底 case

- LLM 给了不在枚举的 emoji 名 → schema reject
- 文件不存在 → CSS 兜底:`.emotion-label:not(:has(.emoji))::before { content: "·" }`(P7 加固已有),不空白
- 强模型支持 Unicode emoji 也走同一套图(统一视觉,不再依赖模型能力)

#### 设计成本评估

- 33 个 PNG @ 32×32 + 32×32@2x = 单文件 ~3.5KB,合计 < 120KB(忽略不计)
- 可以用 OpenMoji / Twemoji / Fluent Emoji 开源 SVG 直接转 PNG,1 小时完成
- 也可以让用户提供品牌定制 emoji(后续可换)

#### LLM 选择 emoji 的指导原则(写进 paradigms 提示)

1. 优先按**画像调性**:艺术画像选愉悦/思考类多,实用画像选物品隐喻类多
2. 同一旅程内 emoji 应有变化,不要 5 个 stage 都用同一个
3. emoji 的**情绪强度**应该与 `level` 匹配:
   - `level: high` + 强 emoji(`laughing` / `excited` / `star_struck` / `heart_eyes`)
   - `level: middle` + 中性 emoji(`smile` / `neutral` / `thinking`)
   - `level: low` + 负面 emoji(`frustrated` / `tired` / `disappointed` / `crying`)

> **注**:33 张 emoji 图设计可以延后到 B 阶段。A.1 阶段只锁定 33 个枚举名 + 文件路径约定。
> Codex 不需要画图,只在 renderer 里写 `EMOJI_VALID_SET = {"smile", "smile_blush", ...}` 校验集 + `<img src="assets/icons/emoji/{emoji}.png" class="emoji">` 渲染。

### 6.4 其他约束

- `stages.minItems: 4`,`maxItems: 6`
- `dimensions` 必含「思考、行为、痛点」,可选「触点、情绪」
- 单 cell `keyword.maxLength: 5`,`summary.maxLength: 25`
- `cells[dim][stage].frequency` 可选,格式 `"N/N"`,Python 解析后 ≥60% 自动应用 `.journey-pain-highlight`(LLM 不直接选 type)
- 触点 cell 截图槽统一约定:`<项目运行目录>/界面截图/touchpoint-<persona_id>-<stage_idx>.png`

---

## 7. layout-matrix-2d 组件(R4 2D 矩阵,放 renderers/matrix.py)

### 7.0 R4/R5 总览 + 子页 × research_type(2026-05-29)

`layout-matrix-2d` / `layout-distribution-multi` 为 **theme-neutral 结构**(DOM 共用),配色由 `<html data-theme>` + design tokens 驱动。总览 slide **禁止**画像/旅程组件(`P8-OVERVIEW-FORBIDDEN-COMPONENT`)。

| 范式 | 总览 layout + 容器组件 | toC 子页画像 | toC 子页旅程 | toB 子页画像 | toB 子页旅程 |
|------|------------------------|--------------|--------------|--------------|--------------|
| R4 | `layout-matrix-2d` + `matrix_2d` | `layout-2c-portrait` | `journey_2c` | `layout-2b-grid` | `tob_journey_l2` |
| R5 | `layout-distribution-multi` + `distribution_multi` | `layout-2c-portrait` | `journey_2c` | `layout-2b-grid` | `tob_journey_l2` |

**R4 子页组件对照**:

| 维度 | toC (`theme=2c`) | toB/toD (`theme=2b`/`2d`) |
|------|------------------|---------------------------|
| 画像身份 | `identity_card` | `identity_panel` |
| 画像正文 | `section_blocks_grid` | `resp_rings` / `painpoint_list` / `scenario_grid` / `ai_scenario_grid` 等 |
| 旅程 layout | `layout-2c-journey` | `layout-2b-journey` `.is-l2` |
| 校验 | `P8-JOURNEY-CELLS-SHAPE` | `P8-THEME-LAYOUT-MISMATCH` |

**R5 子页**:与上表「子页」列相同;详见 §8.0。

> **关键约束**:LLM 不接触受访者点的 `label_direction`,不接触 SVG 坐标。Python 按算法自动避让。

整张矩阵作为**一个容器组件 `matrix_2d`**(props 含轴、象限、受访者列表),Python 内部生成所有 dot + label + 自动选方向。LLM 只填一个 `matrix_2d` + 顶部一个独立的 `matrix_guidance_strip`。

| 组件名(LLM 视角) | 用途 | CSS class |
|---|---|---|
| `matrix_guidance_strip` | 矩阵上方研究问题引导条(独立组件) | `.matrix-guidance-strip` `.matrix-guidance-item` `.decision-strip` |
| `matrix_2d` | **矩阵容器**(含轴 + 4 象限 + N 个受访者) | 见下方所有子 class |

| 内部子结构(Python 渲染细节,LLM 不接触) | CSS class |
|---|---|
| matrix_container | `.matrix-container` |
| matrix_axis | `.matrix-axis.horizontal` `.matrix-axis.vertical` |
| matrix_axis_label | `.matrix-axis-label.top/.bottom/.left/.right` |
| matrix_quadrant_label | `.matrix-quadrant.q{1..4}` `.matrix-quadrant-label` |
| matrix_respondent_dot + label | `.matrix-respondent-dot` `.respondent-label` + 7 方向类 |
| matrix_empty_quadrant | `.matrix-empty-quadrant`(斜纹背景 + "本研究样本未覆盖") |

### 7.1 matrix_2d props 契约

```jsonc
{
  "type": "matrix_2d",
  "props": {
    "axis_labels": {
      "top":    "生活场景触发",   // ≤8 字硬约束(防纵轴下方超界)
      "bottom": "找歌目标驱动",   // ≤8 字
      "left":   "价值概念薄弱",   // ≤8 字
      "right":  "价值感知清晰"    // ≤8 字
    },
    "quadrants": [
      {
        "id": "persona-1",       // 必须能在 personas 数组里找到对应画像 slide(layout-2c-portrait 或 layout-2b-grid)
        "label": "深听场景派",   // ≤5 字硬约束(SKILL.md 约束 10)
        "position": "q1",        // q1=右上 / q2=左上 / q3=左下 / q4=右下
        "is_empty": false        // true 时本象限渲染 .matrix-empty-quadrant 斜纹
      },
      { "id": "persona-q3", "position": "q3", "is_empty": true }
    ],
    "respondents": [
      {
        "x": 82, "y": 25,                    // 0-100% 坐标,Python 不重排
        "display_name": "黄医生",            // 脱敏名,禁止「受访者1」(schema pattern 拦截)
        "quadrant_persona": "深听场景派",
        "label_direction": "label-right",    // 可选,7 方向枚举;不填时 renderer 按受访者顺序在 7 方向中轮转避让
        "evidence": [                        // 严格 2 条:体现 X 轴 / Y 轴 特征
          { "quote": "有可能每天都听,3-4 天写少了", "source": "黄医生" },
          { "quote": "睡觉前一小时定时关闭", "source": "黄医生" }
        ]
      }
    ]
  }
}
```

### 7.2 空象限置灰契约(P8 新增,你图 3 的样式)

`is_empty: true` 时,该象限渲染:
- 斜纹背景:`background: repeating-linear-gradient(45deg, var(--color-bg-card-soft), var(--color-bg-card-soft) 8px, transparent 8px, transparent 18px)`
- 居中圆角胶囊文字「本研究样本未覆盖」(`.matrix-empty-quadrant > .empty-tag`)
- 不渲染 quadrant_label(没必要点开)
- 不放任何 respondent_dot

CSS 需要 B 阶段补 `.matrix-empty-quadrant` 样式(已登记 §14 联动清单)。

### 7.3 受访者点 vs 标签 距离固定(解决「宽的窄的真的很难看」)

旧路径 LLM 给 `style="--label-dx:0px; --label-dy:-10px"`,**这些 inline var 是变量,值不一致导致视觉乱**。

新路径:LLM **完全不接触 dx/dy**,只给 `x` `y`。Python 算法:
1. 收集本象限所有受访者点位(按 y 升序)
2. 按象限位置自动分配方向(贪心:选距离已占用 label 最远的方向)
3. 每个方向类的偏移用 CSS 常量(不是 inline var):
   - `label-right: dx=18px, dy=0px`
   - `label-left: dx=-18px, dy=0px`
   - `label-top: dx=0px, dy=-22px`
   - `label-bottom: dx=0px, dy=22px`
   - `label-top-right: dx=14px, dy=-16px`
   - `label-bottom-right: dx=14px, dy=16px`
   - `label-bottom-left: dx=-14px, dy=16px`
4. 这些常量在 `_components.css` 里 hard-code(已登记 §14 联动清单)

视觉上所有点-label 距离统一。

### 7.4 axis_label 防超界

- 4 端 label 各 `maxLength: 8` 中文字符(防长字符串超出容器)
- CSS 设置 `.matrix-axis-label` `max-width: 200px; white-space: nowrap`(已在 _components.css)
- schema reject 超字情况

### 7.5 respondent_label 命名硬拦截

- `display_name` schema pattern:`^(?!受访者\\d+).*$`
- 不允许「受访者1」「受访者2」(SKILL.md 约束 8)
- 必须用「姓氏+身份」「姓氏+先生/女士」「姓氏 +*」「U1」之一

---

## 8. layout-distribution-multi 组件(R5 多维分布,放 renderers/distribution.py)

### 8.0 R5 子页 × research_type

分布总览 `layout-distribution-multi` 与 R4 矩阵总览同理:**结构共用,仅 theme 配色**。点击图例/类别 tab 后的子页见 §7.0 总表 — toC 用 `layout-2c-portrait` + `journey_2c`; toB 用 `layout-2b-grid` + `tob_journey_l2`。

> **关键约束**:LLM 完全不接触 SVG 坐标。同上下文档,整张图是**一个容器 `distribution_multi`**。

| 组件名(LLM 视角) | 用途 |
|---|---|
| `distribution_multi` | **整张分布图容器**(LLM 只填这一个) |

### 8.1 distribution_multi props 契约

```jsonc
{
  "type": "distribution_multi",
  "props": {
    "title": "4 类画像 × 4 个区分点 — 谁在哪里?",
    "subtitle": "这张图是几类用户在多个区分点上的横向对比",
    "footer_hint": "点画像图例可单独突出某一类的折线",
    "value_variables": [   // 3-5 个区分点
      {
        "name": "价值感知清晰度",
        "levels": [   // 必须 3 档:高/中/低
          { "level": "high",   "name": "能描述差异" },
          { "level": "middle", "name": "只感觉清晰" },
          { "level": "low",    "name": "完全靠想象" }
        ]
      }
    ],
    "personas": [   // N 类画像(2-5 个)
      {
        "id": "persona-1",
        "name": "内行深听派",
        "color": "#7BA8C9",                // 与 accent token 对应
        "positions": [                     // 每个 value_variable 上的档位
          { "variable_idx": 0, "level": "high" },
          { "variable_idx": 1, "level": "middle" },
          { "variable_idx": 2, "level": "middle" },
          { "variable_idx": 3, "level": "high" }
        ],
        "respondents": ["黄医生"]          // 该画像下的受访者(脱敏名)
      }
    ]
  }
}
```

### 8.2 档位名标在点位旁边,不在底部(P8 修订,你的反馈)

旧版样板把档位名(`能描述差异 / 只感觉清晰 / 完全靠想象`)放在 chart 底部 `.snake-axis-x-sublabel`,阅读时眼睛要跳上跳下。

**新版**:档位名直接标在 chart 内每条折线经过的对应点旁边:
- 高档点(y=高) → label 标在点**上方** 12px
- 中档点(y=中) → label 标在点**右侧** 14px(与点同水平)
- 低档点(y=低) → label 标在点**下方** 12px
- 底部只保留区分点主标题(`.snake-axis-x-label`),sublabel(档位枚举名)删掉

CSS 改:删 `.snake-axis-x-sublabel`,新增 `.snake-point-level-label`(已登记 §14 联动清单)。

### 8.3 同坐标多用户聚合 evidence(P8 修订,你的反馈)

当同一坐标点有 2+ 用户(同画像不同人,或同档位不同画像):
- 渲染时 Python 检测同坐标,**合并 `data-evidence`**
- 用 `\n\n` 分隔多个用户块(_base.html tooltip JS 已支持多块解析)
- 每个用户块的格式:`画像名 / 用户名 \n"原话1"\n"原话2"`
- hover 上去显示全部用户和各自原话

### 8.4 区分点数量约束

- `value_variables.minItems: 3`,`maxItems: 5`
- 每个 `levels` 必须恰好 3 档(high/middle/low),不允许 4 档或 2 档
- `personas.minItems: 2`,`maxItems: 5`

---

## 9. 组件总数 + LLM 可填 type 总数(用户第二轮反馈后)

### 9.1 REGISTRY 列出的所有组件(CSS/Python renderer 粒度)

| 类别 | 组件数 |
|---|---|
| 共享(shared) | 3(report_meta_bar / persona_nav / persona_illust) |
| layout-2b-grid | 11(identity_panel + grid_module + 9 body) |
| layout-2b-grid-detail | **新增 1**(layout 容器自身,内部 body 复用 2b-grid 的) |
| layout-2b-journey | 7 |
| layout-2c-portrait | 4 |
| layout-2c-detail | 5 |
| layout-2c-journey | 7(子结构,被 journey_2c 吃掉) |
| layout-matrix-2d | 8(子结构,被 matrix_2d 吃掉) |
| layout-distribution-multi | 4(子结构,被 distribution_multi 吃掉) |
| **合计 REGISTRY 项** | **50** |

### 9.2 LLM 实际可在 JSON 里填的顶层 type(精确清单,A.3 据此写 Schema)

> 当前 24 个允许的顶层 type(P8 删除了 task_freq_list / section_block / layout_2b_grid_detail / layout_2c_detail / nav_trio,见各组件章节)。

| # | type | 所属 layout | 难度(谁写 renderer) |
|---|---|---|---|
| 1 | `identity_panel` | 2b-grid / 2b-grid-detail | ★ |
| 2 | `resp_rings` | 2b-grid / 2b-grid-detail | ★★★(SVG 弧度) |
| 3 | `collab_flow` | 2b-grid / 2b-grid-detail | ★★★(流程箭头) |
| 4 | `scenario_grid` | 2b-grid / 2b-grid-detail | ★★(两种形态切换) |
| 5 | `ai_scenario_grid` | 2b-grid / 2b-grid-detail | ★★(.is-ai 修饰) |
| 6 | `painpoint_list` | 2b-grid / 2b-grid-detail | ★ |
| 7 | `titled_list` | 2b-grid / 2b-grid-detail | ★ |
| 8 | `generic_text` | 2b-grid / 2b-grid-detail | ★ |
| 9 | `generic_bullet` | 2b-grid / 2b-grid-detail | ★ |
| 10 | `generic_kv` | 2b-grid / 2b-grid-detail | ★ |
| 11 | `tob_journey_l1` | 2b-journey | ★★★(UML DSL,几何由 Python 算) |
| 12 | `tob_journey_l2` | 2b-journey | ★★★(UML DSL + focus 截图槽) |
| 13 | `identity_card` | 2c-portrait | ★★(灵活 meta_tags) |
| 14 | `persona_quote_pull` | 2c-portrait / 2c-detail | ★ |
| 15 | `section_blocks_grid` | 2c-portrait | ★★(4/5/6 拼贴,schema oneOf) |
| 16 | `detail_headline` | 2c-detail | ★ |
| 17 | `mockup_list` | 2c-detail | ★★(截图槽 fallback) |
| 18 | `detail_analysis` | 2c-detail | ★ |
| 19 | `detail_illust_corner` | 2c-detail | ★(仅图片;无图不渲染) |
| 20 | `journey_2c` | 2c-journey | ★★★(SVG 曲线 + emoji 查表) |
| 21 | `matrix_guidance_strip` | matrix-2d | ★ |
| 22 | `matrix_2d` | matrix-2d | ★★★(7 方向 label 自动避让 + 空象限) |
| 23 | `distribution_multi` | distribution-multi | ★★★(snake 折线 SVG + 档位 label 定位) |
| 24 | `section_block` | section_blocks_grid 子项(schema 单独维护,顶层 enum 不允许) | ★ |

> `section_block` 既是 grid 子项的 schema,也保留 schema 文件供 grid 引用;但 report.json 顶层 enum **不**允许它直接出现。实际 LLM 顶层可填的是 23 个 type + 1 个内嵌 schema。

**汇总**:
- 主对话写:**7 个 ★★★ renderer**(resp_rings / collab_flow / tob_journey_l1 / tob_journey_l2 / journey_2c / matrix_2d / distribution_multi)
- 主对话写:**1 个 grid_solver**(关键算法)
- 主对话写:**1 个顶层 render_report**(slot 填充 + CSS 随包 + validator 接入)
- Codex 写:**15 个 ★ / ★★ renderer**(都是字符串拼装,模式高度一致)
- Codex 写:**24 个 schema 文件**(批量按模板填)
- Codex 写:**所有单元测试**(每个 renderer ≥ 2 个 case)

按这分工 Codex 不碰任何几何 / SVG / 算法,只做最机械的字符串拼装 + escape。代码能力风险拉到最低。

> 设计权衡:若把 identity_panel 的 5 个子结构、journey_grid 的 5 个子单元拆分得更细,总数可逼近 60。当前粒度选择「每个组件对应一个 LLM 决策的最小单元」—— 比如 identity_panel 整合 5 个内部块(LLM 不需要单独决定哪个块在哪),保持 props 紧凑。

---

## 10. 7 个 layout 的 ASCII 字符画对照表

> 用每张图标注组件 type 名,与上面表格 1:1 对应。LLM 看图就能定位"我要填哪些组件、放在哪"。

---

### 10.1 layout-2b-grid(toB/toD 单画像单页)

**关键**:LLM 不写坐标,只列组件;Layout solver(§13)按下方优先级 + 估高度自动排,保证 12 列网格无缺口。

```
┌────────────────────── persona-slide.layout-2b-grid ──────────────────────────┐
│                                                                              │
│ ┌─ identity-panel(30%)─┐ ┌──── modules-panel(70%,12 col × 3 row)────────┐ │
│ │                      │ │ row 1                                             │ │
│ │ persona_avatar       │ │ ┌── grid_module(resp_rings)──┐ ┌─ grid_module ─┐ │ │
│ │ identity_name        │ │ │ ◯ 职责环图 SVG × N         │ │ collab_flow   │ │ │
│ │ identity_desc        │ │ └────────────────────────────┘ │ 上游→自→下游 │ │ │
│ │ identity_meta_rows   │ │                                 │ + KPI 块      │ │ │
│ │ one_sentence_need    │ │                                 └───────────────┘ │ │
│ │                      │ │ row 2                                             │ │
│ │ (左栏 5 子结构由      │ │ ┌── grid_module(titled_list)───────────────────┐ │ │
│ │  identity_panel 整   │ │ │ ▸ 任务名 [每日] → 流程描述                    │ │ │
│ │  合成一个组件)        │ │ └────────────────────────────────────────────────┘ │ │
│ │                      │ │ ┌── grid_module(scenario_grid)─────────────────┐ │ │
│ │                      │ │ │ 标题:典型业务场景                              │ │ │
│ │                      │ │ │ ┌─scene_card─┐┌─scene_card─┐┌─scene_card─┐ │ │ │
│ │                      │ │ │ │[截图/占位] ││[截图/占位] ││[截图]     │ │ │ │
│ │                      │ │ │ │ 场景描述    ││ 场景描述    ││ 场景描述   │ │ │ │
│ │                      │ │ │ │ □工具A □系统││ □工具C     ││ □工具D    │ │ │ │
│ │                      │ │ │ └────────────┘└────────────┘└───────────┘ │ │ │
│ │                      │ │ └────────────────────────────────────────────────┘ │ │
│ │                      │ │ row 3                                             │ │
│ │                      │ │ ┌── grid_module(ai_scenario_grid)──────────────┐ │ │
│ │                      │ │ │ ✨ 标题:AI 场景/需求(.is-ai)                 │ │ │
│ │                      │ │ │ (与 scenario_grid 同形,大量 AI 提及时启用) │ │ │
│ │                      │ │ └────────────────────────────────────────────────┘ │ │
│ │                      │ │ ┌── grid_module(painpoint_list)────────────────┐ │ │
│ │                      │ │ │ ● 痛点标题 (n/N)                              │ │ │
│ │                      │ │ │   细节描述                                    │ │ │
│ │                      │ │ └────────────────────────────────────────────────┘ │ │
│ └──────────────────────┘ └───────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

字段优先级(从上到下,Layout solver 据此排序):
  ① resp_rings(核心职责)        ② collab_flow(上下游 + KPI)
  ③ titled_list(高频任务/通用列表)  ④ scenario_grid(典型业务场景,含工具/系统标签)
  ⑤ ai_scenario_grid(AI 场景)  ⑥ painpoint_list(核心痛点)
  ⑦ 兜底 titled_list / generic_text / generic_bullet / generic_kv

🗑️ 已删除:
  - system_grid(业务系统并入 scenario_grid 的 tools 标签)
  - fault_list(运维特有,通用画像不需要,改用 titled_list 兜底)
```

---

### 10.2 layout-2b-journey(toB 旅程 — 含 .is-l1 全景 / .is-l2 单角色 两种形态)

**P8 视觉升级**:
- 子阶段 `▭▷` 箭头形(强表流程顺序,避免被误读为工具标签)
- L2 关注点卡片留截图槽

> ⚠️ **下面这张 ASCII 图是旧 P7「flows 胶囊」模型,只看版式占位,别照它的数据模型写。**
> 它把每个角色画成一条独立的 `◯flow ─→ ◯flow` 横向链 —— 这正是 2026-05-29「5 条平行流水线」翻车的错误心智!
> P8 真实数据契约是 `nodes`/`edges` UML DSL(见 §3.3):角色是泳道,任务是落在 (lane, stage) 里的节点,
> **跨角色靠「from/to 在不同 lane」的 edge 织在一起**,没有独立的 `cross_role_arrow` 组件。协同硬下限见 §3.0.1。

```
┌──────────── persona-slide.layout-2b-journey.is-l1(全景) ──────────────────────┐
│                                                                                │
│  ┌──────── tob_banner ────────────────────────────────────┐                    │
│  │  ◤ 多角色全景                                          │                    │
│  │     从需求输入到发布运维的多角色协作链路              │                    │
│  └────────────────────────────────────────────────────────┘                    │
│                                                                                │
│  ┌── tob_rail ──┐┌── tob_main(stages × roles)──────────────────────────────┐  │
│  │ 阶段          ││ ① 持续规划    ② 构建测试    ③ 集成交付    ④ 部署运维    │  │
│  │ ─────────────── tob_stage_header(.tob-stage-tag,深蓝填充) ───────────    │  │
│  │ 子阶段        ││[需求输入▷][范围确认▷][项目准备▷]  [代码规则▷][测试设计▷] │  │
│  │ ──────── tob_substage_row(.tob-substage-arrow,浅色背景+右尖三角)──── │  │
│  │ 角色1 卢女士   ││ ◯flow ─→ ◯flow ─→ ◯flow ─→ ◯is-terminal               │  │
│  │ (运维管理)     ││           ↘ tob_cross_role_arrow(协作长箭头)            │  │
│  │ 角色2 李女士   ││ ◯flow ─→ ◯flow ─→ ◯flow ─→ ◯is-terminal               │  │
│  │ (Scrum Master) ││           ↘                                            │  │
│  │ 角色3 ...      ││ ◯flow ─→ ◯flow ─→ ◯flow ─→ ◯is-terminal               │  │
│  │ 角色4 ...      ││ ◯flow ─→ ◯flow ─→ ◯flow ─→ ◯is-terminal               │  │
│  │ ────── tob_flow_cell(单 cell≤22字),data-evidence 挂在 pill 上 ───── │  │
│  └────────────┘└────────────────────────────────────────────────────────────┘  │
│                                                                                │
│ 注[旧模型,已废弃]:跨角色连接 P8 不再是 overlay 长箭头,而是 nodes/edges 里     │
│     一条 from/to 在不同 lane 的普通 edge(正交连线由 Python 算)。见 §3.3        │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────── persona-slide.layout-2b-journey.is-l2(单角色) ────────────────────┐
│                                                                              │
│  ┌──── tob_banner ────────┐                                                  │
│  │ ◤ DevOps 规则管理员    │                                                  │
│  │   运维管理 · 单角色旅程│                                                  │
│  └────────────────────────┘                                                  │
│                                                                              │
│  ┌── tob_rail ──┐┌── tob_main(stages × dimensions)──────────────────────┐   │
│  │ 阶段         ││ ① 持续规划    ② 构建    ③ 集成    ④ 部署              │   │
│  │ 子阶段       ││[需求输入▷][范围确认▷]   [代码规则▷]   [流水线▷]      │   │
│  │ 工作流程     ││ ◯flow≤22 ─→ ◯flow ─→ ◯flow ─→ ◯is-terminal          │   │
│  │ 关注点/痛点  ││┌─focus_cell─┐ ┌─focus──┐ ┌─focus──┐ ┌─focus.is-pain┐│   │
│  │              │││[截图槽/占位]│ │[截图]  │ │[截图]  │ │  ⚠ 痛点标题   ││   │
│  │              │││ ★ 关注点 1 │ │ 关注点 │ │ 关注点 │ │  痛点细节描述  ││   │
│  │              │││ 一句话描述 │ │ ...    │ │ ...    │ │               ││   │
│  │              │││ (有截图时  │ │        │ │        │ │ (痛点卡片无    ││   │
│  │              │││  渲染图)   │ │        │ │        │ │  截图槽)       ││   │
│  │              ││└───────────┘ └────────┘ └────────┘ └───────────────┘│   │
│  └─────────────┘└────────────────────────────────────────────────────────┘   │
│                                                                              │
│ 注:focus_cell 截图槽路径 = <项目运行目录>/界面截图/focus-<persona>-<stage>.png│
│     没传图自动渲染 mock.is-empty + props.description 一句话描述               │
│     痛点卡片(.is-pain) 不需要截图槽                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.3 layout-2c-portrait(toC 单画像主页)

```
┌────────────────── persona-slide.layout-2c-portrait ──────────────────────────┐
│                                                                              │
│  ┌─ identity_card (32%) ───┐ ┌─────── persona_quote_pull (跨 2 列)──────────┐ │
│  │                         │ │ ❝ 标志性引用句 ...                            │ │
│  │  persona_illust         │ │   — 受访者代号                                │ │
│  │ (img 或 placeholder)    │ └──────────────────────────────────────────────┘ │
│  │                         │                                                  │
│  │  persona_name_anchor    │ ┌─── section_blocks_grid (右下,2 列拼贴) ─────┐ │
│  │   "深听场景派"          │ │ ┌─ section_block ─┐ ┌─ section_block ─┐    │ │
│  │  persona_subtitle       │ │ │ ▢ 标题(胶囊)  │ │ ▢ 标题           │   │ │
│  │   "已经把 HiRes ..."    │ │ │ 一句话总结      │ │ 一句话总结        │   │ │
│  │                         │ │ │ 展开正文        │ │ 展开正文          │   │ │
│  │  meta_tags_list         │ │ │ (data-evidence) │ │                   │   │ │
│  │  ┌───┐┌───┐┌───┐┌───┐   │ │ └─────────────────┘ └───────────────────┘   │ │
│  │  │代表││身份││设备││... │ │                                              │ │
│  │  └───┘└───┘└───┘└───┘   │ │ ┌─ section_block ─┐ ┌─ section_block ─┐    │ │
│  │                         │ │ │ ...             │ │ ...             │    │ │
│  └─────────────────────────┘ │ └─────────────────┘ └─────────────────┘    │ │
│                              │                                              │ │
│                              │ ┌─── section_block.full-width ────────────┐ │ │
│                              │ │ 跨整宽段(如核心共识/痛点合并)         │ │ │
│                              │ └──────────────────────────────────────────┘ │ │
│                              └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

注:section_block 必须 3 层结构(title + summary + body),不允许只 2 层。
```

---

### 10.4 layout-2c-detail(toC 专题详情)

```
┌──────────────── persona-slide.layout-2c-detail ──────────────────────────────┐
│                                                                              │
│  ┌──────────────── detail_headline (大标题,跨整宽) ──────────────────────┐  │
│  │  专区内听歌类型更为多样,期待增添更多终曲音乐                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────── detail_body (左:mockup,右:analysis) ────────────┐   │
│  │  ┌─── mockup_list ───┐  ┌─── detail_analysis ──────────────────┐  │   │
│  │  │  ┌─ mockup_frame ─┐│  │  detail_analysis_section            │  │   │
│  │  │  │  □ 场景截图占位 ││  │  ▸ 标题                              │  │   │
│  │  │  │   (无截图时图标)││  │    主体正文(可含 <strong>)         │  │   │
│  │  │  └─ mockup_caption ─┘│  │                                      │  │   │
│  │  │  ┌─ mockup_frame ─┐│  │  detail_analysis_section             │  │   │
│  │  │  │  □ 第二张占位   ││  │  ▸ 标题                              │  │   │
│  │  │  └────────────────┘│  │    主体                              │  │   │
│  │  └────────────────────┘  └──────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│                                                  ┌── detail_illust_corner ─┐ │
│                                                  │     ◐  小人物呼应插画   │ │
│                                                  └─────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.5 layout-2c-journey(toC 旅程)

```
┌──────────────── persona-slide.layout-2c-journey ─────────────────────────────┐
│                                                                              │
│  ┌───────────── journey_header ──────────────────────────────────────────┐   │
│  │  ◐ 头像                                                                │   │
│  │   journey_title: "用户旅程 — 深听场景派"                              │   │
│  │   journey_subtitle: "阶段:发现 / 试听 / 开通 / 使用 / 续费"           │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────── journey_grid (col=stages+1, row=dims+2) ─────────────────┐   │
│  │ [维度]    │ ① 发现   │ ② 试听   │ ③ 开通   │ ④ 使用   │ ⑤ 续费     │   │
│  │  ─────────┼──────────┼──────────┼──────────┼──────────┼─────────── │    │
│  │ 思考      │ keyword  │ keyword  │ ...      │ ...      │ ...        │   │
│  │           │ summary  │ summary  │          │          │            │   │
│  │  ─────────┼──────────┼──────────┼──────────┼──────────┼─────────── │    │
│  │ 行为      │ ...      │ ...      │ ...      │ ...      │ ...        │   │
│  │  ─────────┼──────────┼──────────┼──────────┼──────────┼─────────── │    │
│  │ 触点      │ □tag □tag│ □tag     │ ...      │ ...      │ ...        │   │
│  │  ─────────┼──────────┼──────────┼──────────┼──────────┼─────────── │    │
│  │ 痛点      │ ⚠ pain_highlight + 💡 机会点(高频共识)                 │   │
│  │  ─────────┼─────────────────────────────────────────────────────── │    │
│  │ 情绪      │ ▁▂▃ journey_emotion_row (SVG 曲线 + 峰谷 emoji+label) │    │
│  │           │   🙂 略好奇   😕 困惑   😌 满意   🎧 稳定   😩 纠结     │    │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  注:每行第 1 格是 journey_dimension_label;后续每格是 journey_cell           │
│      高频痛点用 journey_pain_highlight 替代普通 cell                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.6 layout-matrix-2d(R4 2D 矩阵)

```
┌──────────────── persona-slide.layout-matrix-2d ──────────────────────────────┐
│                                                                              │
│  ┌─────────── matrix_guidance_strip(顶部研究问题引导条)─────────────────┐  │
│  │  问题 1: ... ?     |     问题 2: ... ?    |    问题 3: ... ?           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────── matrix_container ───────────────────────────────────┐  │
│  │                          ↑ matrix_axis_label.top                       │  │
│  │                       「生活场景触发」                                  │  │
│  │   ┌────────── q2 ─────────┬────────── q1 ───────────┐                  │  │
│  │   │                       │                          │                  │  │
│  │   │   「随听场景派」      │     「深听场景派」      │                  │  │
│  │   │  ← matrix_quadrant_   │   button data-target=    │                  │  │
│  │   │     label(button)     │   "persona-1"            │                  │  │
│  │   │                       │                          │                  │  │
│  │   │   ▲respondent_dot     │      ▲respondent_dot     │                  │  │
│  │   │   丁先生(label-left)  │       黄医生(label-right)│                  │  │
│  │   │                       │                          │                  │  │
│  ├←──┤───── matrix_axis ─────┼─── matrix_axis ──────────┤──→               │  │
│  │   │  .vertical            │  .horizontal             │                  │  │
│  │   │                       │                          │                  │  │
│  │   │   ┌─── q3 ────────────┼─── q4 ────────────────┐  │                  │  │
│  │   │   │  matrix_empty_    │   「挑歌升级派」      │  │                  │  │
│  │   │   │  quadrant         │   ▲respondent_dot     │  │                  │  │
│  │   │   │ (当前样本未覆盖) │    韦先生 米先生       │  │                  │  │
│  │   │   └───────────────────┴───────────────────────┘  │                  │  │
│  │   └────────────────────────┼──────────────────────┘  │                  │  │
│  │                        ↓ matrix_axis_label.bottom                      │  │
│  │                      「找歌目标驱动」                                   │  │
│  │  ← matrix_axis_label.left              matrix_axis_label.right →       │  │
│  │  「价值概念薄弱」                       「价值感知清晰」                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ 后续 4 个 .persona-slide.layout-2c-portrait 各对应一个象限,通过 button 切换 │
└──────────────────────────────────────────────────────────────────────────────┘

关键: respondent_label 必须带方向类(7 种之一)
       label-right | label-left | label-top | label-bottom |
       label-top-right | label-bottom-right | label-bottom-left
       同象限多人时方向必须轮换,不能都贴右边
```

---

### 10.7 layout-distribution-multi(R5 多维分布)

```
┌──────────── persona-slide.layout-distribution-multi ─────────────────────────┐
│                                                                              │
│  ┌─────── distribution_header ─────────────────────────────────────────┐    │
│  │  distribution_title:    "4 类画像 × 4 个区分点 — 谁在哪里?"        │    │
│  │  distribution_subtitle: "这张图是几类用户在多个区分点上的横向对比"  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────── distribution_legend(画像图例,点击切换 active)──────────────┐    │
│  │  [● 内行深听派 1人]  [● 高配氛围派 1人]  [● 设备进阶派 1人]  [● ...] │    │
│  │   legend_swatch + legend_name + legend_count(组成 legend_btn)        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────── distribution_chart (主 SVG)──────────────────────────────────┐    │
│  │   高 ┤───┬───┬───┬───┐                                                │    │
│  │     │   │   │ ● 能描述                                                  │    │
│  │     │   │   │   │   │  ← snake-point + 旁标 .snake-point-level-label    │    │
│  │   中 ┤───●───●───┼───┤                                                │    │
│  │     │   │   │   │   │                                                │    │
│  │   低 ┤───┴───●───┴───┘ 完全靠想象                                       │    │
│  │       价值感│付费触发│内容探索│设备配置  ← .snake-axis-x-label          │    │
│  │  (snake_grid_line 水平 + snake_grid_col 垂直 + snake_axis_y_label 高中低)│    │
│  │  P8 改:档位名(能描述 / 设备生态 等)从底部行迁移到点位旁              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────── distribution_footer ────────────────────────────────────────┐     │
│  │  distribution_footer_hint: "点画像图例可单独突出某一类的折线"      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  后续 N 个 .persona-slide.layout-2c-portrait 各对应一类画像                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. 与交接任务书预估的差异(用户第二轮反馈后)

| 类别 | 任务书预估 | 实盘 | 差异说明 |
|---|---|---|---|
| 共享 | 4 (含 tooltip) | 3 | tooltip 是 _base.html 内置 JS+CSS,不需要 LLM 决策 |
| 2b-grid | 10 | 11 | 删 system_grid(并入 scenario_grid) + 删 fault_list + 加 ai_scenario_grid |
| 2b-grid-detail | 0 | **1**(新增 layout) | **P8 新增**:弱模型 + 大信息量 兜底双页 |
| 2b-journey | 5 | 7 | 拆 substage_arrow + 加 cross_role_arrow |
| 2c-portrait | 4 | 4 | identity_card 改为灵活 meta_tags + section_block 加内容深度约束 |
| 2c-detail | 4 | 5 | detail_illust_corner 三级 fallback + 内容深度约束 |
| 2c-journey | 4 | 7 子结构 | **整张做成 journey_2c 容器**;SVG 全 Python 算;emoji 内置图片库 |
| matrix-2d | 4 | 8 子结构 | **整张做成 matrix_2d 容器**;label 方向自动避让;空象限置灰斜纹 |
| distribution-multi | 3 | 4 子结构 | **整张做成 distribution_multi 容器**;档位名标在点位旁(非底部);同坐标多用户聚合 evidence |
| **REGISTRY 总项** | **38** | **50** | 含 7 个 layout 的子结构粒度 |
| **LLM 可填 type** | 29(BTW 估) | **24** | 见 §9.2 精确清单 |

---

## 12. 设计决策记录

1. **identity_panel 整合 5 个子结构**:left-panel 5 个内部块的顺序和呈现高度耦合,LLM 不需要单独决定哪个块在哪个位置;props 一次性接受 5 个对象,renderer 内固定拼装顺序。
2. **distribution_chart 不暴露 SVG 细节**:LLM 给「画像列表 + 区分点列表 + 每个画像在每个区分点的档位」三块数据,Python 算所有 SVG 坐标。LLM 不能控制 cx/cy/x1/x2。
3. **matrix_respondent_dot + respondent_label 一对组件**:JSON 里只产一个 `respondent` 组件,props 含坐标+脱敏名+label_direction+evidence,Python 同时输出 dot 和 label 两个元素。这样避免 LLM 给两个组件后忘记同步坐标。
4. **section_blocks_grid 作为容器组件**:不是 LLM 在 components 数组里写 N 个 section_block;而是 LLM 写一个 section_blocks_grid 组件,props.blocks 是数组。这样能在 Schema 里约束 section_block 数量(2 / 4 / 6,匹配拼贴布局)。
5. **journey_grid 同样是容器组件**:props 含 stages + dimensions + cells 二维数据,renderer 按维度生成 header + rows + emotion。LLM 不需要手写每个 cell 的 grid 定位。
6. **layouts 之间组件不共享(命名空间隔离)**:`identity_card`(2C) ≠ `identity_panel`(2B)。即使外观相似,数据契约和 CSS 不同,强行复用反而导致 LLM 混淆。

---

## 13. Layout solver 契约(回答「弱模型 + 大信息量 布局不均」)

> 你的关切:**"组件 A 占左 4/12,组件 B 占右 3/12,中间空 5/12;上一行底和下一行顶贴在一起"**——这是旧路径里 LLM 手写 `style="grid-column"` 时常翻的车。组件化后由 Python solver 拍位置,LLM 不接触坐标。

### 13.1 LLM 输出契约(只给意图,不给坐标)

```jsonc
{
  "layout": "layout-2b-grid",
  "components": [
    { "type": "resp_rings",    "props": {...} },      // 列表中的顺序 = 优先级
    { "type": "collab_flow",   "props": {...} },
    { "type": "titled_list",   "props": {...} },
    { "type": "scenario_grid", "props": {...} },
    { "type": "painpoint_list","props": {...} }
  ]
}
```

LLM **不允许**写 `grid_column` / `grid_row` / `col_span` / `row_span` 任何字段。Schema 强 reject。

### 13.2 Solver 算法(Python 在 layouts/assemble.py 实现)

12 列 × 3 行 = 36 格,每个组件按估高 + 内容密度自动占用矩形。算法如下:

1. **估高**:每个 renderer 实现 `estimate_rows(props) -> int`,返回 1/2/3(占几行)
   - resp_rings 默认 1 行;collab_flow 默认 1 行
   - scenario_grid 看 scenes 数:1-2 场景 1 行,3-4 场景 1.5 行(2 行)
   - painpoint_list 看条数:≤3 条 1 行,4-5 条 2 行
   - titled_list 同上
2. **估宽**:每个 renderer 实现 `min_cols(props) -> int`,返回最小占列数(默认 6,即半行)
   - resp_rings 内部有 2-3 个 ring,min_cols=6
   - collab_flow 总是 min_cols=6(三段流 + KPI)
   - scenario_grid 看场景数:1 个=6 列,2 个=12 列(整行),3+ 整行 12 列
3. **打包**:按优先级顺序贪心填充
   - 当前行剩余列数 ≥ 组件 min_cols → 放当前行,左对齐
   - 当前行放不下 → 把本行剩余列数**平均分配给同行已有组件**(扩到填满),换新行放该组件
   - 这样保证:**同一行从不留缝**;每行宽度恰好 12 列
4. **行高均分**:CSS 用 `align-content: space-evenly`(已经在 `_components.css` line 40),浏览器自动按 3 行均匀分配垂直空间,**不允许靠 margin 硬挤**
5. **溢出处理**:总占行数 > 3 → 抛 `overflow` 错误,回到字段对齐让用户砍字段(对齐 SKILL.md 约束 3,不静默截断)

### 13.3 弱模型 + 大信息量的具体兜底

| 弱模型容易做的坏事 | Solver 怎么挡 |
|---|---|
| 同行两组件宽度不对齐,留空缺 | LLM 不写宽度;solver 用 min_cols + 均分填满 |
| 一行挤 3 个组件,每个都太窄 | min_cols=6 的组件强制独占半行,3 个组件 = 1.5 行,放不下→换行 |
| 上下行行高不均 | CSS `align-content: space-evenly` 强制 3 行均分;solver 不允许靠 margin 调高 |
| 内容长导致组件被压扁 | renderer 的 `estimate_rows` 看内容长度返回 2 行,solver 自然给它 2 行高 |
| 总信息量超载 | 估算总行数 > 3 时 reject,回字段对齐 |

### 13.4 兜底的兜底:validate_html.py 事后检查

即使 solver 出错,`validate_html.py`(P7 已实现)兜底:

- 检查 `.persona-slide.layout-2b-grid` 内 `.grid-module` 的 `style="grid-column"` 总宽度,任一行 < 12 → `P8-GRID-GAP` 报错
- 检查 `.modules-panel` 高度是否撑满父容器 → `P8-VERTICAL-GAP` warn

事前 schema + solver + 事后 validator,三重防线。

### 13.5 与 layout solver 相关的 Python 文件

- `scripts/components/layouts/grid_solver.py`(新增,B 阶段写)
- 每个 renderer 内 `estimate_rows()` / `min_cols()` 方法(B 阶段写)
- `assemble_layout_2b_grid` 调用 solver(C 阶段)
- **超载兜底**:solver 估算总行数 > 3 → 自动拆双页(layout-2b-grid + layout-2b-grid-detail),不直接 reject

---

## 14. 待联动改动清单(跨文件)

> P8 这一轮在 REGISTRY 里许诺了很多视觉/约束改动,实际还要落到 CSS / `_base.html` / Schema / SKILL.md / visual-system.md / paradigms / 字段池 / 测试 / 资源文件 等地方。下面列出每项的「在哪改 + 何时改 + 验证方式」。每项完成在末尾打 ✅。
>
> **作用**:防止「REGISTRY 改了,别处没改,跑出来还是旧效果」的脱节。

### 14.1 CSS 改动(B 阶段做)

| # | 改动项 | CSS 文件 / 选择器 | 验证 |
|---|---|---|---|
| C1 | `.tob-substage-arrow` 新增(替换旧 `.tob-substage-tag`):浅色方块 + `::after` 右尖三角伪元素 | `_components.css` | grep 找到该类 |
| C2 | `tob_flow_cell` 不再输出 `.tob-flow-arrow`;证据挂在 `.tob-flow-pill` | `_components.css` / `tob_journey.py` | DOM 对照 |
| C3 | `.tob-focus-card-mock.is-empty` 默认占位样式(灰色背景 + 图标占位 + 居中描述) | `_components.css` | 单元测试输出含 .is-empty |
| C4 | `.scenario-card.is-ai` 修饰:顶部 ✨ 图标 + 卡底色微调 | `_components.css` | grep 找到该类 |
| C5 | `.matrix-empty-quadrant` 斜纹背景 + 居中胶囊文字「本研究样本未覆盖」 | `_components.css` | 视觉对比图 3 |
| C6 | `.respondent-label.label-*` 7 方向类的 dx/dy 改为 hard-code 常量(去 inline var 依赖) | `_components.css` | grep `--label-dx` 在 .respondent-label 内出现 0 次 |
| C7 | `.snake-point-level-label` 新增(档位名标在点旁边),**删** `.snake-axis-x-sublabel` 底部档位行 | `_components.css` | grep `.snake-axis-x-sublabel` 应为空 |
| C8 | `.detail-page-banner` 新增(2b-grid-detail 顶部小条 banner) | `_components.css` | grep 找到该类 |
| C9 | `.layout-2b-grid-detail` 新增 layout 类(整页 grid,**沿用 design tokens 三档 density,不引入新硬编码**) | `_components.css` | grep 找到 `.persona-slide.layout-2b-grid-detail { ... }` |
| C10 | `.section-blocks-grid` 显式定义 2/4/6 拼贴 grid 模板 | `_components.css` | grep 找到该类,看 grid-template-columns |
| C11 | `.emoji` 渲染样式(尺寸固定,vertical-align 居中) | `_components.css` | 已存在,确认 |

**注**:`_design-tokens.css` **不需要改**(沿用现有 high/mid/low 三档密度 token)。

### 14.2 资源文件改动(B 阶段做)

| # | 改动项 | 路径 | 验证 |
|---|---|---|---|
| R1 | 内置 emoji 33 张 PNG(从 OpenMoji/Twemoji/Fluent Emoji 取) | `assets/icons/emoji/<name>.png` × 33 | `ls assets/icons/emoji/ | wc -l == 33` |
| R2 | `EMOJI_VALID_SET` Python 常量(枚举 33 个名字) | `scripts/components/renderers/journey_2c.py` | renderer 引用该 set |

### 14.3 Schema 改动(A.3 阶段做)

| # | 改动项 | Schema 文件 | 验证 |
|---|---|---|---|
| S1 ✅ | `report.json` 顶层 `layout` enum 8 个 | `schemas/report.json` | `review_codex_schemas.py` PASS(2026-05-23) |
| S2 ✅ | `report.json` 顶层 `accent` enum 6 个 / `theme` enum 3 个 / `density` enum 3 个 | `schemas/report.json` | 同上 |
| S3 ✅ | 24 个 LLM 顶层 type 各一个 schema | `schemas/<type>.json` × 24 | 25 PASS / 0 FAIL |
| S4 ✅ | 各 props 强约束(maxLength / minItems / pattern / minLength) | 各 schema | review 脚本检查每个 string 字段都有 maxLength |
| S5 ✅ | `emoji` 枚举(33 个) | `schemas/journey_2c.json` | review 脚本对比 EMOJI_ENUM 完整匹配 |
| S6 ✅ | `display_name` 拦截「受访者\d+」pattern | `schemas/matrix_2d.json` | review 脚本验证 pattern 存在 |
| S7 ✅ | `body.minLength: 30` 防敷衍 | `schemas/section_block.json` | review 脚本硬检查 |
| S8 ✅ | `section_blocks_grid.blocks` 数量必须 2/4/6 | `schemas/section_blocks_grid.json` | review 脚本硬检查 minItems:2 / maxItems:6 |
| S9 ✅ | `tob_flow_pill` text `maxLength: 33`(22 汉字 ≈ 33 char) | `schemas/tob_journey_l1.json` / `tob_journey_l2.json` | Codex 已实现 |
| S10 | layout-2b-grid-detail / layout-2b-grid 中的 `accent` 在 2C 主题外可选 | `schemas/report.json` | ⏳ 推到 B 阶段(conditional schema 在 render_report 用 if/then/else 也行,先简化为 accent 通用可选) |
| S11 ✅ | 统一截图槽字段名为 `screenshot`(scenario_grid + mockup_list + tob_focus_cell) | `schemas/mockup_list.json` | A.3 命名修订完成 |

### 14.4 文档改动(D 阶段做)

| # | 改动项 | 文件 | 验证 |
|---|---|---|---|
| D1 ✅(从 7 改;加 layout-2b-grid-detail) | `SKILL.md` 约束 7 / `steps/visual-system.md` 0.2 / 5 | grep `"7 个 layout"` 应为空 |
| D2 ✅ 触发逻辑 + 双页切 mid density 说明 | `steps/visual-system.md` §3 | grep 找到该 layout 名 |
| D3 ✅ 字段提及 | `schemas/schema-tob.md` + `steps/field-alignment.md` | grep `system_grid`、`business_systems` 字段映射到 scenario_grid.tools |
| D4 ✅ 字段提及(`fault_scenarios` 字段映射到 titled_list 兜底) | `schemas/schema-tob.md` | 同上 |
| D5 ✅ 字段说明 | `schemas/schema-tob.md`(`ai_assist_systems` 字段映射到该组件) | grep `ai_scenario_grid` |
| D6 ✅ 是开放字段,LLM 自由命名 label」「section_block.title 自由命名贴画像」 | `schemas/schema-toc.md` | grep 找到「开放字段」段 |
| D7 ✅ 旧概念提及(痛点并入 focus_card.is-pain) | `schemas/schema-tob.md` / `steps/visual-system.md` | grep `tob-pain-banner` 应为空 |
| D8 ✅,禁止产 HTML 字符串」契约 | `paradigms/R*.md` × 5 + `SKILL.md` 约束 12 | 每个 R*.md 末尾有「产出格式」段 |
| D9 ✅「LLM 不输出 SVG path,不输出 Unicode emoji 字符」 | `SKILL.md` | grep 约束 13 标题 |
| D10 ✅(body 含具体动作/场景/程度词)写进 prompt | `paradigms/R*.md` × 5 | grep 找到该规范 |
| D11 ✅(按调性 + 强度匹配 level)写进 prompt | `paradigms/R*.md` × 5 | 同上 |
| D12 ✅(同一画像 N 的 -journey/-detail 自动配对)放进 visual-system.md | `steps/visual-system.md` §3.2 | grep `nav-pair` |
| D13 ✅触发条件:大量提到 AI 才启用,不强制每个画像都有 | `schemas/schema-tob.md` | grep 找到「启用条件」 |

### 14.5 Python 文件改动(B / C 阶段做)

| # | 改动项 | 路径 | 验证 |
|---|---|---|---|
| P1 | `scripts/components/__init__.py`、`renderers/__init__.py`、`layouts/__init__.py`、`schemas/`、`tests/` 目录骨架 | 同上 | 文件存在 |
| P2 | `scripts/components/registry.py`(组件 type → 渲染函数注册表) | 同上 | 24 个 type 全部注册 |
| P3 | `scripts/components/layouts/grid_solver.py`(12 列贪心打包 + 超载拆双页) | 同上 | 单元测试覆盖 5 个超载 case |
| P4 | 每个 renderer 提供 `estimate_rows(props) -> int` 和 `min_cols(props) -> int` | 各 renderer | grid_solver 调用时不报错 |
| P5 | `scripts/components/render_report.py`(顶层组装 + slot 填充 + CSS 随包 + validator 接入 + density 自动切换) | 同上 | E 阶段 snapshot 全过 |
| P6 | `scripts/validate_components_json.py`(F 阶段) | 同上 | HiRes 失败 case 能被拒收 |

### 14.6 测试改动(B / E 阶段做)

| # | 改动项 | 路径 | 验证 |
|---|---|---|---|
| T1 | 每个 renderer ≥ 2 个单元测试(基础 + escape + 约束触发) | `scripts/components/tests/test_<type>.py` × 24 | pytest 全绿 |
| T2 | grid_solver 单元测试(单页 / 双页触发 / 字段满载) | `tests/test_grid_solver.py` | 同上 |
| T3 | Snapshot 测试 10-15 case(覆盖所有 8 个 layout + 边界) | `tests/snapshots/*/` | snapshot 字节级一致 |
| T4 | `tools/review_codex_schemas.py`(我写,A.3 用) | `tools/` | 你跑这个看 PASS/FAIL |

### 14.7 联动校验自动脚本(阶段 D 完成时跑)

```bash
# CSS 应该有的新类全部出现
grep -E "tob-substage-arrow|matrix-empty-quadrant|snake-point-level-label|layout-2b-grid-detail|scenario-card\.is-ai|detail-page-banner|section-blocks-grid" "$SKILL/assets/templates/_components.css"

# 文档不应该再出现的旧概念全部消失
for f in "$SKILL/SKILL.md" "$SKILL/schemas/schema-tob.md" "$SKILL/steps/visual-system.md"; do
  grep -nE "system_grid|fault_list|tob-substage-tag|tob-pain-banner|snake-axis-x-sublabel" "$f"
done
# 上面输出应为空

# Schema 文件数 = 24 个 type + 1 个 report.json
ls "$SKILL/scripts/components/schemas/"*.json | wc -l   # 应为 26

# Emoji 图数量
ls "$SKILL/assets/icons/emoji/"*.png | wc -l            # 应为 33

# Python 测试
cd "$SKILL" && pytest scripts/components/tests/ -v
```

**触发时机**:任何阶段完成时,跑对应行的检查。**全部行都过,才能进下一个阶段。**

### 14.8 联动清单总条数

- CSS: 11
- 资源文件: 2
- Schema: 10
- 文档: 13
- Python: 6
- 测试: 4
- **合计:46 项**

每个阶段完成,在本表对应行末尾打 ✅,确保不漏。

---

## 15. 已废弃项历史记录(代码层面已清理完毕)

下列废弃组件 / 类名在 P8 收尾轮里已从 CSS、renderer、schema 三方一并删除:

| 废弃项 | 替代方案 | 清理时机 |
|---|---|---|
| `system_grid` | 业务系统并入 `scenario_grid` 的 `tools` 标签 | P8 完成 |
| `fault_list` | 用 `titled_list` 兜底 | P8 完成 |
| `task_freq_list` | 用 `titled_list` 兜底 | P8 收尾轮 |
| `.tob-pain-banner` | 痛点并入 `.tob-focus-card.is-pain` | P8 收尾轮 |
| `.tob-substage-tag` | 替换为 `.tob-substage-arrow` | P8 收尾轮 |
| `.snake-axis-x-sublabel` | 替换为 `.snake-point-level-label`(标在点旁) | P8 收尾轮 |
| `.matrix-respondent` wrapper | 拆为独立的 `.matrix-respondent-dot` + `.respondent-label` | P8 收尾轮 |
| Legacy `_render_legacy_tob_journey_l1/l2` + `render_cross_role_overlay` + `_parse_idx` | 统一走 UML DSL(`_render_uml_journey`) | P8 收尾轮 |
| Monolithic `render_layout_2b_grid_detail` + `render_layout_2c_detail` | 组件化路径(assemble.py + 各组件 renderer) | P8 收尾轮 |
| `nav_trio` 顶层组件注册 | nav 由 `build_nav` 内部构造,不走 LLM 路径 | P8 收尾轮 |

> 守门脚本:`scripts/tests/check_css_orphans.py` 防止新孤儿 CSS 进入;
> `scripts/components/tests/test_no_mojibake_literals.py` 防止编码事故再发。

旧的 LLM-产-HTML 路径(`render_html.py` 等)已在 V9 删除;统一走 `render_report.py`。
