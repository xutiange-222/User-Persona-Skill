# 恢复路径与防卡机制

## 原则

每条阻断规则必须有明确恢复路径。系统只允许四类结果：

1. `passed`：进入下一步。
2. `recoverable`：运行一条官方恢复命令，再重试一次。
3. `user_review`：保留待确认状态，缩小范围重新向用户展示。
4. `stopped_repeated_failure`：停止自动修补，生成恢复交付件或报告 Skill 缺陷。

没有恢复路径的门禁属于 Skill 缺陷。模型不得反复试命令，也不得在过程目录编写临时脚本。

弱模型统一使用：

```powershell
python scripts/workflow.py --workdir <过程稿> check --target <当前节点> --auto-recover
```

该入口最多执行一次安全自动恢复和一次复检。需要用户判断、内容修复或 Skill 修复时，它会停止并给出恢复包路径。

## 约束分层

### 不可降级

- 隐私泄露。
- 虚构事实、伪造引文或跨画像证据。
- JSON 无法解析或核心 schema 损坏。
- 缺少用户确认、确认原话矛盾。

这些问题未解决时不能生成最终报告。仍可保留已经通过的上游文件；隐私错误存在时不能生成恢复交付件。

### 可自动恢复

- 04 中文 MD 出现机器字段、机器 ID 或英文枚举，且结构化 JSON 未发生内容分叉。
- 仅派生哈希、中文展示快照或默认头像映射缺失，正文与证据未变化。
- 过程目录出现一次性构建脚本。

04 MD 与结构化 JSON 的内容指纹失配时，可能存在用户手工修改。必须保留两版并重新打开对应 04 检查点，禁止自动覆盖。文件修改时间只用于寻找最新目录，不作为内容过期或回滚依据。

只使用 `scripts/workflow.py recover`。恢复动作必须保留原文件或把它们移入 `历史版本/`。

### 可降级交付

最终 HTML 因布局、组件或渲染环境连续三次失败时，运行：

```powershell
python scripts/workflow.py --workdir <过程稿> recover --action create-recovery-bundle
```

恢复包只包含 MD/JSON 哈希一致的检查点和未解决事项。它用于交给其他 AI、人工排版或后续续跑。恢复包不得冒充最终报告。

## 官方恢复动作

| 问题 | 恢复动作 |
|---|---|
| 04 人类稿只有展示语言错误，内容指纹一致 | `workflow.py recover --action refresh-04-md --stem 04-personas` 或 `04-journeys` |
| 04 MD 与 JSON 内容指纹分叉 | `workflow.py recover --action reopen-04 --stem 04-personas` 或 `04-journeys`；保留两版并重新对齐确认 |
| 04 标题被省略号截断、旅程阶段 ID 重复，需改结构化内容 | `workflow.py recover --action reopen-04 --stem 04-personas` 或 `04-journeys`；旧版与下游自动归档，修复草稿后重新对齐确认 |
| 过程目录存在临时脚本 | `workflow.py recover --action quarantine-builders` |
| 用户确认后又修改了上游结构化正文 | 重新打开对应 04 检查点；旧版与下游一并归档后重新确认 |
| HTML 连续失败或当前模型无法继续 | `workflow.py recover --action create-recovery-bundle` |

## 重试预算

- 自动恢复命令执行后只重试一次当前门禁。
- 同一错误连续三次出现，停止。
- 当前节点错误总数连续三次没有下降，停止。
- 错误数量持续下降视为有效进展，不消耗停止预算。
- 不同错误轮流出现且错误总数不下降，计入无进展次数。

停止后必须输出：已完成检查点、当前阻断错误、已尝试的官方恢复动作、恢复包路径和需要用户处理的事项。
