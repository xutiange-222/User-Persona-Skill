# Component Registry

本文件帮助模型选择组件。props 的字段、类型、长度和枚举以 `scripts/components/schemas/*.json` 为唯一机器真值，layout 组合以 `scripts/components/layouts/layout_rules.py` 为准。

## 1. 选择顺序

1. 从 `03-field-alignment.json` 读取研究类型和 `visual_spec`。
2. 从 `04-personas.json` 读取已确认画像内容。
3. 从 `04-journeys.json` 读取已确认旅程组件 props。
4. 按 `steps/visual-system.md` 选择 layout。
5. 只选择该 layout 允许的 component。
6. 逐个读取对应 schema 后填写 props。
7. 写 `05-report.draft.json`，运行 `workflow.py prepare-05` 生成增量确认 MD；用户确认后封存为 `05-report.json`。

禁止自创 component type、props key、layout 或 CSS class。

## 2. Layout 与 component 组合

| layout | 必需 component | 允许的补充 component |
|---|---|---|
| `layout-2b-grid` | `identity_panel` | `resp_rings`、`collab_flow`、`scenario_grid`、`ai_scenario_grid`、`painpoint_list`、`titled_list`、`generic_text`、`generic_bullet`、`generic_kv` |
| `layout-2b-grid-detail` | 至少一个详情组件 | 与 2B grid 相同，但不放 `identity_panel` |
| `layout-2b-journey` | `tob_journey_l1` 或 `tob_journey_l2`，恰好一个 | 无 |
| `layout-2c-portrait` | `identity_card`、`persona_quote_pull`、`section_blocks_grid` | 无 |
| `layout-2c-detail` | `detail_headline`、`mockup_list`、`detail_analysis` | `detail_illust_corner`、`persona_quote_pull` |
| `layout-2c-journey` | `journey_2c` | 无 |
| `layout-matrix-2d` | `matrix_guidance_strip`、`matrix_2d` | 无 |
| `layout-distribution-multi` | `distribution_multi` | 无 |

数量范围仍以 `layout_rules.py` 为准。表格与代码冲突时停止渲染并修复文档漂移。

## 3. 旅程组件

### 3.0 L1 协同语义门禁

`tob_journey_l1` 用于同一组织或产品流程中的多角色协作。多角色 L1 必须表达真实协同：

- 跨泳道边用于角色交接、指令传递、审核、反馈或产物移交。
- `decision` 用于有证据的关键分叉。
- `doc` 用于有证据的文档或交付物。
- `dashed` 用于异步通知或系统推送。
- 节点和边都引用有效 lane、stage 和 node id。
- 协作语义只从 04 已确认内容和画像 collaboration 字段提取。

真值范例：`scripts/components/tests/golden_samples/tob_journey_l1_coop.json`。

完全独立的多角色不生成 L1，只生成各自 `tob_journey_l2`。

### 3.0.2 判断分支

- 判断节点 label 使用清晰问句。
- 至少有一条 `branch: yes`。
- `branch: no` 只在存在独立补救任务时使用。
- 无补救任务时，把条件和影响写入关注点。
- 禁止让否分支回指主线前序节点形成假循环。

### 3.1 `tob_journey_l1`

必填：`banner_title`、`banner_subtitle`、`stages`、`lanes`、`nodes`、`edges`。

模型提供语义 DSL，Python 计算节点位置、连线、角色 rail 和 SVG。阶段、子阶段、角色列、节点类型和线条语义必须与 2B L2 保持一致。

### 3.2 `tob_journey_l2`

必填字段与 L1 相同。L2 绑定单个画像，使用该画像的阶段、工作流、工具触点、关注点和证据。不得从其他画像借用节点或证据。

### 3.3 `journey_2c`

必填：`title`、`subtitle`、`stages`、`dimensions`、`cells`、`emotion`。

- `cells` 外层与 dimensions 对齐，内层与 stages 对齐。
- 阶段通常 4 至 6 个，维度通常 3 至 5 个。
- 每个画像独立生成 cells 和 emotion。
- 触点、工具和证据标签使用当前画像 palette pack 的辅助色。
- 旅程 props 必须与 `04-journeys.json` 完全一致。

## 4. 2B 与 2D 组件

| type | 用途 | 主要必填 props |
|---|---|---|
| `identity_panel` | 头像、名称、描述、元信息、一句话需求 | `persona_avatar`、`identity_name`、`identity_desc`、`identity_meta_rows`、`one_sentence_need` |
| `resp_rings` | 二至三项职责占比 | `rings` |
| `collab_flow` | 需求来源、交付物、下一步流转、KPI | `demand_source`、`deliverables`、`downstream_flow`、`kpi` |
| `scenario_grid` | 典型业务场景、工具和截图 | `scenes` |
| `ai_scenario_grid` | AI 辅助场景 | `scenes` |
| `painpoint_list` | 痛点、细节、提及比例和证据 | `items` |
| `titled_list` | 标题加说明的通用列表 | `module_title`、`items` |
| `generic_text` | 一段短文本 | `module_title`、`text` |
| `generic_bullet` | 短句列表 | `module_title`、`items` |
| `generic_kv` | 两列键值信息 | `module_title`、`rows` |

`collab_flow` 的 key 固定，显示 label 由 renderer 生成。模型不能填写 `upstream`、`self_role` 或其他别名。

## 5. 2C 组件

| type | 用途 | 主要必填 props |
|---|---|---|
| `identity_card` | 画像名、副标题、标签和插画 | `name`、`subtitle`、`meta_tags` |
| `persona_quote_pull` | 一条代表原话 | `quote`、`source` |
| `section_blocks_grid` | 4 至 6 个画像段卡 | `blocks` |
| `section_block` | 段卡内部结构 | `title`、`summary`、`body`、`evidence_quotes` |
| `detail_headline` | 专题详情大标题 | `headline` |
| `mockup_list` | 一至三张产品或场景图 | `mockups` |
| `detail_analysis` | 二至三段专题解读 | `sections` |
| `detail_illust_corner` | 可选角落插画 | 读取 schema |

`section_blocks_grid` 的合法结构由 schema 的 `oneOf` 约束。当前支持 4、5、6 个 blocks，不满足时直接校验失败。

## 6. 总览组件

| type | 用途 | 主要必填 props |
|---|---|---|
| `matrix_guidance_strip` | R4 读图引导 | `items` |
| `matrix_2d` | 坐标轴、象限和受访者点位 | `axis_labels`、`quadrants`、`respondents` |
| `distribution_multi` | R5 区分点、档位和画像曲线 | `title`、`subtitle`、`value_variables`、`personas` |

矩阵和分布总览只展示分类结构。每个点位或分布判断保留对应受访者证据。

### 6.3 情绪图标

`journey_2c.emotion[].emoji` 只使用 schema 枚举的语义名。常用映射：

| 情绪 | enum |
|---|---|
| 满意、轻松 | `smile`、`content`、`relaxed` |
| 好奇、思考 | `thinking`、`raised_eyebrow` |
| 困惑、中性 | `confused`、`hmm`、`neutral` |
| 失望、受挫 | `disappointed`、`frustrated`、`tired` |
| 惊喜、兴奋 | `surprised`、`excited`、`celebrate` |
| 音乐、灵感、目标 | `headphone`、`light_bulb`、`target` |

模型填写语义名，renderer 负责图片。JSON 中不直接写 Unicode emoji。

## 7. 证据与文本

- 所有 evidence quote 保留原文和稳定 source。
- `mention_count`、`mentioned_by`、`evidence_quotes` 三向一致。
- 同一原话最多支撑两个确实相关的观点，三处及以上复用会被拦截。
- 报告语言使用短句、具体动作、明确对象和可观察事实。
- 避免空泛术语、宣传口号和没有证据的推断。
- 用户可见文本遵守 `assets/prompts/_shared-language-contract.txt`。

## 8. 2C 色卡

模型只填写 accent 白名单值：`purple`、`warm-orange`、`moss-green`、`mustard`、`mist-blue`、`cyan-gold`。

Python 从 `_visual-system.json` 注入完整 palette pack。同一画像的 portrait、detail、journey 必须使用同一 accent。禁止手写 `--color-toc-*`。

## 9. 生成 05 的最小检查

### 9.1 Persona id

- 画像：`persona-N`
- 详情：`persona-N-detail` 或 `persona-N-detail-M`
- 单画像旅程：`persona-N-journey`
- L1 总体旅程：`journey-l1`
- R4 总览：`matrix`
- R5 总览：`distribution`

### 9.2 完整 component type 清单

可直接放入 `personas[].components[]` 的类型：

`identity_panel`、`resp_rings`、`collab_flow`、`scenario_grid`、`ai_scenario_grid`、`painpoint_list`、`titled_list`、`generic_text`、`generic_bullet`、`generic_kv`、`tob_journey_l1`、`tob_journey_l2`、`identity_card`、`persona_quote_pull`、`section_blocks_grid`、`detail_headline`、`mockup_list`、`detail_analysis`、`detail_illust_corner`、`journey_2c`、`matrix_guidance_strip`、`matrix_2d`、`distribution_multi`。

`section_block` 是 `section_blocks_grid.blocks[]` 的内部结构。`report.json` 是总报告 schema，二者都不作为顶层 component type 使用。

### 9.3 提交前

1. 逐个 component 读取对应 schema。
2. 检查 layout 组合和数量。
3. 检查 journey 与 04 一致。
4. 检查 visual_spec 和 persona palette map。
5. 生成 `05-report.draft.json`，运行 `workflow.py prepare-05` 并等待用户确认增量页面编排。
6. 确认后封存为 `05-report.json`，再调用唯一渲染入口。
