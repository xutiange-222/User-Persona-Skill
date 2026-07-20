# 检查点清单

每个关键节点都必须同时存在同名 MD 和 JSON。MD 用于与用户对齐，JSON 用于校验、恢复和续跑。缺少任意一份都不能进入下一步。

目录创建后,第一条用户可见消息必须明确写出项目工作目录和过程稿目录；00 的 MD/JSON 必须保存相同的绝对路径。

下表中的确认短语只用于检查当前节点是否已经完成。当前节点 MD 未生成并交付给用户时，禁止在对话中要求用户回复该短语；禁止提前介绍后续节点的确认方式。

| 节点 | 用户确认稿 | 机器状态 | 完成条件 |
|---|---|---|---|
| 00 | `00-research-goal.md` | `00-research-goal.json` | 完整 value 已展示；用户回复“确认研究目标”；封存脚本通过 |
| 01 | `01-paradigm.md` | `01-paradigm.json` | 完整 value 已展示；用户回复“确认画像方式”；封存脚本通过 |
| 02 | `02-classification.md` | `02-classification.json` | 完整分类与映射已展示，或明确不适用；用户回复“确认分类内容”；封存脚本通过 |
| 03 | `03-field-alignment.md` | `03-field-alignment.json` | 字段、模块、素材、旅程和视觉均已展示；用户回复“确认字段与视觉范围”；封存脚本通过 |
| 04 | `04-personas.md` | `04-personas.json` | `04-personas.draft.json` 经官方脚本生成中文 MD；字段名无机器英文；用户单独回复“确认画像内容”；封存脚本通过 |
| 04 | `04-journeys.md` | `04-journeys.json` | `04-journeys.draft.json` 经官方脚本生成分层中文 MD；复杂 2B/2D 四轮分别展示、分别记录用户原话和内容指纹，第四轮后直接封存；简单旅程单次确认；或明确记录不适用 |
| 05 | `05-report.md` | `05-report.json` | 相对 03/04 新增的页数、详情页、内容分配和信息损失已确认；既有选择不重复确认 |

辅助机器真值：`source-manifest.json` 负责内容去重、证据层级和样本计数；输入含术语审计表时，`terminology-glossary.json` 负责术语规范。两者不替代 00 到 05 的 MD/JSON 配对。

## 恢复前检查

1. 运行 `python scripts/recovery_check.py --workdir <过程稿目录>`。
2. 修复报告中的第一项错误。
3. 同时更新对应节点的 MD 和 JSON。
4. 再次运行检查，直到可以安全续跑。

## 必须拦截的异常

- 缺 MD 或缺 JSON
- 只存在 `05-report.json`
- `processed/`、`extracted/` 和输入清单数量不一致
- 已有 `04-personas.json`，但 `reduced/` 中没有逐字段归并产物
- 检查点状态、用户确认状态或关键字段不一致
- 任一节点的 MD 仍为待确认或草稿，JSON 却标为 confirmed
- 任一节点的 MD 只列字段名、名称或摘要，没有覆盖用户需要确认的正文
- 04 MD 直接暴露阶段 ID、泳道 ID、节点 ID、组件类型、英文枚举或蛇形字段名
- 用户回复含“不确认”“看不懂”“看得头晕”“直接继续”，JSON 却记录为已确认
- 把“继续”“开始渲染”等推进指令或同一轮修改消息记录为节点确认
- 只有 `04-personas.json`，缺少逐份处理和抽取产物
- 05 存在旅程组件，缺少内容一致的 `04-journeys.md/json`
- 05 缺少 `visual_spec`，组件 schema 未通过，或 HTML 合规检查失败
- 缺 `source-manifest.json`，来源哈希重复，补充材料未声明补充字段，或三类计数不一致
- 05 画像页、细节页没有通过 `content_ref` 复用 04 的 `display_components`
- 03 已确认字段在 04/05 中被静默压缩或省略，缺少 `field_decisions`、字段覆盖记录或信息损失确认
- 旅程阶段、节点、连线、痛点卡、2C 单元格或情绪缺少证据绑定
- 已声明术语审计 reference，却缺 `terminology-glossary.json`，或确认稿仍含已知错误术语
- 技术词在 04/05 中被截断，或未出现在材料、用户上下文和术语表中

## 交付前命令

```powershell
python scripts/validate_checkpoint_pairing.py --workdir <过程稿目录> --require-complete
python scripts/validate_journey_checkpoint.py --workdir <过程稿目录>
python scripts/components/render_report.py --input <项目目录>\过程稿\05-report.json --output <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
python scripts/validate_html.py <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
```
