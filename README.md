# User Persona Skill

把访谈、观察记录和研究资料转成可追溯的用户画像与用户旅程。工程目标是让参数量较小、长程规划能力较弱的模型，也能依靠检查点、schema 和脚本门禁稳定完成任务。

[打开人类用户说明书](./人类用户说明书.html)

## 五条运行原则

1. 每个关键节点先写完整 MD；用户用节点专属确认语确认后再写同名 JSON。修改消息和“继续”不能代替确认。
2. 固定生成 7 对检查点，共 14 个文件。缺少任意一份都不能渲染。
3. 模型只生成结构化 JSON，Python 负责校验、恢复和 HTML 渲染。
4. 按内容哈希去重。报告中的“访谈数”只指独立主访谈，补充材料和多画像分配单独计数。
5. 归并真值保留完整内容；04 用 `field_decisions` 明示展示取舍和信息损失，05 通过 `content_ref` 引用；旅程逐元素绑定证据。

## 检查点

| 节点 | MD 与用户对齐 | JSON 供系统续跑 |
|---|---|---|
| 00 | 研究目标 | 研究类型、范围、输入资料数量 |
| 01 | 范式选择 | R1 至 R5 路由 |
| 02 | 分类确认 | 分类依据、命名、成员映射，或不适用 |
| 03 | 字段对齐 | 字段、素材、旅程范围、视觉规格 |
| 04 | 画像确认 | 画像内容、证据、样本风险、字段展示取舍与信息损失 |
| 04 | 旅程确认 | 阶段、节点、触点、痛点、证据缺口，或不适用 |
| 05 | 报告确认 | 页面、组件、字段覆盖、palette pack、交付范围 |

标准目录：

```text
用户画像报告输出/
└── <项目名>-<时间>/
    ├── 过程稿/
    │   ├── 00-research-goal.md
    │   ├── 00-research-goal.json
    │   ├── 01-paradigm.md
    │   ├── 01-paradigm.json
    │   ├── 02-classification.md
    │   ├── 02-classification.json
    │   ├── 03-field-alignment.md
    │   ├── 03-field-alignment.json
    │   ├── 04-personas.md
    │   ├── 04-personas.json
    │   ├── 04-journeys.md
    │   ├── 04-journeys.json
    │   ├── 05-report.md
    │   ├── 05-report.json
    │   ├── source-manifest.json
    │   ├── terminology-glossary.json  # 有术语审计表时
    │   ├── processed/
    │   ├── extracted/
    │   └── reduced/
    ├── 画像头像素材/
    ├── 界面截图/
    └── 最终交付件-.../
        ├── report.html
        ├── _design-tokens.css
        ├── _components.css
        └── assets/
```

## 快速使用

1. 把访谈或研究资料放入一个清晰的项目目录。
2. 调用 skill，并给出研究目标、受众和期望输出。
3. 审核来源清单中的主访谈、补充材料、画像分配和三类计数。
4. 依次确认 00、01、02、03、04 画像、04 旅程和 05 的 MD。
5. 让系统运行渲染命令并打开最终 `report.html`。

初始化过程稿目录：

```powershell
python scripts/init_run_dir.py --base-dir <输出父目录> --project-name <项目名>
```

恢复检查：

```powershell
python scripts/recovery_check.py --workdir <项目目录>\过程稿
```

唯一渲染入口：

```powershell
python scripts/components/render_report.py --input <项目目录>\过程稿\05-report.json --output <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
```

完整质量检查：

```powershell
python scripts/tests/skill_audit.py
python -m pytest scripts/tests scripts/components/tests -q
```

## 目录职责

| 路径 | 职责 |
|---|---|
| `SKILL.md` | 弱模型第一入口、强制流程和停止条件 |
| `steps/` | 每个节点的执行方法、视觉规则和恢复规则 |
| `paradigms/` | R1 至 R5 的分支流程 |
| `templates/checkpoints/` | 7 对检查点模板和交接清单 |
| `assets/prompts/` | 单份抽取、字段归并、分类推荐提示词 |
| `assets/templates/` | HTML 骨架、设计系统、CSS token 和组件样式 |
| `assets/default-avatars/` | 用户没有提供头像时可用的默认头像 |
| `schemas/` | 研究类型和业务字段说明 |
| `scripts/components/schemas/` | 报告和组件的机器校验 schema |
| `scripts/` | 预处理、抽取、归并、隐私、恢复、校验和渲染 |
| `docs/reference/reports/` | 人类可浏览的五份视觉参考报告 |

根目录的 `.gitignore` 用于排除测试缓存和本地报告输出；`.nojekyll` 是 GitHub Pages 的空标记，用于确保以下划线开头的样式文件能够正常发布。两者都属于仓库配置，不参与 Skill 执行。

`source-manifest.json` 是来源和样本计数的机器真值。`primary` 参与主访谈频次，`supplemental` 只补指定字段。术语审计 Markdown 编译为 `terminology-glossary.json`，不计入访谈数。

## 视觉系统

设计系统分为四层：基础属性、语义 token、主题 palette pack、组件契约。

- 人类规则：`steps/visual-style-guide.md`
- 机器真值：`assets/templates/_visual-system.json`
- CSS token：`assets/templates/_design-tokens.css`
- 组件实现：`assets/templates/_components.css`

2B 的 L1 总体旅程与 L2 单角色旅程共用阶段、子阶段、角色列、节点和连线语义。2C 每个画像绑定一套 palette pack，画像页、详情页、旅程页和分布图保持同一映射。跨色卡借色、2C 旅程高饱和整行表头、2C 分布图或旅程文字小于 12px 都会被 HTML 校验器拦截。

## 参考报告

- [2B 单画像](./docs/reference/reports/A-单画像/2B-保障型运维工程师/report.html)
- [2C 单画像](./docs/reference/reports/A-单画像/2C-内行场景派/report.html)
- [2B 多角色与总体旅程](./docs/reference/reports/B-多角色/2B-DevOps五角色/report.html)
- [2C 二维矩阵](./docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html)
- [2C 多维分布](./docs/reference/reports/E-多维分布/2C-HiRes-多区分点/report.html)

刷新参考报告：

```powershell
python scripts/tools/refresh_reference_reports.py
```

## 业务规则变更边界

分类方法、字段定义、合并阈值、证据权重和画像内容 schema 会影响研究结论。修改这些内容前需要研究负责人确认。检查点门禁、路径、渲染、视觉约束、隐私和测试属于工程契约，可通过测试驱动持续加固。
