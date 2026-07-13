# 视觉系统执行入口

本文件只负责路由。完整视觉规则见 `steps/visual-style-guide.md`，机器真值见 `assets/templates/_visual-system.json`，CSS 实现见 `assets/templates/_design-tokens.css` 和 `_components.css`。

## 先记住六条

1. 模型只生成 `05-report.json`，不得直接写 `report.html`。
2. layout、component、accent 必须从白名单选择，不得自创。
3. `03-field-alignment.json.visual_spec` 与 `05-report.json.metadata.visual_spec` 必须一致。
4. 旅程内容必须逐项来自已确认的 `04-journeys.json`。
5. Python 负责模板拼装、色板注入、导航、资源复制和 HTML 校验。
6. 任何校验失败都要回到对应检查点修复 MD 和 JSON，再重新渲染。

## 文件分工

| 文件 | 用途 | 模型是否修改 |
|---|---|---|
| `assets/templates/_visual-system.json` | 主题、色板、字号和组件视觉契约的机器真值 | 否 |
| `assets/templates/_design-tokens.css` | 基础属性、语义 token、主题 palette pack | 否 |
| `assets/templates/_components.css` | 已注册组件和 layout 的稳定样式 | 否 |
| `assets/templates/_base.html` | 报告 HTML 骨架、导航和 tooltip | 否 |
| `scripts/components/schemas/report.json` | `05-report.json` 的总 schema | 否 |
| `scripts/components/schemas/*.json` | 每个 component 的 props schema | 否 |
| `scripts/components/layouts/layout_rules.py` | layout 与 component 组合白名单 | 否 |
| `docs/reference/reports/` | 人类可浏览的视觉样例 | 只查看 |

## 主题与密度

| 研究类型 | `metadata.theme` | 默认 `metadata.density` |
|---|---|---|
| toB | `2b` | `high` |
| toD | `2d` | `high` |
| toC | `2c` | `low` |

用户明确要求更多留白或更高信息密度时，可以在 `low`、`mid`、`high` 中调整。2C 多维分布和旅程仍须保证所有可读文字不小于 12px。

## 八个合法 layout

| layout | 适用场景 | 关键组件 |
|---|---|---|
| `layout-2b-grid` | 2B/2D 画像核心页 | `identity_panel` 加已注册业务组件 |
| `layout-2b-grid-detail` | 2B/2D 工作细节页 | 已注册详情组件 |
| `layout-2b-journey` | 2B/2D 总体或单角色旅程 | `tob_journey_l1` 或 `tob_journey_l2` |
| `layout-2c-portrait` | 2C 画像主页 | `identity_card`、`section_blocks_grid` 等 |
| `layout-2c-detail` | 2C 专题详情页 | `detail_headline`、`mockup_list` 等 |
| `layout-2c-journey` | 2C 单画像旅程 | `journey_2c` |
| `layout-matrix-2d` | R4 二维矩阵总览 | `matrix_2d` |
| `layout-distribution-multi` | R5 多维分布总览 | `distribution_multi` |

精确的必需组件、允许组件和数量范围以 `layout_rules.py` 为准。layout 无法承载已确认内容时，回到 `03-field-alignment` 调整字段或拆页。

## 范式路由

| 范式 | 总览 | 画像页 | 旅程页 |
|---|---|---|---|
| R1 预分组 | 多画像导航 | 按研究类型选择 2B/2D 或 2C | 按 `04-journeys.json` 生成 |
| R2 单角色 | 单画像导航 | 按研究类型选择 2B/2D 或 2C | 按 `04-journeys.json` 生成 |
| R3 分类依据 | 多画像导航 | 按研究类型选择 2B/2D 或 2C | 按 `04-journeys.json` 生成 |
| R4 二维矩阵 | `layout-matrix-2d` | 每类独立画像页 | 每类独立旅程页 |
| R5 多维分布 | `layout-distribution-multi` | 每类独立画像页 | 每类独立旅程页 |

R4/R5 总览只承载分类结构。画像正文和旅程进入各自子页。研究类型决定子页使用 2B/2D 组件族或 2C 组件族。

## 2B 旅程硬规则

- L1 总体旅程只用于同一组织或产品流程中的多角色协作。
- 完全独立的多个角色只生成各自 L2 旅程。
- L1 和 L2 共用阶段、子阶段、角色列、节点、线条、字号、颜色和边框语义。
- L1 必须包含来自证据的跨泳道协作、交接或判断语义。
- 节点类型、几何和连线规则以 `visual-style-guide.md` 和 renderer 为准。
- 旅程节点和关键流程必须绑定 evidence。

## 2C palette pack 硬规则

- 每个画像从白名单选择一套 accent，Python 注入完整 palette pack。
- 同一画像的画像页、详情页、旅程页使用同一套 palette pack。
- 多维分布节点、图例、导航和对应画像页使用同一映射。
- 任何页面都不得跨色卡借色。
- 触点、工具、证据标签使用当前色卡的 `aux` 和 `aux-bg`。
- 页面背景为白色。高饱和主色只用于重点和小面积信号。
- 旅程阶段表头使用当前画像的浅承载层，禁止整行铺高饱和主色。
- 2C 多维分布和旅程中的可读文字最小字号为 12px。

## 页面组合与命名

- 单画像：`persona-1`
- 画像详情：`persona-1-detail` 或 `persona-1-detail-N`
- 单画像旅程：`persona-1-journey`
- L1 总体旅程：`journey-l1`
- 画像、详情和旅程的导航必须相邻成组。
- 首个可浏览页面由渲染器添加 `active`。

## 素材规则

- 用户头像优先从项目的 `画像头像素材/` 读取。
- 用户未提供头像时，可使用 `assets/default-avatars/` 中与画像匹配的默认头像。
- 产品和场景截图从项目的 `界面截图/` 读取。
- 素材路径、画像映射和用户选择记录在 `03-field-alignment.json.visual_assets`。
- 交付目录必须自包含，禁止依赖本机绝对路径。

## 唯一渲染命令

```powershell
python scripts/components/render_report.py --input <项目目录>\过程稿\05-report.json --output <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
```

渲染入口依次执行检查点配对、字段对齐、旅程一致性、组件 schema、模板拼装和 HTML 合规检查。即使调用方请求跳过普通校验，检查点和旅程门禁仍会执行。

## 样例选择

| 目标 | 样例 |
|---|---|
| 2B 单画像 | `docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html` |
| 2C 单画像 | `docs/reference/reports/A-单画像/2C-内行场景派/report.html` |
| 2B 多角色与 L1/L2 旅程 | `docs/reference/reports/B-多角色/2B-DevOps五角色/report.html` |
| 2C 二维矩阵 | `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` |
| 2C 多维分布 | `docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html` |

样例用于理解结构和密度。生成时仍以当前 schema、视觉真值和脚本校验结果为准。
