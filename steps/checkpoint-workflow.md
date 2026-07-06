# Checkpoint Workflow

本文件是弱模型稳定执行的流程门禁。任何执行用户画像 skill 的模型都必须先完成中间文件落盘,再进入下一步。

## 最高优先级原则

1. 每个关键节点必须成对输出 `.md` 和 `.json`。
2. `.md` 面向用户对齐,必须能让用户暂停并接手后续 Keynote、PPT 或其他模型可视化。
3. `.json` 面向系统续跑和脚本校验,必须结构化、可解析、可追踪。
4. 禁止跳过中间稿直接产出 `05-report.json` 或最终 HTML。
5. 当前步骤没有通过校验前,不得进入下一步。

## 检查点清单

| 阶段 | 必须输出的 MD | 必须输出的 JSON | 目的 |
| --- | --- | --- | --- |
| 00 研究目标 | `00-research-goal.md` | `00-research-goal.json` | 锚定读者、研究问题、决策用途 |
| 01 范式选择 | `01-paradigm.md` | `01-paradigm.json` | 选择 2B/2C、R1 到 R5 范式和处理路径 |
| 02 分类依据 | `02-classification.md` | `02-classification.json` | R3/R4/R5 必填,说明分类维度和边界 |
| 03 字段对齐 | `03-field-alignment.md` | `03-field-alignment.json` | 展示字段池、用户取舍、视觉规范选择 |
| 04 画像合并 | `04-personas.md` | `04-personas.json` | 固化画像数量、合并依据、证据映射 |
| 05 报告组件 | `05-report.md` | `05-report.json` | 固化报告结构、组件清单、视觉模板 |

## 每步执行顺序

1. 读取上一步 `.json`,确认状态为 `confirmed` 或 `validated`。
2. 生成本步骤 `.md`,用自然语言向用户展示判断、证据和待确认项。
3. 等待用户确认或根据用户反馈修订。
4. 生成本步骤 `.json`,保存用户确认摘要和机器可读字段。
5. 运行校验脚本,确认 MD/JSON 配对、schema、数量一致性通过。
6. 进入下一步。

## 给用户看的固定话术

每个对齐节点都应使用类似话术:

> 我先把这一步的中间结果落成 MD,方便你直接审阅或交给其他工具继续做视觉化。你确认后,我再生成对应 JSON 作为后续自动续跑和校验的依据。

## 禁止行为

- 禁止只输出 `05-report.json`。
- 禁止只在对话里口头确认,不写入 MD。
- 禁止只写 JSON,不提供用户可读 MD。
- 禁止字段池不展示就进入画像生成。
- 禁止未询问视觉素材、业务类型、模板和色板就生成 HTML。
- 禁止自创 layout 替代 `steps/visual-style-guide.md` 中的模板。

## 弱模型执行提示

当模型参数小于 100B 或遵循能力不稳定时,必须按以下简化命令执行:

1. 只做当前一个检查点。
2. 先复制对应 `templates/checkpoints/*.md` 模板,填完后停止给用户确认。
3. 用户确认后复制对应 `templates/checkpoints/*.json` 模板。
4. 运行 `scripts/validate_checkpoint_pairing.py`。
5. 不要合并多个阶段,不要提前生成最终报告。
