# R1 已分组

## 使用条件

访谈已经按角色、用户类型或用户确认的分组整理在文件夹或文件名中。toB、toD、toC 均可使用。

## 本范式只解决什么

确认现有分组及其中文名称。后续字段、抽取、画像、旅程和渲染走共享流程。

## 01 必须确认

在 `01-paradigm.md` 展示：

- 每个分组的候选名称
- 每个分组包含的匿名受访者 ID
- 分组依据来自文件夹、文件名或用户说明
- 未能识别归属的文件
- 样本量风险

用户确认后写 `01-paradigm.json`：

```json
{
  "checkpoint": "01-paradigm",
  "status": "confirmed",
  "paradigm": "R1",
  "research_type": "toB",
  "known_groups": [
    {"id": "persona-1", "name": "运维工程师", "members": ["P00000001", "P00000002"], "basis": "沿用用户确认的运维分组"},
    {"id": "persona-2", "name": "开发工程师", "members": ["P00000003", "P00000004"], "basis": "沿用用户确认的开发分组"}
  ],
  "confirmation_message_summary": "用户确认两个现有分组及其中文名称。"
}
```

## 02 必须落盘

R1 不重新发明分类依据。`02-classification.md/json` 仍必须存在，JSON 使用 `status: not_applicable`，原因写明“沿用用户已确认的输入分组”。

## 后续执行

1. 按 `steps/field-alignment.md` 完成 03。
2. 按 `steps/extract-merge.md` 对每份访谈独立抽取，并在各分组内独立 reduce。
3. 生成并确认 `04-personas.md/json`。
4. 按 `steps/journey-alignment.md` 确认 `04-journeys.md/json`；无旅程也写不适用。
5. 按 `steps/render-persona-page.md` 组装 05，再运行完整门禁。

## 质量门禁

- 每位匿名受访者只能属于一个分组，除非用户明确允许多重归属。
- 分组名称必须由用户确认，模型不得根据文件名直接写进最终报告。
- 单人分组可以保留，同时在 04 记录样本量风险。
- 多角色 toB/toD 的整体旅程先做组织同构判断。
