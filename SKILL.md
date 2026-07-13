---
name: user-persona
description: 从用户访谈逐字稿和研究资料生成可追溯的用户画像、用户旅程与交互式 HTML 报告。当用户提到「用户画像」「persona」「访谈分析」「画像报告」「用户旅程」「从访谈生成画像」「访谈分类」时使用。支持 toB、toD、toC，以及 R1 至 R5 五种画像构建方式。
---

# User Persona Generator

## 先执行这 18 条

这些规则优先于后文和范式说明。每次启动、续跑、交接时都先读。

参数小于 100B 的模型只调用 `scripts/workflow.py`，禁止自行组合内部脚本。每次只运行一个子命令：`status`、`prepare-04`、`journey-review`、`prepare-05`、`seal`、`check --auto-recover` 或 `recover`。

1. 建好目录后的第一条用户可见消息必须原样发送 `init_run_dir.py` 返回的 `user_message`,显式告知本次工作目录和过程稿目录；并把路径写入 `00-research-goal.md/json`。
2. 固定落盘 7 对检查点文件：`00`、`01`、`02`、`03`、`04-personas`、`04-journeys`、`05`。每个检查点必须同时有同名 `.md` 和 `.json`。
3. 00 至 03 先写中文 MD 给用户确认，确认后固化 JSON。04 先写结构化草稿，再用 `workflow.py prepare-04` 生成中文 MD。05 先写 `05-report.draft.json`，再用 `workflow.py prepare-05` 生成只展示页面编排增量的中文 MD，用户确认后封存为 `05-report.json`。复杂 2B/2D 旅程按脚本提示运行四次 `journey-review`；简单 2C 和小型旅程一次确认。用户只需阅读中文语义，机器 ID、组件类型和枚举留在 JSON。
4. 七个节点必须分别停下等待确认。单独的“继续”“开始”“渲染”不能确认任何节点内容。03 对是否生成 L1/L2 的回答只确认范围。用户说“不确认”“看不懂”“看得头晕”“直接继续”时，保持待确认，缩小范围或分层重排 MD。禁止把确认短语拼接到用户原话中。确认后运行 `workflow.py seal`。
5. `02-classification` 对全部范式必交。R1/R2 写 `status: not_applicable` 和具体原因。
6. 禁止跳步,禁止只产 `05-report.json`,禁止直接手写最终 HTML。
7. 每次继续工作前先运行恢复检查,根据脚本给出的 `next_step` 续跑。
8. `processed/` 和 `extracted/` 必须逐份对应,数量和文件主名都要一致。
9. 渲染前必须通过检查点配对、字段对齐、组件 schema、HTML 合规四道门禁。公开渲染命令没有跳过校验参数。
10. LLM 只生成结构化 JSON。HTML、SVG 几何和 CSS 由固定渲染器与模板生成。
   `过程稿/` 只能保存数据文件。禁止创建自定义 Python、JavaScript、PowerShell、批处理或 HTML 构建器；禁止用 `[:N]` 等字符串切片拼装展示文案。
11. 视觉实现以 `assets/templates/_visual-system.json` 为机器真源,以 `steps/visual-style-guide.md` 为人类可读规则。禁止自创布局、颜色和组件。
12. 不得泄露受访者真实身份。证据要逐条可追溯,不得虚构、跨画像复用或用少量示例代替全量证据。
13. 预处理后立即生成并审核 `source-manifest.json`。样本按内容哈希去重，只把 `unique_primary_interviews` 称为访谈数；补充材料和多画像分配不得增加访谈数或提及频次。
14. 事实字段禁止推断。缺失统一写“材料未提及”。研究综合、用户补充和材料事实分别标为 `synthesis`、`user_context`、`primary/supplemental`。
15. 归并数据保留全部相关真值。`04-personas.json` 用 `field_decisions` 明示完整展示、压缩或省略及信息损失，`display_components` 是用户确认后的画像正文唯一真值；05 的画像页和细节页只写 `content_ref`。旅程逐元素写证据绑定；术语审计表先编译为 `terminology-glossary.json`。
16. 每个检查点结束只运行 `workflow.py check --target <当前节点> --auto-recover`。每个阻断必须同时返回恢复类型、官方恢复命令或安全降级路径。同一错误连续三次未解决，或错误总数连续三次没有下降时，生成恢复交付件并停止。错误数量持续下降视为有效进展。禁止在过程目录新增 `fix_*`、`sync_*`、`build_*` 临时脚本。
17. 确认短语遵循“先交付，后请求”。只有当前检查点 MD 已生成、已落盘，并已在本轮对话中交付给用户审阅，才允许请求该检查点的确认短语。生成内容前只能说明当前正在处理什么，禁止预告“跑完后请回复确认……”；禁止提前介绍下一检查点及其确认话术。用户无需记住未来回复格式。
18. 05 确认前必须运行完整渲染预检。`prepare-05` 一次返回全部上游硬错误；旅程证据、范式、归并快照、组件和 04/05 一致性未通过时，不生成 05 确认稿。渲染阶段只允许首次发现必须依赖真实 HTML 几何才能判断的视觉错误；失败时保留“预览-待修复”目录，禁止让任务无产物结束。机器可安全修复派生哈希和快照；涉及用户手改 MD、画像正文、旅程或证据的分叉必须保留两版并回到对应检查点，禁止自动覆盖。

若任何一条不满足,停止渲染并修复当前检查点。

开始任何范式前先读取 `steps/quality-contract.md`。九类质量标准适用于全部 R1-R5 分支，范式文件只能增加约束，不能降低该标准。
随后读取 `steps/scenario-coverage.md`，只保留当前 research type 与当前范式这一条分支。
每次执行和恢复还必须读取 `steps/recovery-workarounds.md`。门禁只负责发现问题，恢复文件规定如何继续、回退或安全交付。

## 启动与恢复

### 1. 建立工作目录

在用户项目目录下建立：

```text
<项目>/
├── input/                 # 原始访谈,只读
├── 过程稿/                # 用户对齐与系统续跑
│   ├── 00-research-goal.md
│   ├── 00-research-goal.json
│   ├── 01-paradigm.md
│   ├── 01-paradigm.json
│   ├── 02-classification.md
│   ├── 02-classification.json
│   ├── 03-field-alignment.md
│   ├── 03-field-alignment.json
│   ├── 04-personas.md
│   ├── 04-personas.json
│   ├── 04-journeys.md
│   ├── 04-journeys.json
│   ├── 05-report.md
│   ├── 05-report.json
│   ├── source-manifest.json  # 去重、证据层级和三类计数
│   ├── terminology-glossary.json # 存在术语审计表时必需
│   ├── processed/
│   ├── extracted/
│   └── reduced/
└── 交付件/                # report.html、CSS、头像等最终文件
```

将 `templates/checkpoints/CHECKPOINTS.md` 复制到项目根目录，作为交接清单。

### 2. 每次启动先恢复检查

```powershell
python scripts/workflow.py --workdir <项目目录> status
```

只执行输出中的 `next_step`。若脚本报告缺 MD、缺 JSON、JSON 无效、配对失败、只有最终报告、数量不一致或主名不一致,先修复该异常。

### 3. 每步都运行单节点门禁

```powershell
python scripts/workflow.py --workdir <过程稿目录> check --target <当前节点> --auto-recover
```

单节点门禁允许未来检查点尚未生成，不允许已出现的检查点存在空洞。只执行 `next_action`，不得同时修复其他错误。连续三次返回 `stopped_repeated_failure` 时停止自动修改。

完整状态机、状态字段和恢复规则见 `steps/checkpoint-workflow.md`。执行任何检查点前必须读取该文件。

## 00 到 05 的固定流程

| 节点 | 先写 MD 供用户确认 | 确认后写 JSON | 必须读取 |
|---|---|---|---|
| 00 研究目标 | 读者、核心问题、决策用途、范围 | `status: confirmed` | `steps/research-goal.md` |
| 01 范式选择 | 2B/2C、R1 到 R5、判断依据 | `status: confirmed` | 下方范式路由 |
| 02 分类依据 | 分类维度、边界、反例；R1/R2 写不适用原因 | `confirmed` 或 `not_applicable` | 对应范式文件 |
| 03 字段对齐 | 字段池、纳入/排除、视觉选择 | `user_confirmed: true` | `steps/field-alignment.md`、`steps/visual-assets.md` |
| 04 画像合并 | 官方脚本生成的中文画像全文 | 草稿 JSON 经确认后封存为 `status: confirmed` | `steps/extract-merge.md` |
| 04 用户旅程 | 中文全局图、角色 × 阶段矩阵、单旅程细节、分支与证据缺口 | 草稿 JSON 经确认后封存；无旅程写 `not_applicable` | `steps/journey-alignment.md` |
| 05 最终页面编排 | 只展示相对 03/04 新增的页数、详情页、内容分配和信息损失 | 草稿经确认后封存为 `05-report.json` | `steps/render-persona-page.md`、`steps/visual-style-guide.md` |

每一步严格执行：

1. 读取上一检查点 JSON 和本步说明。
2. 生成本步中文 MD，明确列出待确认项。04 必须先写结构化草稿 JSON，再由官方脚本生成 MD；05 必须先写 `05-report.draft.json`，再运行 `workflow.py prepare-05`，禁止提前写最终 JSON。
3. 在本轮对话中交付当前 MD 的路径和可审阅正文，然后才显示该 MD 内已经写明的当前确认短语。停止并等待用户明确确认或修改。
4. 把用户原话逐字写入本步 JSON。不得补写、拼接或改写确认短语。
5. 运行本步 schema 或校验脚本。
6. 运行渐进配对门禁。
7. 门禁通过后进入下一步。

用户说“按推荐来”时,仍需在 MD 中写出具体推荐及后果,再让用户确认该具体方案。

预处理完成后、开始抽取前执行：

```powershell
python scripts/build_source_manifest.py --workdir <过程稿目录>
```

审核每个来源的证据层级、画像分配和补充字段，将 `status` 改为 `reviewed`。输入中存在 `术语审计表*.md` 时，再执行：

```powershell
python scripts/build_terminology_glossary.py --input-dir <原始资料目录> --workdir <过程稿目录>
```

## 范式路由

根据研究输入选择一个主范式,不得把多个范式含混叠加。

### toC 路线选择等待态

toC 在 01 中必须把 A/B/C/D/E 五种路线及其适用条件展示给用户,并直接询问“你选 A/B/C/D/E 哪一种”。用户没有明确选择前,不能进入 Step 2。禁止把研究目标中的描述当作路线选择结果。`01-paradigm.json` 必须记录 `user_confirmed: true`、`choice_label` 和 `choice_reason`。

“我会按多区分点方式跑测试”属于模型替用户选路线,禁止输出这类直接推进话术。坐标图、多维分布图和其它 toC 路线都要由用户显式选择。

| 用户看到的方式 | 机器范式 | 含义 |
|---|---|---|
| A | R2 | 单一用户类型，合并为一个画像 |
| B | R1 | 用户已提供多个分组或角色 |
| C | R3 | 确认一个分类依据后形成多类画像 |
| D | R4 | 两个区分点形成二维矩阵 |
| E | R5 | 三到五个区分点形成多维分布 |

`choice_label` 与 `paradigm` 必须按表一一对应，校验器会阻止错配。

| 范式 | 使用条件 | 读取文件 |
|---|---|---|
| R1 已预分组 | 输入已按角色或画像分组 | `paradigms/R1-pregrouped.md` |
| R2 单角色 | 全部访谈属于一个角色 | `paradigms/R2-single-role.md` |
| R3 分类依据 | 用户提供一个明确分类维度 | `paradigms/R3-classify-basis.md` |
| R4 二维矩阵 | 两个维度交叉形成画像 | `paradigms/R4-2d-matrix.md` |
| R5 多变量 | 需要多变量聚类和人工解释 | `paradigms/R5-multi-variable.md` |

分类维度存在歧义时,在 `02-classification.md` 列出候选解释、边界和样例,由用户选择。不要自行猜测。

### 分类词显性确认硬规则

R3/R4/R5 的类别名、坐标轴档位名和多变量标签都会进入最终报告。02 必须列出全部分类词并获得用户显式确认,随后写入 `label_confirmed: true`。该字段缺失或为 false 时,不能进入画像合并和最终渲染。

## 内容硬约束

### 研究目标

所有“重要”“典型”“高价值”的判断都要回指 `00-research-goal.json`。研究目标改变时,回到 00 更新 MD/JSON,再重跑受影响步骤。

### 字段与内容

- 03 必须展示完整字段池、纳入字段、排除字段及理由。
- 用户未确认的字段不得进入 04 或 05。
- 用户未确认的旅程不得进入 05。05 中的旅程组件必须与 `04-journeys.json` 完全一致。
- 渲染器不得截断数组、文本、证据、旅程节点或画像数量。
- 内容过密时调整布局或分页,保留完整内容。
- 中文报告清理模型痕迹,避免把 `Key insight:`、`Evidence:` 等英文标签直接展示给用户。

### 证据

- 每条结论至少连接一条可定位证据。
- 证据保留来源文件、受访者匿名 ID、段落或行号。
- 同一句引文不得支撑不同画像的独立结论。
- 引文与解释分字段保存,不得改写后冒充原话。
- 04 必须覆盖全部纳入访谈,并说明未采用材料的原因。

### 隐私

- 姓名、公司内部账号、手机号、邮箱、精确地址等全部脱敏。
- 证据来源使用抽取脚本生成的稳定匿名 `_source_id`，格式为 `P` 加 8 位十六进制字符。展示层也可使用脱敏身份称呼。
- 头像只使用用户授权素材或生成的非真人映射形象。
- 最终 HTML、JSON、文件名和元数据都要扫描身份泄露。

### toB/toD 组织同构

多角色报告在绘制 L1 整体旅程前,必须判断角色是否共享同一组织级任务、阶段和交付目标。若同构,共享一套阶段骨架并保留角色泳道。若不满足,分别输出角色旅程,不得强行拼接。细则见 `steps/field-alignment.md`。

### 视觉素材

03 必须询问头像和典型场景截图。记录用户提供、授权生成、占位或不使用的选择。未经确认不得自动加入网络图片。

## 视觉系统硬约束

执行视觉阶段前读取 `steps/visual-style-guide.md`。脚本和模型共同遵守 `assets/templates/_visual-system.json`。

### 通用规则

- 页面背景为白色。
- 可读正文最小字号为 12px。
- 使用设计系统中的字体、间距、圆角、边框和组件结构。
- CSS token 承载颜色语义,禁止在组件里散落无语义色值。
- 图标使用固定图标组件。禁止输出 Unicode emoji 字符和自写 SVG path。

### 2B

- L1 整体旅程与单角色旅程共用阶段、子阶段、角色列、节点、连线、字号、颜色和边框契约。
- 阶段列宽和角色轨道来自同一几何源,禁止目测复制。
- 模型只给节点数据与连接关系,渲染器生成几何和 SVG。

### 2C

- 每个画像只选择一套 TO C 色卡。
- 同一画像的画像页、细节页、分布图和旅程页使用同一套色卡。
- 禁止跨色卡借色。未知或废弃的 `accent` 必须报错,不得静默回退。
- 旅程阶段头使用当前色卡浅表面色,文字用深色,编号和下边框用主色。
- 触点、工具、证据标签使用当前色卡辅助跳色,不得直接复用主色背景。
- 2C 分布图和旅程图所有可读文字不小于 12px。
- 多画像报告在 `visual_spec.persona_palette_map` 显式记录 `persona-N` 到色卡 ID 的映射。

## JSON 与渲染职责

`05-report.json` 必须符合 `scripts/components/schemas/report.json`,并只使用已注册组件。模型不得生成 HTML 字符串、内联脚本、SVG path 或 CSS 片段。

组件 schema 和渲染器负责：

- 允许字段与类型
- 数组完整性
- 设计 token 注入
- 2B 旅程几何
- 2C 色卡映射
- HTML 转义与结构

## 渲染前四道门禁

在完整工作流中按顺序执行：

```powershell
python scripts/validate_checkpoint_pairing.py --workdir <过程稿目录> --require-complete
python scripts/validate_field_alignment.py --workdir <过程稿目录>
python scripts/validate_journey_checkpoint.py --workdir <过程稿目录>
python scripts/validate_components_json.py --workdir <过程稿目录> 05-report.json
python scripts/components/render_report.py --input <项目目录>\过程稿\05-report.json --output <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
python scripts/validate_html.py <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
```

`render_report.py` 会再次执行完整检查点门禁。缺失任一对文件、只有最终报告、03/05 字段或 `visual_spec` 不一致、组件非法时必须失败。

任何校验失败都要回到最早出现问题的检查点修复。不得用参数、手工复制或修改最终 HTML 绕过。

## 交付前检查

- 00 到 05 共 14 个检查点文件齐全且同名配对，其中 04 包含画像与旅程两对文件。
- 02 在 R1/R2 中也存在,状态和原因有效。
- `processed/` 与 `extracted/` 数量、主名逐份一致。
- 03 与 05 的字段、主题、密度、布局、色卡映射一致。
- 04 的画像、证据和 05 的组件一一对应。
- `04-journeys.json` 与 05 的全部旅程组件逐项一致；不生成旅程时也有明确的不适用记录。
- 最终 HTML 无身份泄露、无非法组件、无跨色卡、无小于 12px 的 2C 文字。
- 最终交付件包含 HTML、依赖 CSS、授权视觉素材和必要说明。
- `workflow.py status` 报告 `completed`，全部校验脚本返回成功。

## 错误处理

- 缺文件：补齐最早缺失的 MD/JSON 对,再重跑恢复检查。
- JSON 无效：修复 JSON,不要删除已确认的 MD。
- 用户修改上游决定：从该检查点重新确认,删除或标记后续产物过期,按顺序重建。
- 数量不一致：逐份核对 `processed/` 和 `extracted/`,不得用改计数掩盖缺文件。
- 视觉错误：修复设计 token、`visual_spec` 或组件数据,不要直接补丁最终 HTML。
- 证据或隐私错误：回到 04 修复证据映射或脱敏,再重建 05。
- 旅程阶段、节点或证据错误：回到 `04-journeys.md` 重新让用户确认,再重建对应 JSON 和 05。

## 按需读取地图

只读取当前步骤需要的详细文件,避免把全部说明同时塞入弱模型上下文。

- 检查点与恢复：`steps/checkpoint-workflow.md`
- 全范式质量标准：`steps/quality-contract.md`
- R1-R5 与 toB/toC/toD 分支表：`steps/scenario-coverage.md`
- 研究目标：`steps/research-goal.md`
- 字段对齐与组织同构：`steps/field-alignment.md`
- 逐份提取、合并、证据与隐私：`steps/extract-merge.md`
- 用户旅程确认：`steps/journey-alignment.md`
- 头像与场景图：`steps/visual-assets.md`
- 视觉设计系统：`steps/visual-style-guide.md`
- 页面组件：`steps/render-persona-page.md`
- 视觉系统选择补充：`steps/visual-system.md`
- 检查点模板：`templates/checkpoints/`
- 报告 schema：`scripts/components/schemas/report.json`

## 文件用途速查

弱模型第一次执行时先看本表，只读取当前阶段需要的文件。

| 路径 | 用途 | 何时使用 |
|---|---|---|
| `templates/checkpoints/` | 00 到 05 的 MD/JSON 过程稿模板 | 每个检查点开始时复制对应模板 |
| `assets/prompts/` | 单访谈抽取、字段合并、分类和区分点 prompt | 运行抽取或 reduce 脚本时由脚本读取 |
| `assets/templates/` | HTML 骨架、CSS token、组件样式和机器视觉系统 | renderer 自动读取，模型只读 `_visual-system.json` |
| `assets/default-avatars/` | 可直接使用的默认非真人画像头像 | 用户允许默认头像且画像名能匹配时复制到交付件 |
| `schemas/` | toB、toC 字段库和分类依据 | 00 到 03 做研究类型、分类与字段对齐时读取 |
| `paradigms/` | R1 到 R5 的差异化流程 | 01 确认范式后只读对应文件 |
| `scripts/components/schemas/` | 05 组件 JSON 的机器 schema | 组装与校验 05 时使用 |
| `scripts/` | 预处理、抽取、恢复、校验和渲染 | 按本文件给出的命令执行 |
| `docs/reference/reports/` | 人类查看的静态完整样例 | 只用于说明书和视觉验收，不参与运行时生成 |

执行结束时向用户说明当前检查点、已确认决策、下一步和恢复命令。
