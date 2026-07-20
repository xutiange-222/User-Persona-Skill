# 用户旅程对齐

## 目录

1. 进入条件
2. 固定流程
3. 2B 与 2D
4. 2C
5. 不生成旅程
6. 与 05 报告的关系

## 进入条件

- `03-field-alignment.json` 已确认旅程开关和范围。
- `04-personas.json` 已固化画像、成员和证据映射。
- `source-manifest.json` 已审核；存在术语审计表时 `terminology-glossary.json` 已生成。
- 先复制 `templates/checkpoints/04-journeys.draft.json` 并填入结构化旅程，再运行官方脚本生成 `04-journeys.md`。完成后停止等待用户。

## 固定流程

0. 把 03 的旅程开关和 L1/L2 选择仅作为生成范围。不得复用用户在 03 的回答确认 04 内容。
1. 使用 `assets/prompts/build_journeys.txt` 从 04 画像和证据生成 `04-journeys.draft.json`。
2. 运行 `python scripts/workflow.py --workdir <过程稿> prepare-04 --stem 04-journeys`。禁止手写、拼接或局部修补 04 旅程 MD。
3. 复杂 2B/2D 的 MD 每轮只展示当前层：全局地图、角色责任、单角色旅程、分支与证据。上一轮正文不重复，只在进度表保留确认状态和用户原话；第四轮结束后生成完整交接稿。2C 固定使用“阶段 × 内容维度”表。可见正文使用中文名称，不展示阶段 ID、泳道 ID、节点 ID、组件类型和英文枚举。
4. 用户修改时更新草稿 JSON，再重新生成 MD。禁止只改 MD。
5. 用户说看不懂、看得头晕、不确认或要求直接继续时，保持待确认。先把当前问题拆成全局阶段、角色责任、单角色细节三个小块重新说明，禁止进入 05。
6. `04-journeys.md` 显示“分轮确认进度”时，一次只讨论当前轮。按顺序运行 `workflow.py journey-review --round global_map|role_responsibility|individual_journeys|branches_evidence --user-message <用户本轮原话>`。每次运行都是原子动作：用户原话和本轮内容指纹必须先写入 `04-journeys.draft.json`，随后刷新同一份 MD；禁止只在对话中记住确认结果。
7. 前三轮运行后只交付新生成的当前轮 MD。第四轮运行后，MD 自动成为包含全部正文和四轮确认记录的完整交接稿。四条逐项确认共同构成 04 内容确认，禁止再请求“确认旅程内容”。
8. 四轮完成后直接运行 `workflow.py seal --stem 04-journeys`。简单 2C 和小型旅程仍需用户明确回复“确认旅程内容”，再把该原话传给 `seal`。封存脚本校验分轮记录、每轮内容指纹和完整 MD，并把草稿固化为 `04-journeys.json`。
9. `journeys[].props` 必须符合既有组件 schema，`evidence_bindings` 必须覆盖全部阶段、节点、连线、痛点卡或 2C 单元格和情绪。
10. 封存会自动记录结构化内容数量、JSON 哈希和中文 MD 哈希。随后运行 `workflow.py check --target 04-journeys --auto-recover`。指纹不一致、中文全局导航缺失、机器 ID 外露、分轮未完成或确认原话含矛盾语义时必须进入对应恢复路径。

## 2B 与 2D

- 整体 L1 使用 `tob_journey_l1`，单角色 L2 使用 `tob_journey_l2`。
- 以上组件名只写入 JSON。用户看到“整体旅程”和“单角色旅程”。
- L1 先完成组织同构判断。共享任务、阶段和交付目标不足时，不生成强拼接的整体旅程。
- 决策节点写成可回答的问题，并明确是、否分支。
- 每个节点落在已确认的阶段和泳道中，连线不能引用不存在的节点。
- 工具、触点和关注点来自访谈证据或用户确认，不补写常识性步骤。
- 阶段名使用完整活动短语。整体阶段链先说明每个阶段目标、参与角色和关键交付，再展开局部节点。只有补充材料支撑的节点列入证据缺口，不能直接进入核心旅程。

## 2C

- 使用 `journey_2c`。
- 先确认 4 到 6 个阶段，再填思考、行为、痛点、触点和情绪。
- `cells` 外层按维度组织，内层按阶段组织。
- 每个关键单元优先绑定匿名原话。缺证据时在 `quality_review.evidence_gaps` 记录，并让用户确认。
- 同一画像的旅程与画像页、细节页共用色卡。颜色不写入旅程内容 JSON，由 renderer 注入。

## 不生成旅程

即使用户不需要旅程，也必须生成这对文件：

- MD 说明不生成的原因和用户选择。
- JSON 使用 `status: not_applicable`、`scope: none`、空 `journeys` 和具体原因。

## 与 05 报告的关系

`05-report.json` 中所有 `tob_journey_l1`、`tob_journey_l2`、`journey_2c` 组件必须逐项复制自 `04-journeys.json`。允许 05 调整页面编排，禁止修改已经确认的旅程内容。校验脚本会阻止遗漏、新增或改写。
