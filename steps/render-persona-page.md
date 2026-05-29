# 公共步骤:画像页渲染(P8 组件化,2026-05-25 起)

> **P8 升级**:LLM 不再直接产 HTML 字符串。本文档定义的产品规则**仍然适用**,但渲染由 `python scripts/components/render_report.py` 自动完成,LLM 只产 `05-report.json`。
>
> 旧 P7 路径(LLM 手写 HTML)详见末尾「30 天兼容说明」段,2026-06-25 起删除。

---

## 0. 渲染流程一句话

```
04-personas.json → LLM 决策 layout+components → 05-report.json
                                                       ↓
                              python scripts/components/render_report.py
                                                       ↓
                                                  report.html
```

详细流程图见 `steps/visual-system.md` §5。

## 1. 前置条件

- `04-personas.json` 已存在 + 校验已通过
- 已按 `visual-system.md` §2 确定每个 persona 的 `layout`(8 选 1)
- 已按 `scripts/components/REGISTRY.md` §9.2 挑出每个 persona 要用的组件(24 type 任选,只能从这 24 个里挑)

### 1.1 渲染前素材复检(必做)

写 `05-report.json` 并调用 `render_report.py` **之前**,执行 `steps/visual-assets.md` **检查点 B**:

1. 扫描 `画像头像素材/`、`界面截图/`
2. 对照 `03-field-alignment.json` 的 `visual_assets`
3. 用户说过要补但未放 → 再次提醒;有新文件未映射 → 列出文件名请用户确认
4. **禁止**未问过用户就全部占位交付且不提补图方式

渲染完成后按 **检查点 C** 在交付话术与 `交付件说明.md` 中说明素材使用/占位情况。

## 2. 渲染调用

```bash
python scripts/components/render_report.py \
    --input "过程稿/05-report.json" \
    --output "最终交付件-<对象类型>-<项目名>-<样本数>用户-<构建方式>/report.html" \
    --project-dir "<项目运行目录>"
```

该脚本自动跑:
- **事前** `validate_components_json.py`(schema 校验 05-report.json)
- **事中** layout 拼装(8 个 assemble + grid_solver 自动布局 + 双页拆分 + nav 配对 + accent 注入)
- **事后** `validate_html.py`(P7 HTML 体检,任何 ERROR 阻塞,产物不能交付)
- **打包**:`_design-tokens.css` + `_components.css` 复制到输出目录;实际用到的头像复制到 `assets/画像头像素材/`(来源:用户目录 → skill `assets/default-avatars/` → 占位)

`--skip-validate` 仅供调试用,**产物不可交付**(因为绕过了体检)。

---

## 3. 数据层产品规则(LLM 必须保证)

这些规则是**画像内容质量**约束,不是 HTML 写法。LLM 产 `05-report.json` 时必须遵守。

### 3.1 完整呈现,不在渲染层默默截断

发现内容放不下时,**回到字段对齐阶段砍/合并字段**(SKILL.md 约束 3),不要:
- 在 `section_block.body` 写省略号
- 用更短的 `summary` 偷掉原本应该展开的内容
- 用 `experience_goals` 兜底字段藏掉真实痛点

如果 grid_solver 估算总行数 > 3 行 → render_report 会自动拆双页(P8 layout-2b-grid-detail),不需要 LLM 操心。如果双页都装不下 → render_report raise,**回字段对齐**。

### 3.2 频次徽章(mention badge)

聚合 item 显示 `N/M`(painpoint_list、journey_2c.cells 触点等组件用):
- N = `mentioned_by` 数(几个受访者提到这条)
- M = 该画像的总受访者数
- 例:`3/5` 表示 5 位受访者中 3 位提到
- 高频共识(N/M ≥ 60%)由 renderer 自动应用 `.journey-pain-highlight` / `.mention-badge` 高亮,LLM 不接触 CSS class

### 3.3 多画像旅程必须独立分析(2026-05-20 P0 真实失败)

**真实失败**:HiRes 报告中 `内行深听派旅程` / `内容尝鲜派旅程` / `权益观望派旅程` 的思考、行为、触点、痛点、机会点、情绪曲线**完全一致**,只有标题和颜色不同。

数据层硬规则:
- 每个 persona 必须有自己的 `journey_2c` props,**不复用全局**
- 阶段名称可共用("发现 → 试听 → 开通 → 使用 → 续费"),但 `cells` 二维数组、`emotion` 数组每个 persona 独立
- **`cells` 轴向**:外层行 = `dimensions`,内层列 = `stages`;`len(cells) === len(dimensions)`,`len(cells[i]) === len(stages)`,`len(emotion) === len(stages)`
- **禁止按「一行一个阶段」组织 cells**(常见错误:5 阶段×4 维度写成 5 行×4 列 → 旅程页维度标签错位);校验码 `P8-JOURNEY-CELLS-SHAPE`
- 每个画像的 cells 至少含 3 个该画像专属证据或人群特征(如"内行深听派:对比普通音质后才愿意续费")
- 情绪曲线:每个画像 `emotion[i].level` 数组各自独立,**不能复制**

自检(由 LLM 自查 + render_report 体检 P7-SUBTITLE-DUPLICATE 等规则辅助):
- 任意两个 `journey_2c` props 去掉 `title` / `subtitle` 后,`cells` + `emotion` 内容相似度不能超过 70%
- 3 个旅程页内容完全相同 → 直接判定失败,回旅程分析阶段重做(**禁止换 CSS / 改颜色 / 改标题打补丁**)

### 3.4 协作字段(collab_flow)四个固定 key

`schema-tob.md collaboration` 严格 4 字段:`demand_source` / `deliverables` / `downstream_flow` / `kpi`。

P8 起 LLM **只填 value,不填 label**;label 由 `render_collab_flow` 硬编码注入(需求来源 / 交付物 / 流转去向 / KPI)。从根因切断 LLM 自创「上游 / 核心 / 下游」label 被 P7-BANNED-COLLAB-LABEL 拦截的同类问题。

```jsonc
// 正确(LLM 在 05-report.json 里写):
{
  "type": "collab_flow",
  "props": {
    "demand_source": "业务方提需求",
    "deliverables": "ETL 任务、数据看板",
    "downstream_flow": "交付给业务方做决策",
    "kpi": {"title": "任务成功率", "value": "≥ 99%"}
  }
}
```

LLM **不能**用自创 key(如 `upstream` / `self_role` / `downstream`)— schema 严格 enum 拦截。

### 3.5 受访者展示脱敏(SKILL.md 约束 8)

`evidence_quotes[i].source` / `matrix_2d.respondents[i].display_name` 必须用脱敏名:
- `姓氏 + 身份`(`张医生`)
- `姓氏 + 先生/女士`(`黄先生`)
- `U1` / `U2` 受访者代号(仅在无姓氏 + 无身份时用)

**禁止** `受访者1`、`U1_黄捷` 这类完整姓名。`matrix_2d.respondents[i].display_name` 有 schema pattern `^(?!受访者\d+).*$` 强约束。

### 3.6 多角色 L1 全景必须是「跨角色协同」,不是「N 条平行流水线」(2026-05-29)

`tob_journey_l1`(多角色全景旅程)用 `nodes`/`edges` UML DSL。**真实失败(2026-05-29)**:DevOps 5 角色 × 5 阶段的 L1 节点够多但全是 `step`、边只在自己泳道内,渲染成「5 条互不相干的竖线」,而真值(电力调度员)是跨角色协同 UML 流程图。

数据层硬规则(`_coop_semantics_gate`,多角色全景 L1 即 lanes ≥ 3 且 stages ≥ 3 强制,缺则 reject 回字段对齐):

- **跨泳道边 ≥ 15%**:角色交接(下令→执行、提需求→接需求、执行→审核)写成 from/to 落在不同 lane 的 edge,且必须对应 persona `collaboration` 字段里的真实上下游
- **`decision` ≥ 2**(关键分叉;「是」走主线,「否」仅当有独立补救节点,见 REGISTRY §3.0.2)、**`doc` ≥ 1**(产物沉淀,理想每阶段一个)、**`dashed` ≥ 1**(异步/系统推送)

**L1/L2 共用判断分支**(§3.0.2):菱形须问句;`branch:yes` 必填;`branch:no` 可选且不能回指主线前序节点;无补救任务则删否、把「如果否」写 `focuses`。

写法契约 + 真值范例见 `scripts/components/REGISTRY.md` §3.0.1 / §3.0.2 / §3.3 与 `golden_samples/tob_journey_l1_coop.json`。

---

## 4. 多画像导航(由 render_report 自动配对)

LLM **不写 nav**(P8 起由 `build_nav()` 按 persona id 后缀自动配对)。LLM 只要按 `visual-system.md` §3.2 的 id 命名约定写每个 persona 的 `id`:

| persona id 命名 | 自动出的 nav 形态 |
|---|---|
| `persona-1` 单独 | single 按钮 |
| `persona-1` + `persona-1-journey` | nav-pair(画像名 + ›旅程) |
| `persona-1-core` + `persona-1-detail` | nav-pair(画像名 + ›细节) |
| `persona-1` + `persona-1-detail` + `persona-1-journey` | nav-trio(画像名 + ›细节 + ›旅程) |
| `persona-q1`...`persona-q4` | 4 个 single(矩阵象限) |
| `journey-l1` | single(L1 全景旅程) |
| `matrix` / `distribution` | 不进 nav(它们是顶层首页容器) |

按钮的 `data-target` 由 build_nav 自动指向对应 slide id;`active` class 由 render_report 自动给首个 slide。LLM 不接触这些 attribute。

---

## 5. R4 矩阵 + R5 分布的数据层约束

### R4(layout-matrix-2d)

**总览页规则**(toB/toC 共用):
- 只用 `matrix_guidance_strip` + `matrix_2d`;**禁止**画像/旅程组件(`P8-OVERVIEW-FORBIDDEN-COMPONENT`)
- 配色由 `metadata.theme` + design tokens 驱动,**不改变** matrix DOM 结构

- **受访者点位**:LLM 给 `x` / `y`(0-100%);**不给** `label_direction` / `dx` / `dy`(Python 按象限自动避让,7 方向轮换)
- **空象限**:`quadrants[i].is_empty: true` 触发斜纹背景 + 居中胶囊「本研究样本未覆盖」
- **象限画像名 ≤ 5 字**(SKILL.md 约束 10,schema 强约束)
- **顶部研究问题引导条**:`matrix_guidance_strip.items` 至少 1 个,渲染在矩阵上方(不在下方)
- **不允许复制总图**:每位受访者的 `evidence` 必须从自己的访谈出,不能批量赋值

**R4 子页按 research_type 分支**:

| research_type | 象限画像 layout | 旅程(用户确认时) | theme |
|---------------|-----------------|------------------|-------|
| toC | `layout-2c-portrait` | `layout-2c-journey` + `journey_2c` | `2c` |
| toB/toD | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` `.is-l2` + `tob_journey_l2` | `2b` |

toB R4 画像组件映射见 `paradigms/R4-2d-matrix.md`「toB/toD 渲染专节」。禁止 toB 项目照抄 HiRes `build_hires_report.py`。

### R5(layout-distribution-multi)

**总览页规则**(toB/toC 共用):
- 只用 `distribution_multi` 容器;**禁止**画像/旅程组件(`P8-OVERVIEW-FORBIDDEN-COMPONENT`)
- 配色由 `metadata.theme` 驱动;**不改变** distribution DOM 结构

- **区分点数量 3-5**(schema 强约束),超过 5 → 回到分类阶段砍区分点,不在渲染层硬塞
- **档位严格 3 档**:high / middle / low,每档名是具体表现而不是"高 / 中 / 低"(`"能描述差异"` / `"只感觉清晰"` / `"完全靠想象"`)
- **档位名标在折线点旁边**:Python 自动定位(高档点上方 12px / 中档点右侧 14px / 低档点下方 12px),LLM 不接触坐标
- **同坐标多用户聚合 evidence**:Python 检测同坐标自动合并,LLM 在 `personas[i].respondents[j]` 给各自原话即可

**R5 子页按 research_type 分支**:

| research_type | 类别画像 layout | 旅程(用户确认时) | theme |
|---------------|-----------------|------------------|-------|
| toC | `layout-2c-portrait` | `layout-2c-journey` + `journey_2c` | `2c` |
| toB/toD | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` `.is-l2` + `tob_journey_l2` | `2b` |

toB R5 画像组件映射见 `paradigms/R5-multi-variable.md`「toB/toD 渲染专节」。

---

## 6. 最终交付件目录自检(由 render_report 调用方负责)

`render_report.py --output` 指向的目录名应符合:

```
最终交付件-<对象类型>-<项目名>-<样本数>用户-<构建方式>
```

例:`最终交付件-toC-HiRes音乐专区-12用户-R4矩阵/`

自检项(主对话或 wrapper 脚本):
- ✅ 目录名含对象类型 / 项目名 / 样本数 / 构建方式四类信息
- ❌ 禁用通用名:`report` / `final` / `最终版` / `2C结果` / `测试效果`
- ✅ `report.html` 在目录根
- ✅ 依赖文件(`_design-tokens.css` + `_components.css` + 头像 + 截图)都在同一目录
- ✅ 必有 `交付件说明.md`(列入口文件 + 依赖清单 + **用户可补充素材**一节,见 `steps/visual-assets.md` §4)
- ❌ HTML 内禁止引用 `过程稿/` / 本机绝对路径 / 工作目录外部资源

`render_report.py` 自动复制 CSS 与解析到的头像;界面截图 / `交付件说明.md` 仍由调用方拷贝。

---

## 7. 报错回到字段对齐的话术

布局预检 / 渲染失败时:

```
当前选了 12 个字段,grid_solver 估算需要 4 行(超过单页 3 行物理上限,
双页第二页也仍溢出)。

要继续渲染,需要做以下之一:
1. 减少字段(我可以推荐先砍哪些)
2. 减少字段内容(某些字段当前有 8 条,精简到 5 条)
3. 拆成多个 detail 页(persona-N-detail-1 / -detail-2,每页一个主题)

你倾向哪个?
```

**不允许**模型自己决定砍哪些(SKILL.md 约束 2)。用户拍板。

---

## 8. 边界情况

- **某画像样本只有 1 人**:照常渲染,频次徽章 `1/1`,顶部加提示话术
- **某字段所有受访者都没数据**:对应组件不渲染(不要硬塞「暂无数据」骨架);若该字段是 layout 必需组件 → schema 校验失败,回字段对齐补
- **字段内容包含中英混杂**:正常渲染,日志提示「该字段含英文,可在报告里检查」

---

## 渲染路径(V9)

**唯一入口**:`scripts/components/render_report.py` + `过程稿/05-report.json`。

事前校验:`scripts/validate_components_json.py`(实现于 `components/validate.py`)  
事后体检:`scripts/validate_html.py`
