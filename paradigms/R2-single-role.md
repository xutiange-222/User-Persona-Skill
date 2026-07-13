# R2 单角色合并

## 使用条件

全部访谈属于同一种角色或同一类消费者，目标是合并成一个画像。toB、toD、toC 均可使用。

## 01 必须确认

在 `01-paradigm.md` 展示：

- 单角色判断依据
- 候选画像名称
- 纳入的匿名受访者 ID
- 可能不属于该角色的异常样本

用户确认后写 `01-paradigm.json`，设置 `paradigm: R2`、`status: confirmed` 和具体确认摘要。

## 02 必须落盘

R2 不做分群。`02-classification.md/json` 使用 `status: not_applicable`，原因写明“全部样本已确认为同一角色”。

## 后续执行

1. 读取 `schemas/schema-tob.md` 或 `schemas/schema-toc.md`，按 `steps/field-alignment.md` 完成 03。
2. 按 `steps/extract-merge.md` 对每份访谈独立抽取，再按字段 reduce。
3. 生成 `04-personas.md`，让用户确认画像名称、共性、差异和证据风险，再写 JSON。
4. 按 `steps/journey-alignment.md` 确认单画像旅程；无旅程也写 04 不适用文件。
5. 组装 05 并渲染。

## 质量门禁

- 合并结果不得把少数人的特征写成全体共性。
- 共性、分歧、单人观点分开表达，并保留提及人数和证据。
- 画像名称由用户确认后进入 04 和 05。
- 有效样本只剩 1 位时，暂停并让用户确认是否继续。
