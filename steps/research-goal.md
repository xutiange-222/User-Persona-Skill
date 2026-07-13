# 00 研究目标对齐

## 先锁定六项

在分类、字段、旅程和视觉选择之前，先与用户确认：

1. 报告的主要读者。
2. 本次要回答的核心研究问题。
3. 报告将支持哪项真实决策。
4. 研究对象类型：`toB`、`toC` 或 `toD`。
5. 纳入分析的原始资料数量。
6. 时间、样本、保密、交付形式等已知约束。

研究目标未确认时，只写 `00-research-goal.md`，不要提前选择范式或生成 JSON。

## MD 对齐稿

复制 `templates/checkpoints/00-research-goal.md`，用具体语言填写六项内容。避免“了解用户需求”“支持产品优化”等无法检验的表述。

推荐写法：

- 读者：负责 Hi-Res 会员体验的产品经理和设计师。
- 研究问题：不同付费动机用户在发现、试听、开通和续费阶段分别遇到什么阻力。
- 决策用途：决定下一版本的试听入口、会员权益说明和续费提醒优先级。

向用户展示完整 MD，并等待明确确认或修改。

## JSON 系统稿

用户确认后，复制 `templates/checkpoints/00-research-goal.json` 并填写：

```json
{
  "checkpoint": "00-research-goal",
  "status": "confirmed",
  "audience": "负责 Hi-Res 会员体验的产品经理和设计师",
  "research_question": "不同付费动机用户在关键阶段分别遇到什么阻力",
  "decision_use": "决定试听入口、权益说明和续费提醒优先级",
  "research_type": "toC",
  "source_count": 12,
  "constraints": ["不展示受访者真实姓名"],
  "confirmation_message_summary": "用户确认报告用于下一版本会员体验功能优先级决策"
}
```

`source_count` 在预处理前是预计输入范围；生成 `source-manifest.json` 后，必须更新为去重后的 `unique_primary_interviews`。补充材料和同一材料的多画像分配不计入该字段。

`research_type` 只使用以下机器值：

| 人类表述 | JSON 值 | 报告 theme |
|---|---|---|
| 2B | `toB` | `2b` |
| 2C | `toC` | `2c` |
| 2D | `toD` | `2d` |

## 变更处理

研究目标、研究类型、输入范围或决策用途发生变化时：

1. 更新 `00-research-goal.md` 并重新获得确认。
2. 重写 `00-research-goal.json`。
3. 删除或标记 01 至 05 为过期。
4. 从 01 开始重新执行受影响节点。

不要保留新旧研究目标混合生成的下游文件。
