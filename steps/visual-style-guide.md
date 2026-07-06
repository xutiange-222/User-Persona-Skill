# Visual Style Guide

本文件把视觉规范拆成通用、2B、2C 三层。弱模型必须先选规范、模板和色板,再填内容。

## 最高优先级原则

1. 报告组件 JSON 只能选择本文件列出的模板、色板和组件填充规则。
2. 2B 默认强调流程、阶段、职责、协同和风险信号。
3. 2C 默认强调画像个性、生活方式、动机、场景和情绪节奏。
4. 不得自创 layout、色板名称、组件类型或视觉结构。
5. `03-field-alignment.json` 必须写入 `visual_spec`,`05-report.json.metadata.visual_spec` 必须与之保持一致。

## 通用规范

- 页面采用 V9 组件化渲染体系,由 `scripts/components/render_report.py` 输出 HTML。
- 组件数量、layout、props 必须通过 `scripts/validate_components_json.py` 和 `scripts/components/schemas/report.json`。
- 颜色只从本文件色板选择。需要微调时,只能在 CSS token 层做轻量校准。
- 视觉素材必须先问用户,记录在 `visual_assets`。
- 输出前必须确认模板、色板、组件数量、旅程页范围。

## 2B 规范:流程与旅程

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

适用:toB/toD 多角色、同组织协作、需要呈现整体流程。

固定结构:

1. 顶部:研究目标与总体流程一句话。
2. 主体:横向阶段流,每个阶段包含角色、任务、关键系统、交接物。
3. 风险层:用警告红标注阻塞点、返工点、责任不清点。
4. 完成层:用完成绿标注顺畅节点和价值兑现点。
5. 侧栏或底部:证据摘要与可追溯 hover。

推荐组件:
- L1 全局页:`layout-2b-journey` + `tob_journey_l1`
- 单角色页:`layout-2b-journey` + `tob_journey_l2`
- 补充组件:`collab_flow`,`scenario_grid`,`painpoint_list`,`generic_kv`

## 2C 规范:画像与旅程

### 色板

| 色板 ID | 名称 | 色值 |
| --- | --- | --- |
| `2c-purple-default` | 紫色默认 | `#9664FF`,`#DCD2FF`,`#F0F0FA`,`#FA5A5A` |
| `2c-red-orange` | 红橙 | `#F05A28`,`#FFE6E6`,`#F0AA8C`,`#3C6E64` |
| `2c-green-gray` | 绿灰 | `#82B4B4`,`#96AA78`,`#D2D278`,`#F0F0DC` |
| `2c-yellow-orange` | 黄橙 | `#FFB41E`,`#F0E678`,`#FFE6D2`,`#E6F0F0` |
| `2c-high-contrast` | 高对比 | `#6E46E6`,`#FABE32`,`#FF6446`,`#E6E6D2` |
| `2c-blue-yellow` | 蓝黄 | `#5A8CFA`,`#B4C8FA`,`#F0DC0A`,`#FFF0BE` |
| `2c-cyan-gold` | 青金 | `#285A82`,`#32B4DC`,`#FFC846`,`#DCF0F0` |

### 模板 `2c-persona`

适用:toC 单画像或多画像中的画像主页。

固定结构:

1. 左侧或顶部:画像名称、关键词、头像、代表性一句话。
2. 中部:核心动机、典型场景、行为特征、需求触发点。
3. 右侧或底部:痛点、机会点、证据 hover。
4. 图片素材优先承载真实产品、场景、截图,不得只做装饰。

推荐组件:
- `layout-2c-portrait`
- `identity_card`,`detail_headline`,`section_blocks_grid`,`mockup_list`,`persona_quote_pull`

### 模板 `2c-journey`

适用:toC 消费者旅程、使用路径、决策路径、体验情绪波动。

固定结构:

1. 顶部:旅程目标和用户状态。
2. 主体:阶段、行为、触点、情绪、阻塞、机会点。
3. 证据层:每个阶段必须绑定来源片段。
4. 情绪和阻塞允许用高对比色强调,但不得压过内容可读性。

推荐组件:
- `layout-2c-journey`
- `journey_2c`,`detail_analysis`,`mockup_list`,`persona_quote_pull`
