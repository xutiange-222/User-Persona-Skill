# R4 二维矩阵

## 使用条件

研究需要两个关键区分点交叉定位用户。toB、toD、toC 均可使用。总览使用二维矩阵，画像子页仍按 research type 选择 2B 或 2C 组件族。

## 02 是本范式核心

使用 `assets/prompts/recommend-value-variables.md` 推荐两个区分点。每个区分点必须同时满足：

1. 样本覆盖充分
2. 受访者之间存在可解释差异
3. 与研究决策直接相关

## 固定确认顺序

在同一份 `02-classification.md` 中分四轮确认，每轮都可以修订 MD：

1. 确认两个区分点及横纵轴。
2. 确认两端档位名称和行为定义。档位名要表达可观察差异，避免只写高、低。
3. 确认每位匿名受访者的二维落点和原话证据。
4. 确认象限名称、画像名称、成员归属和空象限处理。

四轮都完成后写 `02-classification.json`。至少固化：

档位名确认闸门：这些词会进入最终报告。只有用户确认全部档位名后，才允许写入 `label_confirmed: true`。

```json
{
  "checkpoint": "02-classification",
  "status": "confirmed",
  "label_confirmed": true,
  "value_variables": [],
  "axes": {"x": "横轴变量 id", "y": "纵轴变量 id"},
  "respondent_mapping": {},
  "groups": [],
  "empty_groups": [],
  "confirmation_message_summary": "用户确认区分点、档位名、受访者落点和画像名称。"
}
```

## 命名要求

- toC 类型名保持短、直观，复杂判断放在副标题或正文。
- toB、toD 优先使用角色、任务或能力差异名称。
- 坐标轴档位名、象限名和画像名分别承担不同用途，不能用同一串抽象词覆盖三层。

## 后续执行

1. 完成 03，单独展示字段池并确认旅程范围。
2. 按象限分组独立抽取和 reduce。
3. 在 `04-personas.md/json` 固化画像及证据。
4. 在 `04-journeys.md/json` 确认每个画像旅程；无旅程也写不适用。
5. 05 使用 `layout-matrix-2d` 作为总览，子页按 research type 选组件族。

## 质量门禁

- 区分点改变后，受访者映射、象限和画像全部重新确认。
- 空象限如实展示为未覆盖，禁止补造用户。
- 单人象限保留样本量风险。
- 05 的矩阵点位、标签和画像成员必须与 02 一致。
