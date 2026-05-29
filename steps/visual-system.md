# 视觉系统执行手册

> 模型在「渲染画像页」时按本手册执行。手册分 6 部分:
> 0. **★ 渲染硬约束(红线,违反任一条都不可接受)**
> 1. 主题与密度选择
> 2. 布局类自动判断(单页 / 双页 / tab / 矩阵 / 旅程图)
> 3. 双页切分逻辑
> 4. 2C 强调色选色规则
> 5. 模板文件清单 + slot 填充规范

---

## 0. ★ 渲染硬约束(对应 SKILL.md 约束 7)

**P0 测试暴露的真问题**:LLM 在没硬约束时会**凭空创建新视觉系统**(暗色主题、自创类名、不引用骨架 CSS),导致 P1-P5 阶段建立的骨架完全失效。本节是不可越界的红线。

### 0.1 红线 5 条

| # | 红线 | 违反的样子 |
|---|---|---|
| 1 | **必须 link 骨架 CSS** | 内联自创 `<style>` 块、不 link `_design-tokens.css` / `_components.css` |
| 2 | **必须用现有 layout-XXX 类**,只能从 0.2 节 6 个选 | 用 `.persona-page` / `.main-grid` / `.identity-card` 等自创类 |
| 3 | **必须用 `_base.html` 的 slot 填充** | 不读 `_base.html`、直接写新 `<html>` 骨架 |
| 4 | **颜色/字号/间距必须用 design tokens** | 写 `background: #0f1729` / `font-size: 14px` / `padding: 32px` 硬编码 |
| 5 | **layout 不够用 → 报错回字段对齐** | 自己造新组件、新 layout 类 |

### 0.2 仅能用的 7 个 layout 类

| 类名 | 适用场景 | 修饰类 |
|---|---|---|
| `layout-2b-grid` | toB/toD 单画像单页(30/70 双栏 + 12×3 右栏网格) | — |
| `layout-2b-journey` | toB/toD 用户旅程图(角色 × 阶段;L1 全角色汇总,L2 单角色细化) | **`is-l1`** / **`is-l2`** 必选一个 |
| `layout-2c-portrait` | toC 单画像主页(白底拼贴 + 身份小卡 + section 段卡) | — |
| `layout-2c-detail` | toC 专题详情页(大标题 + mockup + 解读 + 角落插画) | — |
| `layout-2c-journey` | toC 用户旅程图(阶段 × 维度网格 + 情绪曲线) | — |
| `layout-matrix-2d` | R4 2D 矩阵(4 象限 + 受访者点位 + 轴标签) | — |
| `layout-distribution-multi` | R5 多维分布图(3-5 个区分点 × N 类画像) | — |

### 0.3 凭空创作 vs 合规渲染对照

❌ **错(P0 真实发生过)**:
```html
<style>
  :root { --bg: #0f1729; --accent: #4f8cff; }
  .persona-page { ... }
  .identity-card { ... }
  .main-grid { ... }
  .panel { ... }
</style>
<div class="persona-page">
  <div class="identity-card">...</div>
  <div class="main-grid"><div class="panel">...</div></div>
</div>
```
错在哪:暗色主题硬编码、自创类名(`.persona-page` / `.main-grid` / `.panel`)、不 link 骨架 CSS、不用 slot。

✓ **对**:
```html
<html lang="zh-CN" data-theme="2b" data-density="high">
<head>
  <meta charset="UTF-8">
  <title>电力调度员画像</title>
  <link rel="stylesheet" href="_design-tokens.css">
  <link rel="stylesheet" href="_components.css">
</head>
<body>
  <div class="report-meta-bar">
    <div class="report-meta-title">电力调度员画像研究</div>
    <div class="report-meta-info">1 个画像 · 5 份访谈 · 2026-05-19</div>
  </div>
  <section class="persona-slide layout-2b-grid active" id="persona-1">
    <div class="identity-panel">
      <div class="avatar-wrap"><div class="persona-avatar placeholder">电</div></div>
      <div class="identity-name"><div class="name-line">电力调度员</div></div>
      ...
    </div>
    <div class="modules-panel">
      <div class="grid-module" style="grid-column: 1 / 7; grid-row: 1 / 2;">...</div>
      ...
    </div>
  </section>
</body>
</html>
```
对在哪:`data-theme` + `data-density` 在 `<html>` 上、link 骨架 CSS、用 `layout-2b-grid` 类、用 `.persona-slide` / `.identity-panel` / `.modules-panel` / `.grid-module` 这些骨架已有的类、不硬编码颜色。

### 0.4 渲染前 checklist(模型自检)

渲染任何 HTML 前,模型必须自问 5 条:
- [ ] link 了 `_design-tokens.css` 和 `_components.css` 吗?
- [ ] `<html>` 上有 `data-theme` + `data-density` 吗?
- [ ] 主 section 用的是 0.2 节 7 个 layout 类之一吗?(`layout-2b-journey` 必须带 `is-l1` 或 `is-l2` 修饰类)
- [ ] 有没有写任何硬编码颜色/字号/间距(像 `#0f1729` / `14px` / `32px`)? 有就换成 `var(--xxx)`。
- [ ] 有没有自创新组件类名(像 `.persona-page` / `.panel`)? 有就停下,报错回字段对齐。

**5 条全过才能出 HTML**。任一条不过 = 违反 SKILL.md 约束 7。

---

## 1. 主题与密度选择

| 范式 / 受众 | data-theme | data-density |
|---|---|---|
| toB(R1/R2/R3 中 toB 数据) | `2b` | `high`(默认) |
| toD(开发者画像) | `2d` | `high`(默认) |
| toC(R2/R3 中 toC 数据) | `2c` | `low`(默认) |
| R4 / R5 | 按 `03-field-alignment.json` 的 `research_type`：`toB/toD` → `2b`/`2d`；`toC` → `2c` | 同左列 theme 默认密度 |

**密度可由用户在研究目标里强制覆盖**:
- 用户说「信息很多」「希望塞满」「不希望太空」→ 切 `mid`
- 用户说「想要密集汇报感」→ 切 `high`(即使是 toC)
- 用户说「希望留白」「不要太挤」→ 保持 `low`

**密度切换不影响主题色**(theme 和 density 是正交的)。

---

## 2. 布局类自动判断

**五种方式 × 2B/2C 主路由表**(与 `SKILL.md` §布局自动判断 一致,单点真相):

| 方式 | 范式 | 导航/首页 | 2B/2D 画像子页 | 2B/2D 旅程(用户确认时) | 2C 画像子页 | 2C 旅程(用户确认时) |
|------|------|-----------|----------------|------------------------|-------------|---------------------|
| A | R2 | 单 tab | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` `.is-l2` + `tob_journey_l2` | `layout-2c-portrait`(溢出→`layout-2c-detail`) | `layout-2c-journey` + `journey_2c` |
| B | R1 | 多 tab | 同上 × N | 同上(可选 L1+L2) | 同上 × N | 同上 × N |
| C | R3 | 多 tab | 同上 × N | 同上 | 同上 × N | 同上 |
| D | R4 | `layout-matrix-2d`(**总览仅配色**) | `layout-2b-grid` × 4 | `tob_journey_l2` × 4 | `layout-2c-portrait` × 4 | `journey_2c` × 4 |
| E | R5 | `layout-distribution-multi`(**总览仅配色**) | `layout-2b-grid` × N | `tob_journey_l2` × N | `layout-2c-portrait` × N | `journey_2c` × N |

硬规则:
1. `research_type` 决定走 2B/2D 列或 2C 列,**禁止混用**(`P8-THEME-LAYOUT-MISMATCH`)。
2. R4/R5 **总览 slide** 只用 `matrix_2d` / `distribution_multi`,**禁止**画像/旅程组件(`P8-OVERVIEW-FORBIDDEN-COMPONENT`)。
3. R4/R5 总览 DOM 结构 toB/toC **共用**;差异仅 `metadata.theme` + `data-density`(design tokens 配色)。

布局类(`layout-XXX`)由 `layout.py` + 模型联合判定。判定流程:

```
Step A: 判断是单画像还是多画像
  ├─ 单画像 → 进 Step B
  └─ 多画像 → 进 Step C

Step B: 单画像走单页 / 双页判断
  ├─ 估算 12×3 网格能否装下所有字段
  │  ├─ 能装下                → layout-2b-grid(toB/toD)
  │  │                          / layout-2c-portrait(toC)
  │  └─ 装不下                → 按"画像核心 vs 工作细节"切双页
  │                            第 1 页:layout-2b-grid(画像核心)
  │                            第 2 页:layout-2b-grid-detail(工作细节,P8 新增)
  │                            (见第 3 节;**LLM 不主动选 layout-2b-grid-detail**,
  │                             由 Python grid_solver 估算溢出后自动拆;
  │                             双页时整报告 density 自动从 high 切 mid)
  └─ 若主题是 2C 且研究目标涉及"旅程/流程/上手过程"
     → **可建议**用户加一页 layout-2c-journey,但必须问用户(2026-05-28 修订)
     → 旧的"自动补充"已删除;用户在 field-alignment Step 5 确认前不渲染旅程页

Step C: 多画像走 tab / 矩阵 / 多维分布
  ├─ R1/R2/R3 多画像 toB    → tab 切换
  │                          (外层 nav,每画像走 Step B 逻辑)
  │   └─ 仅当 `03-field-alignment.json` 中 `add_on_pages.journey = true`
  │      ├─ **约束 14 / Step 5.1**:先读 `journey_l1_eligible` 与 `journey_scope`
  │      │  ├─ `journey_l1_eligible = true` 且 `journey_scope` 含 L1
  │      │  │  → 加 L1:`id=journey-l1`,nav="整体旅程/总体旅程"
  │      │  │  → 可选 L2:`persona-N-journey`(用户要或 scope=L1_and_L2)
  │      │  │  · L1 内容须来自访谈跨角色 UML(节点/边/判断/虚线),禁止模板凑密度
  │      │  │  · 参考 golden:`scripts/components/tests/golden_samples/tob_journey_l1_dense.json`
  │      │  └─ `journey_l1_eligible = false`(完全独立)
  │      │     → **禁止**输出 `journey-l1`;仅 `persona-N-journey`(L2_only)
  │      └─ `journey = false` → 无任何 journey slide
  │      ※ 已废弃:仅因「角色≥3 且能聚合阶段」或「研究目标提流程」就自动加 L1
  ├─ R4 (2D 矩阵)           → layout-matrix-2d 作为首页(矩阵页 toB/toC 共用)
  │                            子页按 research_type 分支(见下表)
  └─ R5 (多维分布)          → layout-distribution-multi 作为首页
                              子页按 research_type 分支(见下表)
```

**R4 / R5 子页路由**(矩阵/分布首页共用,**子页 theme/layout 必须跟 research_type 一致**):

| 条件 | 矩阵/分布首页 | 象限/类别画像 | 旅程(用户确认时) | theme |
|------|---------------|---------------|------------------|-------|
| R4/R5 + `research_type=toC` | `layout-matrix-2d` / `layout-distribution-multi` | `layout-2c-portrait` | `layout-2c-journey` + `journey_2c` | `2c` |
| R4/R5 + `research_type=toB/toD` | 同上 | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` `.is-l2` + `tob_journey_l2` | `2b` |

**禁止**:toB 研究因「矩阵首页像 toC 样板」而在象限子页混用 `identity_card` / `section_blocks_grid` / `journey_2c`。事前校验 `P8-THEME-LAYOUT-MISMATCH` 会拦。

**journey_2c.cells 轴向**(toC 旅程必填,校验 `P8-JOURNEY-CELLS-SHAPE`):

```json
{
  "stages": ["告警发现", "研判决策", "协调执行", "处置复电", "结案复盘"],
  "dimensions": ["思考", "行为", "痛点", "触点"],
  "cells": [
    [ /* 思考 × 5 阶段 */ ],
    [ /* 行为 × 5 阶段 */ ],
    [ /* 痛点 × 5 阶段 */ ],
    [ /* 触点 × 5 阶段 */ ]
  ],
  "emotion": [ /* 5 项,与 stages 对齐 */ ]
}
```

**禁止按「一行一个阶段」组织 cells** — 外层行 = dimensions,内层列 = stages。

**toB 旅程图(layout-2b-journey)与 toC 旅程图(layout-2c-journey)的区别**:
- toB:高密度专业咨询风,深蓝深色 banner + 浅蓝椭圆 pill + 渐变阶段色块 + 红色痛点 banner;支持 L1 全景(角色 × 阶段)+ L2 单角色(阶段 × 工作流程/关注点/痛点)双形态
- toC:清爽插画风,白底卡片 + 单角色 × 阶段 × (思考/行为/痛点/触点/情绪) 矩阵 + SVG 情绪曲线
- **两种 layout 不可混用**:数据主题决定 layout 选择,toB 数据强制走 2b-journey

**模型在切换布局时,必须在终端告知用户原因**,例如:
> "已切换为双页布局,原因:你提供的字段(职责+协同+系统+AI 系统+决策源+痛点+故障+高频任务)共 8 个,12×3 网格(最多 6 个 grid-module)放不下。第 1 页放画像核心,第 2 页放工作细节。"

**禁止静默切换**(违反硬约束 4 — 屏蔽实现细节但要告知决策)。

---

## 3. 双页切分逻辑(不平均砍)

切分原则:按「画像核心」vs「工作细节」分,不按字段数平分。

**第 1 页 — 画像核心** `layout-2b-grid`(读者快速建立人物画像):
- 身份卡(`identity_panel` 整合头像 / 名字 / 描述 / meta-row / 一句话需求)— 左栏
- 工作职责(`resp_rings`)
- 上下游协同(`collab_flow` + KPI)
- 核心痛点(`painpoint_list`)

**第 2 页 — 工作细节** `layout-2b-grid-detail`(读者深入了解具体工作流):
- **顶部 banner**:`<画像名> · 工作细节`(由 Python 自动生成,无需 LLM 填)
- **整页 12 列大网格**(无左栏身份卡,不重复画像信息)
- 业务系统 + AI 辅助系统(`scenario_grid` + `ai_scenario_grid`)
- 决策信息源(`titled_list` 兜底)
- 高频任务(`titled_list`,字段 `main_tasks` / `high_freq_tasks`)
- 故障场景(`titled_list` 兜底)
- **density 自动切 mid**:双页两页都从 high 切到 mid(行距更舒展,Python 自动)

**切分时的硬约束**:
- 两页都必须保留身份卡,保证视觉锚一致
- 不允许把同一个字段在两页都展示(避免读者疑惑)
- 切完后两页都要再走一次溢出估算 — 若任一页仍溢出,**报错回到字段对齐**(硬约束 3)

### 3.0.1 拥挤红线(2026-05-26 新增)

**触发条件**(满足任一即视为页面拥挤,必须拆双页 or 砍内容):

| 维度 | 阈值 | 说明 |
|---|---|---|
| 模块上下间距 | ≥ 16 px(grid gap) | 模块壳之间不能贴在一起,小于 16 px 必须拆 |
| 模块内边距 | ≥ 14 px(.module-body padding) | title 与正文 / 列表条目之间留呼吸感 |
| 单行模块数 | ≤ 2(toB grid) / ≤ 3(scenario-grid 内部卡片) | 同行 ≥ 3 个并列模块就会压扁字号,触发拆双页 |
| 列表条目数 | painpoint_list/titled_list ≤ 5 | >5 条要么砍要么拆到 detail tab |
| 单列字数 | ≤ 70(高密度) / ≤ 55(中密度) | 单行超出会导致字号被压到 ≤ 12 px |

**判定流程**:
1. LLM 给完 05-report.json,Python 跑 `solve_grid` 估算行数
2. 若某模块 `min_cols=6` 且与同行兄弟模块累计 col > 12 → 自动换行
3. 若累计 row > 3(layout-2b-grid 上限),走 `_dual_page_split` 拆双页
4. **若拆双页后第二页仍只有 1 个低密度模块**(titled_list 3 条以内)→ 推荐 LLM 直接显式给 `persona-N-detail` slide,避免 grid_solver id 冲突
5. **若 LLM 已显式声明 detail tab**(id=`persona-N-detail`)→ 第一页严格按 LLM 排,grid_solver 不再自动拆;**若第一页仍溢出,报错回到字段对齐让 LLM 砍内容**

**LLM 应对建议**:
- 内容多到一页装不下:**首选**显式拆 2 个 persona slide(persona-N 核心 + persona-N-detail 细节),不要寄望 Python 自动拆
- 拆完单页字段仍超 4-5 个:**砍优先级最低的**,不要靠压字号塞下
- 同一 row 不要塞 3 个 ≥ span 4 的模块,会触发拥挤红线

### 3.0.2 toB 兜底字段语义索引(2026-05-26 新增)

`generic_text` / `generic_bullet` / `generic_kv` + `titled_list` 这 4 个组件是 toB 报告 detail tab 的主力。下表把"研究员常会遇到的语义片段 → 推荐组件"映射好,LLM 写 05-report 时按图索骥,**不再凭空造组件 / 信息丢失**。

| 信息语义 | 推荐组件 | 关键字段 | 例子 |
|---|---|---|---|
| **关注的数据指标** | `generic_kv` | `headers: ["指标","考核口径"]` | 联络线偏差 / 母线负荷 / 力调电费 |
| **典型行为模式** | `titled_list` | item 带 `insight`(行为/关注点/洞察三层) | 跨系统拼数 → 单系统视角不足 → 高频刚需 |
| **工具栈** | `generic_kv` | `headers: ["场景","工具"]` | 调度主监控 → D5000/Open3000/SCADA |
| **业务规模** | `generic_kv` | `headers: ["维度","数值"]` | 调度层级 / 管控对象 / 年考核额 |
| **决策路径** | `titled_list` | item 带 `insight` | 关键岔路口判断依据 + 实际选择 + 隐藏成本 |
| **风险/合规清单** | `generic_kv` | `headers: ["类型","约束"]` | 数据脱敏 / 审计留痕 / SLA |
| **历史里程碑** | `generic_kv` | `headers: ["时间","事件"]` | 团队/系统过去 3 年的演化锚点 |
| **未来路线期望** | `titled_list` | item 标题用时间(3 月/6 月/12 月) | 短/中/长期演进方向 |
| **学习路径 / 上手成本** | `generic_text` 或 `titled_list` | — | 新人到熟手周期、必备资源 |
| **关键时间窗口** | `generic_kv` | `headers: ["节点","动作"]` | 每日/每月/每年高峰 + 关闭点 |
| **预算 / 成本结构** | `generic_kv` | `headers: ["项目","年额"]` | 总预算 / 单次操作成本 / 降本目标 |
| **能力差距清单** | `titled_list`(insight) | — | 现状能力 vs 期望能力 + 差距分析 |
| **跨角色协同(轻量)** | `generic_kv` | `headers: ["对接角色","频率"]` | 协作矩阵简化版 |
| **金句 / 原话集合** | `generic_bullet` | — | 跨多人浮现的共同表达模式 |
| **研究员观察 / meta 洞察** | `generic_text` | — | 一段总结句 / 设计原则推论 |
| **零散观察**(未达痛点强度的小坑) | `generic_bullet` | — | "顺手吐槽" / 隐性动作 |

**判断规则**:
- 某语义在 ≥ 3 个 toB 项目中重复出现且结构相似 → 考虑做**专用结构化组件**
- 否则:用上表的兜底组合,**通过 module_title + headers/insight 自由命名**就够了

**字段约束**(兜底组件三剑客 + titled_list):
- `module_title` ✱必填,2-12 字(LLM 自由命名,如"关注的数据指标"/"业务规模")
- `generic_kv.headers` 可选,数组长度严格 2,每元素 1-6 字
- `titled_list.items[i].insight` 可选,10-100 字(用于"行为/关注点/洞察"三层结构)

**视觉规格**(2026-05-26 后):
- detail tab strict 2 列 × 3 行(上限 6 个组件),无 banner;`assemble.py:assemble_layout_2b_grid_detail` 强制
- detail section 内边距:4 边统一 = module-title 按钮高度(`calc(var(--space-2) * 2 + 22px)` ≈ 32/34/38 px,跟随密度)
- 模块间 row-gap = `var(--space-9)` ≈ 20 px (high) / 24 px (mid) / 31 px (low)
- 模块间 column-gap = `var(--space-6)` ≈ 12 px (high) / 14 px (mid) / 18 px (low)
- generic_kv 行内紧凑:`gap:0` + `padding: var(--space-1) 0`(3 px high)+ 1 px border-bottom

### 3.1. 2C 双页:**主画像页 + 专题详情页**(不是信息拆分)

参考 image002+003 / image005+006:2C 双页的本质是**两种不同布局的页面**,不是简单切分信息。

- **第 1 页 — 主画像页**(layout-2c-portrait):身份卡 + 代表原话 + 段落式 section
- **第 2 页 — 专题详情页**(layout-2c-detail):**针对画像的某一关键观点/期望做深入展开**
  - 顶部大标题:画像的某条核心观点(如"专区内听歌类型更为多样,期待增添更多终曲音乐")
  - 左侧:产品场景 mockup — **可接收用户截图**(见 `steps/visual-assets.md`);`mockup_list` 的 `screenshot` 指向 `<项目运行目录>/界面截图/<文件名>`,无图时渲染占位帧
  - **mockup 帧高规则**:同一 `mockup_list` 内所有槽位(含 mockup-2 / mockup-3)**帧高一致**(`--mockup-frame-height`);真图 **高度铺满帧、宽度按原图比例自动缩放**(居中,不裁切);用户应提供**单屏截图**,勿用多屏横拼大图
  - 右侧:访谈解读文字(2-3 段)
  - 角落:小人物插画呼应

**层数自适应**:专题详情页可以有 1 张或多张(每张针对一个核心观点)。tab 数量上限同 3.2 节(6 个)。

**模型话术**:
> "你的画像有 N 条特别强烈的观点/期望,我把它们各做一页专题详情页,你可以点上方标签切换查看。"

### 3.2. 多 tab × 双页 × 旅程图 × L1/L2 组合(命名约定,不改 JS)

### 2C 多画像旅程页规则

toC 多画像场景不能只生成一张“总旅程”。如果用户要旅程页,每个用户类型都要各接一张 `layout-2c-journey`:

- id: `persona-1-journey`、`persona-2-journey`、`persona-3-journey`
- tab: `画像名` 后紧跟 `画像名 · 旅程`
- 旅程页标题: `画像名 · 旅程`
- 阶段:通常 5 个,如“发现 → 试听 → 开通 → 日常使用 → 续费/流失”;确有证据时可 4-6 个
- 维度:至少包含“思考 / 行为 / 痛点 / 情绪”,有明确产品触点时加“触点”
- 单元格层级:先 `.journey-cell-keyword` 放 3-5 字关键词,再 `.journey-cell-summary` 放 15-25 字总结
- 痛点:高频共识用 `.journey-pain-highlight`,并加 `.journey-pain-opportunity-tag` 标“机会点”
- 情绪:必须使用 SVG 曲线 + `.emotion-area` 色块 + 峰谷 label,不能只写文字行

旅程图参考 `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` 旅程 tab。tab 组织参考 `docs/reference/reports/B-多角色/2B-DevOps五角色/report.html` 的一级 nav 方式。
#### 2026-05-20 P0 补充:每个画像的旅程必须独立分析

多画像 toC 报告里,旅程页是“该用户类型如何经历产品”的分析结果,不能把一张总旅程复制 3 份再改标题。真实失败案例:HiRes 报告中 `内行深听派旅程`、`内容尝鲜派旅程`、`权益观望派旅程` 的思考、行为、触点、痛点、机会点、情绪曲线完全一致,只有标题和颜色不同。

生成规则:
- 每个 `persona-N-journey` 必须只使用该画像绑定的受访者、代表原声、痛点、使用场景、付费动机和流失原因来生成
- 允许阶段名称共用,如“发现专区 / 理解价值 / 试听与判断 / 开通付费 / 使用沉淀 / 复购或断开”
- 不允许 `思考`、`行为`、`触点`、`痛点`、`机会点`、`情绪标签` 六行整行复用
- 如果多个画像在同一阶段确有共同问题,也必须写出各自差异:谁卡在价值解释,谁卡在内容新鲜感,谁卡在价格权益
- 每个旅程页至少有 3 个单元格含该画像专属证据或人群特征,例如 `内行深听派:对比普通音质后才愿意续费`;`内容尝鲜派:被专区内容吸引但缺少持续新鲜感`;`权益观望派:价格和会员权益解释决定是否开通`
- 情绪曲线必须按画像差异单独绘制,不能三页使用同一条 SVG path 和同一组情绪标签

数据结构要求:
- `04-personas.json` 或生成中间数据里,每个 persona 必须有自己的 `journey` 对象
- `journey` 至少包含 `stages`、`rows.thinking`、`rows.behavior`、`rows.touchpoints`、`rows.pain_points`、`rows.opportunities`、`emotion.points`、`evidence_refs`
- 禁止只在全局写一个 `journey = {...}` 再让 `render_journey(p)` 复用
- `render_journey(persona)` 只能读取 `persona.journey`,不能读取全局 `journey` 或全局 `rows_data`

交付前自检:
- 去掉标题、画像名、颜色和头像后,任意两个 `layout-2c-journey` 的正文相似度不能超过 70%
- 若 3 个旅程页的阶段以外文本完全相同,直接判定失败,回到旅程分析阶段重做
- 自检失败时不能通过换 CSS、改标题或改颜色解决,必须重写每个画像的旅程内容

当多画像 + 每画像内容多 + 含旅程图,**用一级 nav 列出所有页面组合**,不引入二级 nav。
#### 2026-05-20 补充:画像与旅程必须做成组合页签

当一个画像后面接自己的旅程页时,导航必须把两者做成一组,视觉上像一个按钮被分成左右两段。左段是画像名,右段固定写 `› 旅程`。这条规则优先于旧的 `画像名 · 旅程` 文案。

```html
<div class="nav-pair">
  <button class="nav-btn nav-btn-persona" data-target="persona-1">内行深听派</button>
  <button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>
</div>
```

渲染检查:
- 有 `persona-N-journey` 时,同一个 `N` 必须有一个 `.nav-pair`
- 旅程按钮不能写成 `内行深听派旅程`
- `.nav-pair` 内两个按钮都必须有 `data-target`,点击后按 `_base.html` 的统一切换逻辑工作

**id + nav 文字命名约定**:

| 场景 | id 格式 | nav 文字 |
|---|---|---|
| 单画像单页 | `persona-1` | "画像名" |
| 单画像 + 旅程图 | `persona-1` / `persona-1-journey` | "画像名" / "画像名 · 旅程" |
| 单画像双页 | `persona-1-core` / `persona-1-detail` | "画像核心" / "工作细节" |
| 单画像双页 + 旅程图 | `persona-1-core` / `persona-1-detail` / `persona-1-journey` | "画像核心" / "工作细节" / "旅程" |
| 单画像 + 多张专题详情 | `persona-1` / `persona-1-detail-1` / `persona-1-detail-2` ... | "画像名" / "专题 · 标题 1" / "专题 · 标题 2" ... |
| 多画像单页 | `persona-1` / `persona-2` ... | "画像名 1" / "画像名 2" ... |
| 多画像 + 各自旅程图(L2) | `persona-1` / `persona-1-journey` / `persona-2` / `persona-2-journey` ... | "画像名 1" / "画像名 1 · 旅程" / "画像名 2" / "画像名 2 · 旅程" ... |
| 多画像双页 | `persona-1-core` / `persona-1-detail` / `persona-2-core` ... | "画像名 1 · 核心" / "画像名 1 · 细节" / "画像名 2 · 核心" ... |
| **多画像 toB + L1 全景旅程 + 各自 L2 旅程** | `journey-l1` / `persona-1` / `persona-1-journey` ... | "整体旅程" / "画像名 1" / "画像名 1 · 旅程" ... |
| **多画像 toB + 仅 L2(完全独立,无 L1)** | `persona-1` / `persona-1-journey` ... | **无** `journey-l1` tab |

**核心规则**:
- id 用 ASCII 短横线分隔:`persona-N-<page-type>`
- nav 文字用全角中点 ` · ` 分隔画像名和页签
- page-type 后缀:`-core` / `-detail` / `-detail-N` / `-journey`
- L2 单角色旅程图绑定到具体画像,**走 `persona-N-journey` 命名**;nav 文字"画像名 · 旅程"
- **L1 全景旅程图独立 id**:`journey-l1`,nav 文字 **"整体旅程"** 或 **"总体旅程"**
  - **仅当** `add_on_pages.journey_l1_eligible = true` 时出现(约束 14)
  - L1 是跨多画像的"全景视角",不绑定任何单画像
  - 同组织多角色且含 L1 时,**L1 放第 1 个 tab 并 active**
- **完全独立的多角色** → 禁止 `journey-l1`,即使 `journey=true` 也只能 L2

**tab 数量上限**:**12 个**。超过 → 报错回字段对齐,让用户决定砍画像还是砍内容。

> 上限从 8 提高到 12 的原因:toB 同组织 + L1/L2 的常见组合是 9-11 个 tab。

**模型告知用户的话术**(仅 `journey_l1_eligible=true` 时):
> "这几个角色在同一 [产品/组织] 里协作,我会做 1 张「整体旅程」+ 每个角色各自的旅程页,排成多个标签页,首屏停在整体旅程。"

---

## 4. 2C 强调色选色规则

适用于 `data-theme="2c"`。**对每个 2C 画像执行一次**,把结果写进 `<html style="--color-accent: var(--accent-XXX)">`。

```
Step 1. 判断画像是否"AI 相关"
  触发条件:画像核心场景涉及 AI 工具 / AI 决策 / AI 辅助 / 大模型 / 智能助手 / 智慧搜索等
  是 → 强制使用 --accent-purple(雾紫 #9B7BC4),结束
  否 → 进入 Step 1.5

Step 1.5. 判断画像是否"主题明显匹配某色板"(特例,优先于哈希)
  当画像核心场景与下表某条强吻合时,直接取对应色,不走哈希:
  ┌──────────────────────┬─────────────────────────────────────┐
  │ --accent-mist-blue   │ 文艺 / 治愈 / 阅读 / 音乐 / 安静沉思 │
  │ --accent-moss-green  │ 自然 / 健康 / 户外 / 运动 / 养生     │
  │ --accent-warm-orange │ 美食 / 生活 / 社交 / 温暖陪伴        │
  │ --accent-clay-red    │ 文化 / 复古 / 收藏 / 影视            │
  │ --accent-mustard     │ 童趣 / 家庭 / 烹饪 / 育儿            │
  └──────────────────────┴─────────────────────────────────────┘
  判断标准:画像名 / 核心场景 / 一句话需求里出现该列关键词或同义概念。
  若无明显匹配 → 进入 Step 2(哈希 fallback)

Step 2. 单画像哈希取色(fallback,主题不明显时用)
  对画像中文名所有字符求 unicode 总和,mod 5,从下表取色:
  ┌─────┬──────────────────────┐
  │ 0   │ --accent-mist-blue   │ 雾蓝
  │ 1   │ --accent-moss-green  │ 苔绿
  │ 2   │ --accent-warm-orange │ 暖橙
  │ 3   │ --accent-clay-red    │ 陶红
  │ 4   │ --accent-mustard     │ 芥末
  └─────┴──────────────────────┘
  哈希让同一画像名永远是同一色,可复现。

Step 3. 多画像并存时,顺序循环避免相邻同色
  适用场景:tab 切换、矩阵 4 象限、分布图 N 类。
  第 1 个画像:走 Step 1 → 1.5 → 2 取色作为起点。
  第 2-N 个画像:在 5 色环上顺时针取下一色,跳过 AI 类的紫色。
  色环顺序:雾蓝 → 苔绿 → 暖橙 → 陶红 → 芥末 →(回到雾蓝)
  AI 类画像强制紫,不参与循环计数(即如果第 3 个是 AI 类,第 4 个还是从第 2 个的下一位继续)。
  如果主题匹配 Step 1.5 的结果在循环中已被占用,可优先保留主题匹配色给主画像,其余画像走循环。
```

**例子**:
- "品质聆听者"(Hi-res 音乐画像)→ Step 1.5 命中"音乐/安静沉思" → 雾蓝(若走哈希会得到芥末,与主题不符)
- "驴友登山客"(户外画像)→ Step 1.5 命中"户外/运动" → 苔绿
- "盘古助手用户"(AI 类)→ Step 1 命中 → 雾紫
- "二次元手帐控"(主题不明显匹配色板)→ Step 2 哈希取色

**colour-token 列表**(完整定义在 `assets/templates/_design-tokens.css`):
- `--accent-purple` = #9B7BC4
- `--accent-mist-blue` = #7BA8C9
- `--accent-moss-green` = #6B8E5A
- `--accent-warm-orange` = #D97757
- `--accent-clay-red` = #B8665C
- `--accent-mustard` = #C9A55A

---

## 5. 渲染路径(P8 组件化,2026-05-25 起)

> P8 升级:**LLM 不再直接接触 `_base.html` 的 slot,也不再写 HTML 字符串**。LLM 的产出是 `过程稿/05-report.json`,Python `render_report.py` 拼装一切。

### 5.0 整体流程

```
LLM(你)                    Python(自动)
─────────                    ────────────
决策 layout(8 选 1)
决策 components(24 type 任选)
填每个 component 的 props
   ↓
05-report.json
   ↓
            validate_components_json.py(事前 schema 校验)
            ↓ 通过
            render_report.py
              ├─ 调用 ASSEMBLERS[layout](persona) 拼每个 slide
              ├─ grid_solver 自动布局 2b-grid(超载拆双页)
              ├─ build_nav 按 id 后缀自动配对 nav-pair/nav-trio
              ├─ 填 _base.html 的 {{slot}}
              ├─ 复制 _design-tokens.css + _components.css 到输出目录
              └─ validate_html.py P7 体检
            ↓
            report.html(交付)
```

### 5.1 LLM 决策范围(只做这些)

| 决策点 | 怎么决 | 参考 |
|---|---|---|
| 报告主题 | `metadata.theme` ∈ `2b` / `2c` / `2d` | 本文档 §1 |
| 信息密度 | `metadata.density` ∈ `high` / `mid` / `low` | 本文档 §1(双页时由 Python 自动切 mid,LLM 不操心) |
| 画像 layout | 每个 persona 的 `layout` ∈ 8 个 enum | 本文档 §2 |
| 2C accent | 每个 2C persona 的 `accent` ∈ 6 个 enum | 本文档 §4 |
| 画像 id | 按命名约定 `persona-N` / `persona-N-journey` / `persona-N-detail` 等 | 本文档 §3.2 |
| 组件清单 | 每个 persona 的 `components` 数组(从 24 type 挑) | `scripts/components/REGISTRY.md` §9.2 |
| 每个组件的 props | 严格匹配 `scripts/components/schemas/<type>.json` | 对应 schema 文件 |

### 5.2 LLM 不接触清单(Python 自动)

| 项 | 由谁负责 |
|---|---|
| `_base.html` 的 8 个 `{{slot}}` 填充 | `render_report.py` |
| `grid_solver` 12 列贪心布局(2b-grid) | `layouts/grid_solver.py` |
| 双页拆分 + density 切 mid | `assemble_layout_2b_grid()` 内 |
| nav-pair / nav-trio 按 id 配对 | `layouts/nav.py::build_nav()` |
| `--color-accent` inline 注入 | 各 2c assemble 函数 |
| 首个 slide `.active` class | `render_report.py::_inject_active_class()` |
| CSS 文件随包 | `render_report.py::_copy_css()` |
| SVG path(情绪曲线 / 矩阵点位 / snake 折线)| 各 renderer 内算法 |
| Unicode emoji 字符 | `assets/icons/emoji/<name>.png` 内置图片库(LLM 给语义名) |
| 矩阵 respondent label 方向自动避让 | `renderers/matrix.py` |
| `data-field-key` 注入(collab_flow 等)| renderer 硬编码 |

### 5.3 LLM 调用渲染的命令

```bash
# 命令一条:校验 + 渲染 + 体检 + 头像随包
python scripts/components/render_report.py \
    --input "过程稿/05-report.json" \
    --output "最终交付件-<项目名>-<时间戳>/report.html" \
    --project-dir "<项目运行目录>"
```

成功:终端输出 `[OK] <path>`,产物目录含 `report.html` + `_design-tokens.css` + `_components.css` + (若有匹配) `assets/画像头像素材/*.png`,可直接邮件分发。头像解析见 `steps/visual-assets.md` §1.1。

失败的两类:

1. **事前校验失败**(`validate_components_json` 报 ERROR)
   - Python 直接 raise,不会产 HTML
   - 错误消息含 `path`(`personas[0].components[2].props.blocks`)+ `code`(`P8-COMPONENT-PROPS`)
   - **修复**:照 path 找到 05-report.json 对应字段改

2. **事后体检 WARN**(`validate_html` 报 WARNING)
   - HTML 已经生成,但有视觉警告(如某画像 subtitle 跟别的画像重复)
   - **修复**:回到字段对齐阶段或证据抽取阶段补内容,**不要直接改 report.html**

### 5.4 渲染唯一路径(V9)

所有画像报告统一走 `scripts/components/render_report.py`。LLM 产出 `05-report.json`,Python 拼装 HTML。**禁止** LLM 直接写 report.html 字符串。

---

## 5.1. 渲染前样板对照(2C 真实测试后新增)
### 发布期交付目录规则

所有运行都必须落在用户可理解的中文目录下:

```text
用户画像报告输出/
└── <项目名>-<日期时间>/
    ├── 过程稿/
    ├── 画像头像素材/
    ├── 界面截图/
    └── 最终交付件-<对象类型>-<项目名>-<样本数>用户-<构建方式>/
        ├── report.html
        ├── _design-tokens.css
        ├── _components.css
        ├── assets/
        └── 交付件说明.md
```

生成前必须告诉用户(并已在字段对齐阶段主动问过,见 `steps/visual-assets.md`):

- **画像头像** → `<项目运行目录>/画像头像素材/`(建议 `<画像中文名>.png`)
- **典型场景 / 界面截图** → `<项目运行目录>/界面截图/`(2B 场景卡片、2C 专题 mockup、可选旅程关注点)

用户明确说不补充某类截图时,对应模块用文字+占位,不假装有图。用户补充截图后,先列出图片名并确认每张图对应哪个场景/关注点,再写入 `05-report.json`。

最终交付件目录名必须可读、可归档、可区分版本,固定使用:

```text
最终交付件-<对象类型>-<项目名>-<样本数>用户-<构建方式>
```

目录内只放交付相关文件。过程稿、日志、抽取 JSON、测试脚本留在 `过程稿/`。最终交付件必须能整包复制后打开,不能依赖工作目录里的隐藏文件或本机绝对路径。

渲染 2C 报告前,模型必须先对照 `docs/reference/layouts/` 或 `docs/reference/reports/` 下对应样板,只在现有骨架里选择合适布局,不修改 `_design-tokens.css`、`_components.css`、`_base.html`。

对照规则:
- 单画像主页 → 看 `docs/reference/layouts/2C-品质聆听者-单页.html`
- 主画像 + 专题详情 → 看 `docs/reference/layouts/2C-品质聆听者-双页.html`
- 用户旅程 → 看 `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` 旅程 tab
- 2 维坐标图 → 看 `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html`
- 多维分布图 → 看 `docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html`

如果视觉效果不理想,优先检查:
1. 是否选错 layout
2. 是否缺少用户提供的画像头像素材
3. section-block 是否有"标题 / 一句话总结 / 展开正文"三层
4. 是否用错密度或 accent
5. 是否字段过多导致页面拥挤

以上都检查后仍不理想,产出问题说明并回到字段对齐或素材补充阶段。**不能为了视觉优化直接改稳定骨架 CSS**。

### 渲染脚本职责(`render_report.py`)

1. 读 `05-report.json`(components JSON)
2. 跑 `validate.py` 事前 schema 校验
3. 按 `layouts/assemble.py` 拼装各 persona slide
4. 读 `_base.html`,填充 slot(`{{theme}}` / `{{persona_nav}}` / `{{main_content}}` 等)
5. 复制 `_design-tokens.css` + `_components.css` 到交付件目录
6. 按 `scripts/avatar_assets.py` 解析头像(用户 `画像头像素材/` → skill `assets/default-avatars/`),复制到交付件 `assets/画像头像素材/`
7. 写出 `report.html`
8. 自动跑 `validate_html.py`;ERROR 阻塞交付

### toC / toB / R4 / R5 统一路径

所有 layout(2B/2C/2D 单页、旅程、矩阵、分布)均通过同一 `render_report.py` 入口。**禁止** LLM 直接产 HTML 字符串。交付前必须:

```bash
python scripts/validate_html.py "<交付件>/report.html" --project-dir "<项目运行目录>"
```

---

## 5.5. 2C 单画像布局:拼贴 grid(不是分栏)

**重要更新(P4-v2)**:`layout-2c-portrait` 是**拼贴布局**,不是 38/62 分栏。

```
┌──────────┬────────────────────────────┐
│          │  代表原话色块(跨 2 列)     │
│ 身份卡   ├──────────┬─────────────────┤
│ (独立小卡)│ section1 │ section2        │
│ 大插画 + ├──────────┼─────────────────┤
│ 名字 +   │ section3 │ section4        │
│ meta 卡  ├──────────┴─────────────────┤
│          │ section5(可跨整宽,如核心痛点) │
└──────────┴────────────────────────────┘
```

CSS 已实现:`grid-template-columns: 32% 1fr 1fr`(身份卡 32% + 右侧 2 列各 34%)。

**主背景规范**:`--color-bg-page: #FCFAF5`(近白) — **不再铺米黄**。米黄只用作 `--color-bg-card-soft`(辅助色块底)。这避免了"灰扑扑融背景"问题。

**身份卡(.identity-card)的色块背景**:`--color-bg-illust = color-mix(accent 15%, bg-page)`——accent 是雾蓝就带蓝调,是暖橙就带橙调,**主题色自动跟随**。

**section-block 必须 3 层结构**:
```html
<div class="section-block">
  <div class="section-block-title">【胶囊小标题,3-5 字】</div>
  <div class="section-block-summary">【一句话粗体总结,15-25 字】</div>
  <div class="section-block-body">【展开正文,可含 <strong> 强调】</div>
</div>
```
**不允许只有标题+body 两层**——参考图 image002/005 的每个信息块都是"标题/总结/展开"三层结构,这是 2C toC 风格的核心特征。

**核心共识/痛点段**可加 `.full-width` 跨整宽:`<div class="section-block full-width">`。

---

## 5.6. 用户视觉素材规则(2B / 2C)

完整流程(三处检查点、标准话术、JSON 字段)见 **`steps/visual-assets.md`**。本节为渲染层技术约定。

**两类目录**:
- `画像头像素材/` — 头像与插画
- `界面截图/` — 典型场景截图 + 旅程关注点截图

| 对象 | 头像 | 典型场景截图 |
|------|------|----------------|
| **2B** | `identity_panel.persona_avatar.image_path` | `scenario_grid.scenes[].screenshot` |
| **2C** | `identity_card.illust_path`,旅程头图,detail 角落 | `mockup_list.mockups[].screenshot` |

**画像头像规则**:渲染前检查 `<项目运行目录>/画像头像素材/<filename>`:

- **存在** → 复制到 `assets/画像头像素材/`,渲染 `<img class="persona-avatar">` 或 `persona-illust`
- **不存在** → 首字/渐变色块占位;交付时须告知用户可补图(见 visual-assets 检查点 C)

**典型场景截图规则**:字段对齐与渲染前须问过用户。`scenario_grid` / `mockup_list` 的 `screenshot` 字段由用户确认映射后写入。Python 检查 `<项目运行目录>/界面截图/<filename>` — 不存在则形态 B(文字+占位图标)。

**2C mockup 截图素材**:每张须为**单屏** PNG/JPG;允许多张宽高不一,渲染时由 CSS 统一帧高、按比例缩放宽。勿把多屏合成图当一张文件直接引用(需先裁成多张再放入 `界面截图/`)。

**旅程关注点截图**(仅 `add_on_pages.journey=true`):`tob_focus_cell` / 旅程触点格,同一 `界面截图/` 目录,须单独确认 `screenshot_mapping`。

**推荐尺寸**:头像 240×320 px 以上,3:4 半身像,PNG 透明背景。

**多画像时**(R1/R3/R4/R5):每个画像各检查头像;场景映射注明画像名。有图用图、没图占位,**单画像间可混用**。

---

## 6. 实际样板参考(P1-P5 阶段产出)

下列样板用电力调度 / Hi-res 音乐两个真实研究数据,演示骨架在不同 layout 下的视觉效果。
**模型在新场景渲染前,可先打开对应样板对照结构**。

| 场景 | 主题 | 密度 | 布局 | 样板文件路径 |
|---|---|---|---|---|
| 2B 单画像单页(基准) | 2b | high | layout-2b-grid | `电力调度员-v2.html`(项目根目录) |
| 2B 单画像**双页**(画像核心 + 工作细节) | 2b | high | layout-2b-grid × 2 + persona-nav 切换 | `docs/reference/layouts/2B-电力调度员-双页.html` |
| 2B **多 persona tab**(3 个子角色) | 2b | high | layout-2b-grid × N + persona-nav 切换 | `docs/reference/layouts/2B-电力调度员-多tab.html` |
| 2C **单画像单页**(拼贴布局,白底) | 2c | low | layout-2c-portrait | `docs/reference/layouts/2C-品质聆听者-单页.html` |
| 2C **双页**(主画像 + 专题详情) | 2c | low | layout-2c-portrait + layout-2c-detail | `docs/reference/layouts/2C-品质聆听者-双页.html` |
| 2C **用户旅程图 v2**(5 阶段 × 5 维度,2 层信息 + 情绪色块 + 触点 + 机会点) | 2c | low | layout-2c-journey | `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` |
| 2C **2D 矩阵图**(4 象限 + 受访者点位) | 2c | low | layout-matrix-2d + layout-2c-portrait × 4 | `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` |
| 2C **多维分布图**(R5,3-5 个区分点 × N 类画像) | 2c | low | layout-distribution-multi + layout-2c-portrait × N | `docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html` |
| **2B 多角色 + L1 全景旅程 + L2 单角色旅程 9 tab 整合**(P4-toB 扩展) | 2b | high | layout-2b-grid × 4(画像) + layout-2b-journey × 5(1 L1 + 4 L2)+ 单层 nav | `docs/reference/reports/B-多角色/2B-DevOps五角色/report.html` |
| **2B R4 二维矩阵**(4 象限 + toB 画像 + L2 旅程) | 2b | high | layout-matrix-2d + layout-2b-grid × 4 + layout-2b-journey.is-l2 × 4 | `docs/reference/layouts/2B-R4矩阵-样板.html` |
| **2B R5 多维分布**(3 区分点 + toB 画像 + L2 旅程) | 2b | high | layout-distribution-multi + layout-2b-grid × N + layout-2b-journey.is-l2 × N | `docs/reference/layouts/2B-R5多维-样板.html` |
| └ R4 构建参考 | — | — | 勿照抄 HiRes toC 脚本 | `scripts/tools/build_tob_r4_layout_sample.py` |
| └ R5 构建参考 | — | — | 勿照抄 HiRes toC R5 脚本 | `scripts/tools/build_tob_r5_layout_sample.py` |
| └ 含 1 张 L1 全景旅程(角色 × 阶段聚合,4 角色 × 4 阶段) | 2b | high | layout-2b-journey.is-l1(`id=journey-l1`) | 上文件内 `#journey-l1` section |
| └ 含 4 张 L2 单角色旅程(每角色:阶段 × 工作流程/关注点/痛点) | 2b | high | layout-2b-journey.is-l2(`id=persona-N-journey`) | 上文件内 `#persona-1-journey` ... `#persona-4-journey` |
| └ 含 4 份 toB 画像页(Scrum Master/配置管理员/测试工具教练/测试人员) | 2b | high | layout-2b-grid(`id=persona-N`) | 上文件内 `#persona-1` ... `#persona-4` |

**`layout-2b-journey` 关键特征**(P4-toB 扩展新增):
- **形态切换**:`.is-l1` 用于全景(角色 × 阶段),`.is-l2` 用于单角色(阶段 × 维度行)
- **视觉规格**:顶部深色 banner(用 `--color-text-primary`)+ 左侧 rail(深色)+ 右侧主区(渐变蓝阶段头 → 灰底子阶段 → 浅蓝椭圆 pill 流程 → 白底关注卡片)。痛点合并进关注点卡片,使用 `.tob-focus-card.is-pain` 区分,不再单独放底部痛点 banner。
- **零新 token**:所有色全部用 v2 已有 token(`--color-primary` / `--color-primary-light` / `--color-warning` / `--color-warning-soft` / `--color-text-primary` 等),不引入新强调色
- **网格**:`--stages` inline var 控制阶段列数(默认 4);`--rail-rows` / `--main-rows` 控制行模板(L1 推荐 `auto auto repeat(N, 1fr)`,L2 推荐 `auto auto 1fr 1.4fr auto`)
- **L1 / L2 UML DSL 排布规则一致**(同一 `_render_uml_journey`):`slot` 按值横向定位、`track` 同格上下错行(重叠时最少节点下沉第二行)、`edges` 正交连线 + `branch`/`dashed`、节点 `type` 尺寸算法相同。详见 `REGISTRY.md` §3.3.1。
- **L1 独有**:多泳道 + §3.0.1 协同语义门禁(跨泳道边/decision/doc/dashed 下限);密度 `lanes × 子阶段总数 × 0.5`。
- **L2 独有**:通常单泳道;密度 `ceil(子阶段总数 × 1.2)`;`tools_touchpoints` 与 `stages` 等长;协同门禁豁免。禁止用模板凑密度代替访谈任务。
- **L1 协同 DSL**(同组织):**允许**跨泳道虚线边与判断分支,内容须来自访谈(参考电力调度员、`tob_journey_l1_coop.json`)。
- **数据 binding**:flow pill / UML 节点加 `data-evidence`,hover 弹 tooltip 查全量证据

**`layout-2c-journey` v2 关键升级**(P4 优化):
- **信息层次**:每个 journey-cell 用 2 层结构 — `.journey-cell-keyword`(胶囊小标签,3-5 字) + `.journey-cell-summary`(一句话总结,15-25 字)
- **阶段头**:`.journey-stage-number` 加编号 ① ② ③ ④ ⑤
- **触点维度(可选)**:`.journey-cell-touchpoint` + `.touchpoint-tag`,LLM 根据数据判断要不要加(如有"App 弹窗 / 支付页 / 音乐播放器"等明确触点描述就加)
- **痛点高亮**:`.journey-pain-highlight` 给高频共识(5/5 或 3/5)加 accent 色块底 + `.journey-pain-opportunity-tag` 标"💡 机会点"
- **情绪曲线**:SVG path 加 `.emotion-area` 闭合到底部填充半透明 accent(0.14 opacity);峰谷点用 `.journey-emotion-label`(`.above` / `.below`)绝对定位贴 emoji + 文字 label(如 🙂 略好奇 / 😕 困惑 / 😌 满意 / 🎧 稳定 / 😩 纠结)
- **画像-旅程绑定**:id 走 3.2 节 `persona-N-journey` 命名,nav 文字用 "画像名 · 旅程"

**双页切分原则**(见第 3 节):身份卡两页共享,工作细节页砍知识结构等长文,保留头像+名字+核心 meta+一句话需求。
**多 tab 切换原则**:nav 按钮文字直接用画像名(如"省级调度员"),不用"画像 1/2/3"这种代号。

---

## 已知限制(第一版接受)

1. **flow-cell 箭头 SVG 色不跟 accent 切换** — 待修:在 `_components.css` 或 renderer 层按 accent 注入 SVG,不再依赖已删除的 P7 脚本。
2. **黑色系主题未实现** — 仅留 hook,后续追加 `[data-theme="2b"][data-mode="dark"]` 等。
