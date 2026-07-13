# 画像报告渲染

模型只负责填写 `05-report.draft.json`。用户确认页面编排后，封存脚本生成 `05-report.json`；`render_report.py` 负责检查点门禁、schema、布局、导航、色板、素材复制和 HTML 校验。

## 前置条件

以下条件必须全部满足：

- 00 至 05 的 7 对 MD/JSON 已存在。
- `04-personas.json` 已通过内容校验。
- `04-journeys.json` 已确认，或明确记录 `not_applicable`。
- `03-field-alignment.json.visual_spec` 与 05 的视觉规格一致。
- `processed/`、`extracted/` 和输入清单数量一致。
- 用户承诺补充的头像或截图已经复检。

## 数据流

```text
04-personas.json + 04-journeys.json
                 ↓
       05-report.draft.json
                 ↓
   prepare-05 → 05-report.md 用户确认
                 ↓
        seal → 05-report.json
                 ↓
     render_report.py 全部门禁
                 ↓
             report.html
```

05 中的旅程组件必须逐项复制自 `04-journeys.json`。页面顺序可以调整，已经确认的阶段、节点、触点、痛点、情绪和证据不能改写。

## 模型只做五件事

1. 从八个合法 layout 中选择页面结构。
2. 从注册表中选择 layout 允许的 component。
3. 按 component schema 填写 props。
4. 先把完整组件结构写入 `05-report.draft.json`，运行 `workflow.py prepare-05` 生成增量式 `05-report.md`。MD 只要求用户判断相对 03/04 新增的页数、详情页、模块分配和信息损失；模板、色板、旅程开关及画像与旅程正文标为沿用，不重复确认。
5. 用户确认最终页面编排后运行 `workflow.py seal --stem 05-report`，由脚本封存为 `05-report.json`。确认前禁止生成最终文件。

`prepare-05` 会先执行 `preflight_render.py`，一次检查全部上游和报告草稿。任何数据与内容阻断都在用户看到 05 确认短语之前解决。真实 HTML 生成后才能判断的几何错误仍在渲染阶段检查；失败时渲染器保留带问题说明的“预览-待修复”目录，已有有效交付件不被覆盖。

自动分页后若细节页仅剩一个组件,停止渲染。先在 `05-report.md` 展示建议保留的核心模块、建议删除或合并的模块及信息损失,获得用户明确确认后再更新 05 JSON。渲染器不得静默删除组件。

`05-report.md` 必须列出最终页面清单和页数。`05-report.json.metadata.page_count` 必须与 assembler 实际产生的页面数一致；自动分页产生额外页面也要回到 05 重新对齐。

精确契约：

- layout 白名单：`scripts/components/layouts/layout_rules.py`
- component 白名单：`scripts/components/REGISTRY.md`
- props schema：`scripts/components/schemas/`
- 总报告 schema：`scripts/components/schemas/report.json`
- 视觉路由：`steps/visual-system.md`
- 视觉规则：`steps/visual-style-guide.md`

模型不得写导航 HTML、CSS、SVG 坐标、tooltip 脚本或页面骨架。

## 内容质量门禁

### 证据三向一致

- `mention_count` 等于 `mentioned_by` 长度。
- `mention_count` 等于 `evidence_quotes` 长度。
- 每位受访者在同一归并项中最多计数一次。
- 原话和 source 必须能回到 extracted 文件。

### 多画像旅程独立

- 每个画像有自己的旅程组件 props。
- 阶段名称可以共用，行为、触点、痛点、机会点和情绪要体现画像差异。
- 2C `cells` 外层对应 dimensions，内层对应 stages。
- 任何两个画像的旅程正文高度相似时，回到 04 旅程检查点重做。

### 2B L1 协同语义

- L1 只用于同一组织或产品流程中的多角色协作。
- 跨角色交接使用跨 lane edge 表达。
- 判断、文档和异步信号只在证据支持时出现。
- 完全独立的角色只生成各自 L2。

### 隐私

- 展示名使用脱敏身份、姓氏加身份或稳定匿名代号。
- 真实姓名、电话、邮箱、账号和未授权组织信息不得进入 05 或 HTML。
- 渲染前后都运行 `privacy_guard.py`。

## R4 与 R5 总览规则

| 范式 | 总览 layout | 总览 component | 子页 |
|---|---|---|---|
| R4 | `layout-matrix-2d` | `matrix_guidance_strip`、`matrix_2d` | 按研究类型选择 2B/2D 或 2C |
| R5 | `layout-distribution-multi` | `distribution_multi` | 按研究类型选择 2B/2D 或 2C |

总览只承载分类结构。画像正文和旅程进入各自子页。空象限和样本不足需要如实展示。

## 2C 色卡检查

- 每个画像选择一个白名单 accent。
- Python 根据 accent 注入完整 palette pack。
- 同一画像的画像页、详情页和旅程页使用相同 accent。
- 分布图、矩阵、图例和导航使用同一画像映射。
- 触点、工具和证据标签使用当前色卡辅助色。
- 旅程阶段表头使用浅色承载层。
- 2C 旅程和多维分布的所有可读文字不小于 12px。

## 素材复检

1. 扫描项目的 `画像头像素材/` 和 `界面截图/`。
2. 对照 `03-field-alignment.json.visual_assets`。
3. 新素材没有映射时，列出文件名让用户确认。
4. 用户没有提供头像且接受默认头像时，从 `assets/default-avatars/` 选择。
5. 交付件中只引用已经复制到交付目录的相对路径。

## 渲染命令

```powershell
python scripts/components/render_report.py --input <项目目录>\过程稿\05-report.json --output <项目目录>\最终交付件-<标识>\report.html --project-dir <项目目录>
```

脚本会依次检查：

1. 7 对检查点完整且字段一致。
2. 旅程检查点与 05 完全一致。
3. 05 总 schema 和每个 component schema。
4. layout 与 component 组合合法。
5. `visual_spec`、2B 旅程和 2C palette pack 契约。
6. HTML 导航、隐私、证据、字号、颜色和资源路径。

公开渲染命令没有跳过校验参数。调试 renderer 时使用单元测试和临时目录，禁止生成绕过门禁的交付件。

## 失败处理

| 错误类型 | 返回位置 |
|---|---|
| 缺检查点、数量不一致 | 对应缺失节点或单份处理 |
| 字段太多、页面溢出 | 03 字段对齐 |
| 画像内容或证据错误 | 04 画像确认 |
| 旅程差异、阶段或证据错误 | 04 旅程确认 |
| layout、component、palette 错误 | 05 报告确认 |
| renderer 或 CSS 契约漂移 | 修复代码并跑全量测试 |

模型不能自行删除已确认字段。需要删减字段或拆页时，先向用户说明影响并等待选择。

## 交付目录

```text
最终交付件-<对象类型>-<项目名>-<样本数>用户-<构建方式>/
├── report.html
├── _design-tokens.css
├── _components.css
├── assets/
└── 交付件说明.md
```

交付件必须整包复制后仍能打开，禁止引用过程稿、本机绝对路径或工作目录外资源。
