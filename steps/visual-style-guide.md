# Visual Style Guide

本文件是画像最终交付物的视觉规范。模型必须先选业务类型、模板和色板，再填写内容。规范落点分三层：

- 规则文档：`steps/visual-style-guide.md`
- 机器可读设计系统：`assets/templates/_visual-system.json`
- CSS token：`assets/templates/_design-tokens.css`
- 组件样式：`assets/templates/_components.css`

设计系统采用四层结构：基础属性、语义 token、主题 palette pack、组件契约。`_visual-system.json` 是渲染器与校验器的共同事实源；本文件负责告诉模型如何选择，CSS 负责呈现。三者出现冲突时禁止渲染，先修复契约漂移。

## 最高优先级原则

1. 报告组件 JSON 只能选择本文件列出的模板、色板和组件填充规则。
2. 2B 默认强调流程、阶段、职责、协同和风险信号。
3. 2C 默认强调画像个性、生活方式、动机、场景和情绪节奏。
4. 不得自创 layout、色板名称、组件类型或视觉结构。
5. `03-field-alignment.json` 必须写入 `visual_spec`，`05-report.json.metadata.visual_spec` 必须保持一致。
6. 视觉素材必须先问用户，并记录在 `visual_assets`。
7. 最终 HTML 必须通过 `scripts/validate_html.py`，CSS 视觉契约报 ERROR 时禁止交付。

## 通用规范

- 页面采用 V9 组件化渲染体系，由 `scripts/components/render_report.py` 输出 HTML。
- 组件数量、layout、props 必须通过 `scripts/validate_components_json.py` 和 `scripts/components/schemas/report.json`。
- 颜色只能从本文件色板选择。需要微调时，只能在 CSS token 层做少量校准。
- 固定格式 UI 必须有稳定尺寸，避免 hover、标签、按钮、节点文本造成布局跳动。
- 字号不随 viewport 缩放，letter-spacing 固定为 `0`。
- 页面不使用单一色相堆叠，不使用装饰性渐变球、光斑、漂浮卡片。
- 文本不得遮挡上下文。按钮、节点、标签里的文字必须完整可读。

## 2B 规范：流程与旅程

### 色板 `2b-process-blue`

| 用途 | 色值 |
| --- | --- |
| 主流程蓝 | `#96BEFA` |
| 浅蓝底 | `#DCF0FA` |
| 节点蓝 | `#6EA0DC` |
| 重点蓝 | `#3296FF` |
| 警告红 | `#DC2828` |
| 警告浅底 | `#FAE6E6` |
| 完成绿 | `#8CBE6E` |
| 中性线 | `#DCDCDC` |
| 次级文字 | `#B4B4B4` |
| 辅助文字 | `#787878` |
| 主文字 | `#282828` |

### 模板 `2b-overall-journey`

适用：toB/toD 多角色、同组织协作、需要呈现整体流程。

固定结构：

1. 顶部：研究目标与总体流程一句话。
2. 主体：横向阶段流，每个阶段包含角色、任务、关键系统、交接物。
3. 风险层：用警告红标注阻塞点、返工点、责任不清点。
4. 完成层：用完成绿标注顺畅节点和价值兑现点。
5. 证据层：每个关键节点必须绑定可追溯 hover。

推荐组件：

- L1 全局页：`layout-2b-journey` + `tob_journey_l1`
- 单角色页：`layout-2b-journey` + `tob_journey_l2`
- 补充组件：`collab_flow`、`scenario_grid`、`painpoint_list`、`generic_kv`

### 2B L1 总体旅程样式锁定

- 标题和说明在同一块浅灰蓝底上，背景 `#EDF3F7`，左对齐。
- 标题文字 `#282828`，说明文字 `#787878`。
- 阶段、子阶段、左侧角色列共用中性层级，用灰线 `#DCDCDC` 分隔。
- 阶段表头、子阶段表头、下方 SVG 泳道必须使用同一个几何源。L1 viewBox 为 `1180`，左侧 rail 为 `87`；其余宽度必须按实际阶段数等分，并由 renderer 写入 `--l1-grid-columns`。禁止把 5 阶段比例固化到 CSS，因为 4、6 或更多阶段会换行错位。
- 同一泳道与阶段内的节点按 `slot` 顺序等距排布；`slot` 有数字空洞时先压紧。节点发生横向碰撞时，renderer 必须计算最少无碰撞轨道，可从两轨自动扩展到三轨或更多轨道。禁止依靠删节点、截断标题或缩小到不可读字号解决碰撞。
- 左侧表头列宽必须与下方角色列一致，当前 CSS 锁定为 viewBox 中的 `87/1180`。禁止用 `92px`、`repeat(...)`、`fr` 手调模拟。
- 阶段头使用主流程蓝 `#96BEFA`，文字白色，字号 `14px`。
- 子阶段使用浅蓝底 `#DCF0FA`，文字和分隔符均为黑色，字号 `12px`。
- 阶段行底色必须承接 `#96BEFA`，子阶段行底色必须承接 `#DCF0FA`，避免箭头裁切后露出白色条或白色三角。
- 左侧角色栏固定在 `87px` 轨道内居中排版。角色名横排显示，字号 `12px`，必须完整显示；超过 4–5 个汉字时用 `tspan` 自然断成两行，优先按 `工程师`、`负责人`、`管理者` 等语义后缀断行。
- 左侧角色动作标签是独立下一行，字号不低于 `11px`，与角色名至少保持 14px 纵向间距。禁止使用旧的 `x=36` 角色名 + `x=60` 标签坐标写法，因为长角色名会和标签重叠。
- 普通步骤节点使用节点蓝 `#6EA0DC`，文字白色，不加边框。
- 操作类节点使用浅灰底 `#F3F3F3`，蓝色描边 `#6EA0DC`。
- 起止节点使用完成绿 `#8CBE6E`，不加边框。
- 判断节点使用警告浅底 `#FAE6E6`，文字黑色，不加边框。
- 文档类节点使用浅紫底 `#EAE5FF`，文字黑色，不加边框。
- 节点文字最低字号 `12px`。
- 连线使用中性灰，不使用高饱和色。

### 2B L2 单角色旅程样式锁定

- L2 旅程页的阶段、子阶段、工具触点、工作流节点必须与 L1 总体旅程保持一致。
- L2 左侧 rail 宽度固定为 `87px`，阶段、子阶段、工具触点、工作流、关注点左栏对齐。
- L2 阶段 rail 和子阶段 rail 字号为 `12px`。
- L2 阶段头使用 `#96BEFA`，字号 `14px`，右侧不得出现旧样式白色遮挡三角。
- L2 子阶段使用 `#DCF0FA`，字号 `12px`，分隔符 `›` 也是黑色。
- L2 工具触点标签字号为 `12px`。
- L2 工作流 SVG 外层不得出现细灰色整体边框。
- L2 工作流行高必须按泳道数计算，SVG 使用完整宽度与对应高度。禁止用固定 `max-height` 同比缩小整张流程图。
- L2 内嵌 UML 节点沿用 L1 节点规则，普通节点、判断节点、文档节点不额外加边框。
- 渲染完成后必须运行 `scripts/validate_html.py`。若出现 `P10-2B-L1-ROLE-RAIL-OVERLAP`、`P10-2B-L1-ROLE-NO-WRAP` 或 `P10-2B-L1-STAGE-GRID-MISMATCH`，说明 L1 总体旅程几何会错乱，必须回到 `05-report.json` 或 renderer 修复后重渲染。

### 2B 画像页重点色

- 模块标题胶囊、关键状态、选中态使用重点蓝 `#3296FF` 或 token `--color-primary-dark`。
- 不得使用过浅蓝作为重点色，避免与弱信息层混淆。
- 侧栏身份底色使用浅蓝底 `#DCF0FA` 或 token `--color-bg-canvas-left`。

### 2B 细节页疏密规则

- 细节页使用两列轻量卡片，组件行高随内容自适应；组件组在标题下方的剩余区域垂直居中，避免内容缩在左上角。
- 页面外边距小于模块间距与两侧内容宽度之和；卡片必须有稳定内边距、浅边框和明确边界。
- 模块内部只使用卡片宽度内的短实线分隔，不使用跨过大片空白的长虚线。
- 同义或高度重复的模块先在 05 中向用户说明合并方案。用户确认后合并为一个模块，保留所有独有信息。
- 四个模块优先排成稳定的 `2 × 2`；奇数模块按阅读顺序排列，最后一个核心模块可以占满整行。
- 内容不足时先在 05 向用户建议保留核心模块，并写清删除页面或模块的信息损失。用户确认前不得自动删除细节 tab。

## 2C 规范：画像与旅程

### 色板

| 色板 ID | 名称 | 色值 |
| --- | --- | --- |
| `2c-purple-default` | 紫色默认 | `#9664FF`,`#DCD2FF`,`#F0F0FA`,`#FA5A5A` |
| `2c-red-orange` | 红橙 | `#F05A28`,`#FFE6E6`,`#F0AA8C`,`#3C6E64` |
| `2c-green-gray` | 绿灰 | `#82B4B4`,`#96AA78`,`#D2D278`,`#F0F0DC` |
| `2c-yellow-orange` | 黄橙（TO C-3） | `#FFB41E`,`#F0E678`,`#FFE6D2`,`#E6F0F0` |
| `2c-blue-yellow` | 蓝黄（TO C-4，原 TO C-5 顺位前移） | `#5A8CFA`,`#B4C8FA`,`#F0DC0A`,`#FFF0BE` |
| `2c-cyan-gold` | 青金（TO C-5，原 TO C-6 顺位前移） | `#285A82`,`#32B4DC`,`#FFC846`,`#DCF0F0` |

### 2C 色板选择规则

- AI 工具、AI 决策、大模型、智能助手相关画像，优先使用 `2c-purple-default`。
- 多画像报告必须给每个画像分配可区分 accent，不得相邻同色。
- 多维分布图、矩阵图、图例、画像 tab、画像详情页要使用同一套画像 accent 映射。
- 警告和风险使用 `#FA5A5A` 或对应色板 alert 色，不用 2B 警告红。

### 2C 色卡语义层

2C 页面不得直接临时写 icon、标签、重点词颜色。先选画像 accent，再由 CSS token 派生：

| 语义 token | 用途 | 来源 |
| --- | --- | --- |
| `--color-toc-focus` | 当前画像重点色 | `--color-accent`，必须来自 2C 色板 primary/accent |
| `--color-toc-surface` | 身份卡、头像底、大面积色块 | 当前 2C 色板 bg/soft 色 |
| `--color-toc-icon` | icon、引用符号、重点词 | `--color-toc-focus` |
| `--color-toc-icon-bg` | icon/胶囊浅底 | `--color-toc-focus` 混白 |
| `--color-toc-focus-tint` | 选中卡片、弱强调底色 | `--color-toc-focus` 混白 |
| `--color-toc-on-focus` | 深色重点底上的文字 | `#FFFFFF` |

落地规则：

- `section-block-title` 作为 2C 信息卡标签，文字使用 `--color-text-primary`，背景使用 `--color-toc-soft`。
- `section-block` 左侧重点线、正文 strong、代表原话左线均使用 `--color-toc-focus`。
- 身份卡、头像底等大面积色块使用 `--color-toc-surface`，不能直接铺 `--color-toc-focus`。
- 浅底、阴影、代表原话底色由色卡语义 token 自动生成，不能写固定紫色或固定蓝色。
- 多画像报告中，每个画像 section 必须同时写入 `--color-accent` 与 `--color-toc-surface`，两者来自同一套 2C 色板。
- 弱模型只在 `05-report.json` 中选择白名单 `accent`。完整 palette pack 由 Python 渲染器从 `_visual-system.json` 注入，模型不得手写 CSS 变量。

### 模板 `2c-persona`

适用：toC 单画像或多画像中的画像主页。

固定结构：

1. 顶部或左侧：画像名称、关键词、头像、代表性一句话。
2. 中部：核心动机、典型场景、行为特征、需求触发点。
3. 右侧或底部：痛点、机会点、证据 hover。
4. 图片素材优先承载真实产品、场景、截图，不只做装饰。

推荐组件：

- `layout-2c-portrait`
- `identity_card`、`detail_headline`、`section_blocks_grid`、`mockup_list`、`persona_quote_pull`

### 模板 `2c-journey`

适用：toC 消费者旅程、使用路径、决策路径、体验情绪波动。

固定结构：

1. 顶部：旅程目标和用户状态。
2. 主体：阶段、行为、触点、情绪、阻塞、机会点。
3. 证据层：每个阶段必须绑定来源片段。
4. 情绪和阻塞可用高对比色强调，但不能压过内容可读性。

推荐组件：

- `layout-2c-journey`
- `journey_2c`、`detail_analysis`、`mockup_list`、`persona_quote_pull`

### 模板 `2c-complex-distribution-report`

适用：多画像、多维分布、画像详情和画像旅程同时存在的复杂 2C 报告。

固定结构：

1. 首页使用 `layout-distribution-multi` 展示总体分布。
2. 首页必须有图例、分布轴、画像节点、可追溯 evidence。
3. 每个画像至少包含一个 `layout-2c-portrait` 主画像页。
4. 需要产品或场景说明时，增加 `layout-2c-detail` 详情页。
5. 每个画像的旅程页使用 `layout-2c-journey`，正文不能整片复用。
6. 导航中画像页、详情页、旅程页必须成组，不让用户迷失当前画像。
7. 所有页面使用 `data-theme="2c"` 与 `data-density="low"`。

### 2C 字体与布局

- 2C 整体页面背景使用白色 `#FFFFFF`，包括 `--color-bg-page`、`--color-bg-canvas-left`、`--color-bg-canvas-right`。
- `#F0F0FA` 只作为柔和辅助底色、色板背景或局部信息块，不作为整页背景。
- 2C 主体字号使用低密度 token，信息块不追求高密度压缩。
- 画像标题可更大，但模块内标题不得使用 hero 级字号。
- 详情页截图、标签、注释要留出稳定尺寸，不能依赖图片自然尺寸撑开布局。
- 多维分布图节点、图例、线条必须沿用画像 accent，不能临时写新色。
- 多维分布图内所有文字最小字号为 `12px`。已有 13px、14px 等较大文字保持原尺寸，不统一压到 12px。
- 2C 旅程页所有文字最小字号为 `12px`。正文摘要和左侧维度标签使用固定 `12px`；关键词、触点标签和情绪标签都不能低于 `12px`；标题、阶段名等较大字号保持原尺寸。
- 2C 旅程阶段表头与左侧维度栏使用同一套当前画像浅色承载层 `--color-toc-surface`，文字使用 `--color-text-primary`。阶段编号使用 `--color-toc-primary`。禁止整行使用高饱和主色底。
- 旅程页每个阶段必须有差异化行为或证据，不能只换画像名。
- 情绪曲线为上下标签预留至少 `40px` 安全区。高位节点的标签放在点下方，低位节点的标签放在点上方，曲线、表情和文字均不得被页面边界或相邻单元格遮挡。
- “情绪”维度标签在左侧栏水平、垂直居中。

## 交付前校验清单

渲染后必须运行：

```bash
python scripts/validate_components_json.py --workdir <过程稿目录> 05-report.json
python scripts/validate_html.py --project-dir <项目目录> <最终输出目录>/report.html
```

以下视觉问题一律阻塞交付：

- 缺少 `_design-tokens.css` 或 `_components.css`。
- 2B/2D 旅程报告缺少 `2b-process-blue` 色值。
- L1/L2 阶段、子阶段、工具触点字号不符合规范。
- L2 阶段头出现旧样式白色遮挡三角。
- L2 工作流 SVG 外层出现细灰色整体边框。
- 2C 报告未使用 `data-density="low"`。
- 2C 多维分布报告缺图例、分布线、节点或 evidence。
- 2C 六套可选色板 token 缺失。

## 2C Palette Pack 规则补充

2C 多画像报告中，每个用户角色使用一套独立主色卡风格。色卡风格不是单个 `accent`，而是一组必须同时注入的视觉变量。

每个 `layout-2c-portrait`、`layout-2c-detail`、`layout-2c-journey` section 必须包含：

| Token | 用途 |
| --- | --- |
| `--color-accent` | 兼容旧组件的主色入口 |
| `--color-toc-style` | 当前角色色卡风格名 |
| `--color-toc-primary` | 主按钮、描边、重点词、标题强调 |
| `--color-toc-secondary` | 图表辅助、弱装饰、次级视觉信号 |
| `--color-toc-surface` | 身份卡、头像底、大面积色块 |
| `--color-toc-bg` | 表头、触点标签、浅承载区 |
| `--color-toc-soft` | 胶囊、小标签、轻强调底色 |
| `--color-toc-alert` | 痛点、风险、价格敏感等警示信息 |
| `--color-toc-aux` | 触点标签、工具标签、证据标签等辅助区隔色 |
| `--color-toc-aux-bg` | 触点标签、工具标签、证据标签的跳色底色，必须等于同色卡内的 `--color-toc-aux` |
| `--color-toc-aux-text` | 触点标签、工具标签、证据标签的文字色，默认 `--color-text-primary` |

可选色卡风格：

| 风格 | 主色 | 辅助色 | 大面积底色 | 警示/冲突色 |
| --- | --- | --- | --- | --- |
| `purple-default` | `#9664FF` | `#DCD2FF` | `#F0F0FA` | `#FA5A5A` |
| `red-orange` | `#F05A28` | `#F0AA8C` | `#FFE6E6` | `#3C6E64` |
| `green-gray` | `#82B4B4` | `#96AA78` | `#F0F0DC` | `#D2D278` |
| `yellow-orange` | `#FFB41E` | `#F0E678` | `#FFE6D2` | `#FFB41E` |
| `blue-yellow` | `#5A8CFA` | `#F0DC0A` | `#FFF0BE` | `#5A8CFA` |
| `cyan-gold` | `#32B4DC` | `#FFC846` | `#DCF0F0` | `#32B4DC` |

落地规则：

- 同一个用户角色的画像页、详情页、旅程页必须使用同一套 `palette pack`。
- 每张画像素材先绑定一套 TO C 色卡；该画像对应的画像页、详情页、旅程页只能从这套色卡取色。
- 不同用户角色优先使用不同 `--color-toc-style`，避免相邻角色视觉风格重复。
- 身份卡、头像底、大面积色块使用 `--color-toc-surface` 或 `--color-toc-bg`。
- icon、标题胶囊、重点词、描边使用 `--color-toc-primary`。
- 图表辅助线、装饰符号可使用 `--color-toc-secondary`。
- 痛点、风险、价格敏感、冲突信息使用当前色卡的 `--color-toc-alert`。浅底、标签和左边线都从同一 palette pack 的 alert 语义生成，禁止借用其他色卡或退回固定红色。
- 禁止只输出 `--color-accent` 后依赖 CSS 自动混白。渲染器必须从 `_visual-system.json` 注入完整 palette pack。
- 禁止跨色卡借色。例：`green-gray` 角色不能调用旧废弃色卡或 `--palette-2c-purple-*`。
## 2C Palette Pack 同色系执行规则

2C 多画像报告中，每个用户角色必须先选择一套 TO C 主色卡。选定后，该角色的画像页、详情页、旅程页必须统一使用同一套 `palette pack`，不得把紫色头像底、蓝色边框、黄色表头混在同一角色里。
画像素材本身也参与色卡绑定：一张画像素材对应一个 `--color-toc-style`，同一素材延展出的画像页、细节页和旅程页不得切换色卡或跨色卡取色。

同一角色的视觉元素映射如下：

| 元素 | 必须使用的 token |
| --- | --- |
| 头像底、身份卡底、大块引用底 | `--color-toc-surface` 或 `--color-toc-soft` |
| 旅程阶段表头底 | `--color-toc-surface`，文字使用 `--color-text-primary`，阶段编号使用 `--color-toc-primary` |
| icon、引用边框、卡片边框、强调句、重点词 | `--color-toc-primary` |
| 模块标题、小标题、旅程维度文字、旅程关键词文字 | `--color-text-primary`，色彩通过底色表达 |
| 胶囊标签、小标签、轻强调底色 | `--color-toc-soft` |
| 触点标签、工具标签、证据标签 | 使用同一色卡中的跳色 `--color-toc-aux`；底色 `--color-toc-aux-bg` 必须直接等于跳色，不能使用主色或主色浅底 |
| 图表辅助线、辅助装饰、次级视觉信号 | `--color-toc-secondary` |
| 痛点、风险、价格敏感、冲突信息 | `--color-toc-alert` |

示例：
- 角色选择紫色默认色卡时，引用块边框、引号 icon、强调句使用紫色主色；旅程阶段表头使用紫色浅底深色字，阶段编号使用紫色主色。
- 角色选择绿色色卡时，身份卡底、引用块底、旅程关键词底、旅程阶段表头都必须来自绿色色卡；旅程阶段表头使用绿色浅底深色字。
- 角色选择紫色默认色卡时，关键词胶囊使用紫色浅底黑字，触点标签使用同色板定义的米黄色辅助区隔色黑字，避免所有标签都变成紫色。
- 红橙、蓝黄、青金同理，各自只允许使用本色卡内的主色、浅底、辅助色和警示色。
- `TO C-4.png` 对应的旧 `high-contrast` 色卡已废弃，不得再作为新报告的可选色卡。旧 `TO C-5.png` 顺位前移为 TO C-4，旧 `TO C-6.png` 顺位前移为 TO C-5。

生成约束：
- `layout-2c-portrait`、`layout-2c-detail`、`layout-2c-journey` 的最终 HTML 必须由渲染器显式写入完整 `--color-toc-*` 变量。
- 同一 `persona.id` 的三类页面必须使用同一个 `--color-toc-style`。
- 同一 section 中出现的 `--palette-2c-*` 变量必须全部属于该 section 声明的 `--color-toc-style`。
- 校验时如果出现跨色系混用，如紫色角色中出现蓝色强调或黄色旅程表头，应阻塞交付。
## 2C 导航与身份卡同步规则

2C 多画像报告的顶部导航不允许使用全局固定紫色。点击任意画像、细节页或旅程页时，当前 active tab 必须从目标 section 读取同一套角色色板：

- active tab 背景和边框使用目标 section 的 `--color-toc-primary`。
- hover 底色使用目标 section 的 `--color-toc-soft`。
- `identity-card` 背景必须优先使用 `--color-toc-surface`，边框与阴影使用 `--color-toc-primary` 的弱化色。
- 引用符号、引用边框、卡片边框、正文强调句必须直接使用 `--color-toc-primary`，不要再走固定紫色或固定蓝色。
- `section-block-title`、旅程维度标签、旅程关键词标签的文字必须使用 `--color-text-primary`，只允许底色使用当前色卡。
- `.touchpoint-tag` 必须使用 `--color-toc-aux-bg` 与 `--color-toc-aux-text`，其中 `--color-toc-aux-bg` 要直接呈现色卡跳色，用于和主色关键词胶囊区分。
- 浏览器选中态或评论标注产生的蓝色描边不属于页面样式，不纳入视觉规范判断。

校验要求：

- 2C 报告中必须包含导航色板同步逻辑 `syncNavPalette`。
- `layout-2c-portrait` 出现时，CSS 中的 `.identity-card` 必须以 `--color-toc-surface` 为背景入口。
- 如果某个角色选择绿色色卡，它的身份卡、引用块、标题胶囊、强调词、旅程表头和导航 active tab 都必须呈现绿色系。
## 2026-07-08 2C Palette Pack Hard Rules

These rules are mandatory for weak-model execution and validator review.

1. One persona, one palette pack. A persona's portrait page, detail page, and journey page must all use the same `--color-toc-style`.
2. One image reference, one palette pack. If a persona visual is mapped to a TO C reference image or color card, every page derived from that persona must use only that card.
3. Cross-palette borrowing is forbidden. A `green-gray` persona must not use `--palette-2c-purple-*`; a `purple-default` persona must not use `--palette-2c-blue-yellow-*`, and so on.
4. Each 2C persona/detail/journey section must explicitly set the complete palette pack: `--color-accent`, `--color-toc-style`, `--color-toc-primary`, `--color-toc-secondary`, `--color-toc-surface`, `--color-toc-bg`, `--color-toc-soft`, `--color-toc-alert`, `--color-toc-aux`, `--color-toc-aux-bg`, and `--color-toc-aux-text`.
5. Header, border, icon, large quote mark, quote border, emphasis phrase, active nav, and major outline use `--color-toc-primary`.
6. Large soft backgrounds, identity cards, avatar panels, quote blocks, journey dimension cells, and table header light areas use `--color-toc-surface`, `--color-toc-bg`, or `--color-toc-soft`.
7. Touchpoint, tool, evidence, and auxiliary tags use the palette jump color: `--color-toc-aux-bg` and `--color-toc-aux-text`. They must not reuse the primary color capsule.
8. Journey stage headers and the left dimension rail use the current palette surface color with dark text. Stage numbers use the current palette primary color.
9. Pain or risk highlight blocks must be derived from the current persona palette. The block background may mix the current primary with white; the left border and pain tag use the current primary.
10. Minimum text size in 2C distribution and 2C journey pages is 12px. Existing larger labels remain larger; do not normalize everything down to 12px.
11. Deprecated palette: old `high-contrast` / old `TO C-4.png` is removed. Old TO C-5 becomes current TO C-4. Old TO C-6 becomes current TO C-5.
12. Validator expectation: `validate_html.py` must fail on incomplete palette packs, unknown palette names, cross-palette token mixing, primary-colored touchpoint tags, missing nav palette sync, and any text below the 12px floor in 2C journey/distribution templates.
