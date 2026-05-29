# 公共步骤:画像字段对齐

这一步在所有 5 个范式中都会被引用。决定每个画像里要展示哪些字段(信息块)。

---

## 前置条件

- `00-research-goal.json` 已存在(研究目标已对齐)
- `01-paradigm.json` 已存在(范式已选)
- 已知道每个画像对应哪些受访者(R1/R2/R3 在 paradigm.json,R4/R5 在 02-classification.json)

---

## 字段对齐的两条原则

1. **完整列出可选字段池**,不只列默认推荐
2. **基于研究目标做推荐**,但用户拍板

## research_type 与 layout/components 绑定(2026-05-29)

字段池选定后,**渲染族必须与 research_type 一致**,不因 R4/R5 总览页共用而混用。完整 5 方式 × 2B/2C 路由见 `SKILL.md` §布局自动判断 与本文档 §2 主路由表。

| research_type | 字段池 | metadata.theme | 画像子页 layout | 旅程(用户确认时) |
|---------------|--------|----------------|-----------------|------------------|
| toB / toD | `schemas/schema-tob.md` | `2b` / `2d` | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` + `tob_journey_l2` / `tob_journey_l1` |
| toC | `schemas/schema-toc.md` | `2c` | `layout-2c-portrait` / `layout-2c-detail` | `layout-2c-journey` + `journey_2c` |

**R4/R5 总览页**(与上表子页分离):
- R4:`layout-matrix-2d` + `matrix_2d` / `matrix_guidance_strip` — 结构共用,**仅** `theme` 控制配色
- R5:`layout-distribution-multi` + `distribution_multi` — 同上
- 点击象限/类别后的 tab → 必须走上表「画像子页 / 旅程」列,不得因总览像 toC 样板而混用 toC 组件

硬规则:
- `research_type=toB` 时 **禁止** 在象限/画像子页使用 toC 字段(如「核心动机」「消费观」)和 toC 组件(`identity_card`、`section_blocks_grid`、`journey_2c`)
- 违反时 `validate_components_json.py` 报 `P8-THEME-LAYOUT-MISMATCH` 或 `P8-OVERVIEW-FORBIDDEN-COMPONENT`

---

## Step 0.5:硬门禁(2026-05-29)

**聚类/分类确认后必须先停在这一步**,不得静默写 `03-field-alignment.json` 或进入抽取/渲染。

1. 用 Step 1 话术展示**完整**字段池(★/□)
2. **等待用户回复**后再写 JSON
3. JSON 必填 `field_pool_presented: true`、`fields_display_names`、`user_confirmed: true`、`confirmation_message_summary`(≥10 字用户原话摘要)
4. 写 JSON 前跑 `python scripts/validate_field_alignment.py --workdir <过程稿目录>` 自检

仅有 `alignment_mode: recommended_by_goal` 而无用户原话摘要 → 视为未对齐,`recovery_check` 不会标记字段对齐完成。

---

## Step 1:展示完整字段池

模型从对应 schema 读取字段池(`schemas/schema-tob.md` 或 `schemas/schema-toc.md`),把所有可选字段**用中文展示**给用户。

话术模板(toB/toD 版):

```
基于你的研究目标(给 [audience] 看,回答 [research_question]),
我推荐以下字段(★ 是推荐的,你可以增减):

【用户身份】(画像左栏)
★ 基本特征:性别、岗位、部门、工作年限等
★ 知识背景:领域知识 / 工具能力 / 经验积累

【工作内容】(画像右栏核心)
★ 主要工作职责及占比
□ 主要业务任务(更细的任务清单)
□ 高频任务处理(每天/每周必做)
★ 岗位 KPI
★ 上下游协同关系
□ 使用的业务系统
□ 使用的 AI 辅助系统
□ 典型故障场景

【用户感受】(画像右栏)
★ 典型痛点
□ 体验目标

【用户原声】
★ 一句话需求
★ 代表性原声(2-4 条)

你要哪些?可以直接说:
- "按推荐来"(用 ★ 的字段)
- "加上 业务系统、AI 辅助系统"
- "去掉 协同关系,加上 典型故障场景"
- "全选" / "再砍一些"
```

toC 版话术结构类似,但用 `schemas/schema-toc.md` 的字段池。

---

## Step 2:推荐 ★ 的逻辑(必须基于研究目标)

模型推荐 ★ 的字段时,**必须显式回扣研究目标**。

- `audience` = "产品团队" + `research_question` 涉及"功能优先级" → 推荐侧重 `kpi`、`pain_points`、`high_freq_tasks`
- `audience` = "高层" + `decision_use` 涉及"团队拆分" → 推荐侧重 `responsibilities`、`collaboration`、`one_sentence_need`
- `audience` = "运营团队" + 探索性 → 推荐全面、不侧重某一组

模型推荐时**话术里必须显式说明**:

```
我推荐这些 ★ 字段的理由:
你说要"决定新功能要不要做",所以我推荐:
- 岗位 KPI(知道用户用什么标准衡量自己,新功能要服务这个标准)
- 典型痛点(新功能的切入点)
- 高频任务处理(新功能的使用场景密度)
- 一句话需求(对决策最有说服力的引用)
```

---

## Step 3:用户自定义字段

用户可能要加 schema 没有的字段。此时**模型必须问三件事**(SKILL.md 硬约束 6):

```
你要加的这个字段,我需要确认:
(a) 中文显示名是什么?(画像里会展示的名字)
(b) 这个字段收集什么内容?(1-2 句话定义)
(c) 数据形态是哪种?
    - 列表(几条短句)
    - 段落(一段说明文字)
    - 单值(一个名词/数字)
```

用户回答后,模型把自定义字段也写入 `03-field-alignment.json`,数据形态影响后续抽取 prompt 和渲染布局。

---

## Step 4:用户给的字段映射不到 schema 时

例:用户说"我要『日常工作压力』",但 schema 里没这个字段。

模型应该:

1. **先查 schema**,看是不是某个 schema 字段的别名/子集
   - "日常工作压力" 可能对应 `pain_points`(典型痛点)的一个子集
2. **如果是子集**,问用户:"你要的是不是 pain_points 里专门聚焦工作压力的部分?如果是,我把 pain_points 加进去就行。"
3. **如果不是**,走自定义字段流程

---

## Step 5:渲染布局预检 + 旅程页确认(含 toB L1 组织同构判定)

字段确定后,模型必须先补问呈现相关问题(含 **用户视觉素材** 与旅程页)。**素材必问**见 Step 5.0 与 `steps/visual-assets.md`;不能静默跳过。

### Step 5.0:用户视觉素材确认(所有范式,2B/2C 必问)

字段确定后、写 `03-field-alignment.json` **之前**,必须按 `steps/visual-assets.md` **检查点 A** 主动询问用户:

1. **画像头像** — 自定义放 `画像头像素材/`(`<画像中文名>.png`);不提供时说明会用 skill 默认库 `assets/default-avatars/`
2. **典型场景界面截图** — `界面截图/`,用于画像页场景卡片 / 专题详情 mockup(2B `scenario_grid`,2C `mockup_list` 等)
3. **旅程关注点截图** — 仅当用户选择加旅程页时追问,仍用 `界面截图/`,须先确认文件名与阶段/关注点映射

**禁止**:
- 只建空目录不提问
- 把场景截图说成「仅旅程用」而漏问 2B 典型业务场景 / 2C 专题截图
- 用户放入截图后自动猜测对应场景

用户回答后写入 `visual_assets`(格式见 `steps/visual-assets.md` §5)。`assets_asked: true` 为进入抽取的硬门禁之一。

### Step 5.0.1:旅程页与其它呈现问题

在 Step 5.0 素材问题之后,继续问旅程等呈现问题。toB/toD 多角色见 Step 5.1;toC 见 Step 5.2。

### Step 5.1:是否加旅程页 — **toB/toD 多角色(画像数 ≥ 2)**

**必须在写 `03-field-alignment.json` 之前完成。** 顺序固定:

**① 组织同构判定(模型先做,用人话告诉用户)**

读分组方式、逐字稿、`collaboration` 等,判定 `organizational_cohesion`:

| 判定 | 含义 | 下一步 |
|------|------|--------|
| `same_org` | 同企业/同产品平台/同交付链路,角色有交接 | 可推荐 L1 |
| `independent` | 角色彼此独立,无共同组织内工作流 | **禁止**推荐 L1 |
| `uncertain` | 证据不足或矛盾 | **必须先问用户**再定 |

话术(同组织,示例):

```
从访谈看,这 N 个角色都在 [DevOps 平台 / 同一项目组] 里分工协作,
需求、测试、发布、运维之间有交接 — 属于「同一组织内的多角色」。

如果加旅程,我可以做:
· 1 页「整体旅程」— 看各角色在同一流程里怎么配合
· 每个角色再各 1 页单角色旅程(可选)

你要加旅程页吗? 如果要,整体旅程和单角色旅程都要,还是只要其中一种?
```

话术(完全独立,示例):

```
从访谈看,这几个角色是 [不同类型客户 / 不同企业] ,彼此没有共同组织内工作流 —
这种不适合做「整体旅程」汇总页。

如果你需要旅程,我只能给每个角色各做 1 页单角色旅程。你要加吗?
```

话术(不确定,必问):

```
我还不能确定这些角色是否在同一组织/同一产品里协作。
请确认:他们是在同一个 [公司/项目/产品平台] 里分工,还是彼此独立的用户类型?
```

**② 用户拍板 → 写入 JSON**

| 用户回答 | `journey` | `journey_scope` | `journey_l1_eligible` |
|---------|-----------|-----------------|----------------------|
| 不要旅程 | `false` | `none` | `false` |
| 要,且同组织,要整体+单角色 | `true` | `L1_and_L2` | `true` |
| 要,且同组织,只要整体 | `true` | `L1_and_L2` | `true`(L2 可省略) |
| 要,且同组织,只要单角色 | `true` | `L2_only` | `true` |
| 要,但完全独立 | `true` | `L2_only` | `false` |
| 要,但完全独立且用户也拒绝单角色 | `false` | `none` | `false` |

**禁止**:在 `independent` 或用户否认同组织时仍写 `journey_l1_eligible: true`。

**范式确认阶段(Step 2)已做过的组织初判**,此处必须**显式回扣或修正**,不能前后矛盾。

### Step 5.2:是否加旅程页 — **toC 多画像 / toB 单画像 / toD 单画像**

toC 多画像(R4/R5 等):

```
这次是多画像研究,我可以为每个画像各做 1 页用户旅程图。你要加旅程页吗?
```

toB/toD **单画像**(R2):默认不加;研究目标明确含工作流/使用流程时可问:

```
这次只有一个角色画像,如果要看 ta 的工作流程,我可以加 1 页单角色旅程。你要加吗?
```

toC 单画像:同 SKILL.md 旅程规则 C/D。

**toB/toD 和 toC 都必须问(适用时)**。toB 多角色走 Step 5.1;toC 多画像走 Step 5.2。

**默认处理**:

### 2C 多画像旅程页规则

toC 多画像场景不能只生成一张“总旅程”。如果用户要旅程页,每个用户类型都要各接一张 `layout-2c-journey`:

- id: `persona-1-journey`、`persona-2-journey`、`persona-3-journey`
- tab: `画像名` 后紧跟 `画像名 · 旅程`
- 旅程页标题: `画像名 · 旅程`
- 阶段:通常 5 个,如“发现 → 试听 → 开通 → 日常使用 → 续费/流失”;确有证据时可 4-6 个
- 维度:至少包含“思考 / 行为 / 痛点 / 情绪”,有明确产品触点时加“触点”
- 单元格层级:先 `.journey-cell-keyword` 放 3-5 字关键词,再 `.journey-cell-summary` 放 15-25 字总结
- 痛点:高频共识用 `.journey-pain-highlight`,并加 `.journey-pain-opportunity-tag` 标“机会点”
- 情绪:必须使用 SVG 曲线 + `.emotion-area` 色块 + 峰谷 label,不能只写文字行

旅程图参考 `docs/reference/reports/D-二维矩阵/2C-HiRes-2维/report.html` 旅程 tab。tab 组织参考 `docs/reference/reports/B-多角色/2B-DevOps五角色/report.html` 的一级 nav 方式。
#### 2026-05-20 P0 补充:每个画像的旅程必须独立分析

多画像 toC 报告里,旅程页是“该用户类型如何经历产品”的分析结果,不能把一张总旅程复制 3 份再改标题。真实失败案例:HiRes 报告中 `内行深听派旅程`、`内容尝鲜派旅程`、`权益观望派旅程` 的思考、行为、触点、痛点、机会点、情绪曲线完全一致,只有标题和颜色不同。

生成规则:
- 每个 `persona-N-journey` 必须只使用该画像绑定的受访者、代表原声、痛点、使用场景、付费动机和流失原因来生成
- 允许阶段名称共用,如“发现专区 / 理解价值 / 试听与判断 / 开通付费 / 使用沉淀 / 复购或断开”
- 不允许 `思考`、`行为`、`触点`、`痛点`、`机会点`、`情绪标签` 六行整行复用
- 如果多个画像在同一阶段确有共同问题,也必须写出各自差异:谁卡在价值解释,谁卡在内容新鲜感,谁卡在价格权益
- 每个旅程页至少有 3 个单元格含该画像专属证据或人群特征,例如 `内行深听派:对比普通音质后才愿意续费`;`内容尝鲜派:被专区内容吸引但缺少持续新鲜感`;`权益观望派:价格和会员权益解释决定是否开通`
- 情绪曲线必须按画像差异单独绘制,不能三页使用同一条 SVG path 和同一组情绪标签

数据结构要求:
- `04-personas.json` 或生成中间数据里,每个 persona 必须有自己的 `journey` 对象
- `journey` 至少包含 `stages`、`rows.thinking`、`rows.behavior`、`rows.touchpoints`、`rows.pain_points`、`rows.opportunities`、`emotion.points`、`evidence_refs`
- 禁止只在全局写一个 `journey = {...}` 再让 `render_journey(p)` 复用
- `render_journey(persona)` 只能读取 `persona.journey`,不能读取全局 `journey` 或全局 `rows_data`

交付前自检:
- 去掉标题、画像名、颜色和头像后,任意两个 `layout-2c-journey` 的正文相似度不能超过 70%
- 若 3 个旅程页的阶段以外文本完全相同,直接判定失败,回到旅程分析阶段重做
- 自检失败时不能通过换 CSS、改标题或改颜色解决,必须重写每个画像的旅程内容
#### 2026-05-20 补充:画像与旅程必须做成组合页签

当一个画像后面接自己的旅程页时,导航必须把两者做成一组,视觉上像一个按钮被分成左右两段。左段是画像名,右段固定写 `› 旅程`。这条规则优先于旧的 `画像名 · 旅程` 文案。

```html
<div class="nav-pair">
  <button class="nav-btn nav-btn-persona" data-target="persona-1">内行深听派</button>
  <button class="nav-btn nav-btn-journey" data-target="persona-1-journey">› 旅程</button>
</div>
```

渲染检查:
- 有 `persona-N-journey` 时,同一个 `N` 必须有一个 `.nav-pair`
- 旅程按钮不能写成 `内行深听派旅程`
- `.nav-pair` 内两个按钮都必须有 `data-target`,点击后按 `_base.html` 的统一切换逻辑工作
- 用户说要旅程页 → 在 `03-field-alignment.json` 记录 `add_on_pages.journey = true`,并按 Step 5.1/5.2 填写 `journey_scope` / `journey_l1_eligible` / `organizational_cohesion`;渲染时按 `steps/visual-system.md` 选择 `layout-2b-journey` 或 `layout-2c-journey`
- 用户说不要旅程页 → 记录 `add_on_pages.journey = false`,`journey_scope = none`
- 用户提供自定义画像头像 → 记录 `avatar_provided: true` / `avatar_expected`;渲染时优先于默认库
- 用户不提供自定义头像、接受默认库 → `avatar_provided: false`, `avatar_use_default: true`
- 用户说稍后补**自定义**头像 → `avatar_deferred: true`,渲染前按 `steps/visual-assets.md` 检查点 B 复检
- 用户要典型场景截图 → `scenario_screenshots_enabled: true`,必须先确认 `scenario_screenshot_mapping`
- 用户明确不要典型场景截图 → `scenario_screenshots_enabled: false`
- 用户提供旅程关注点截图 → `screenshots_enabled: true`,必须先确认 `screenshot_mapping`
- 用户明确不要旅程截图 → `screenshots_enabled: false`
- 用户没有自定义头像素材 → `avatar_use_default: true`,按画像名匹配 `assets/default-avatars/`;未匹配才占位;**不反复追问**,但交付时须说明默认库路径(检查点 C)
### 受访者显示名对齐

R4/R5 后续要在矩阵里展示每位受访者,字段对齐阶段必须同时准备 `display_label`。它是展示名,不是内部 source。

生成顺序:
1. 从访谈文件名、source、基本资料里提取姓氏和身份
2. 输出 `黄医生`、`米同学`、`张*` 这类脱敏名
3. 如果只能得到编号,记录为待补充,不要直接进入最终渲染

这一步的目的像给每个点贴“可读但不泄露隐私的名牌”。没有名牌时,矩阵先不要交付。

---

字段确定后,模型必须做一个**布局预检**:

- 画像渲染是 12×3 网格布局(具体规则见 `steps/render-persona-page.md`)
- 字段数量过多会溢出
- 在 `03-field-alignment.json` 里标注:估计每个字段占多少格,合计是否超过 36 格

如果超过,**话术告诉用户**:

```
你选了 12 个字段,按一般填充情况会超过画像页的物理上限(36 格)。
要不要砍一些?优先级低的可以考虑:
- 主要业务任务(和职责重叠)
- 业务系统(可以并入痛点描述里)

或者你坚持都要,我会用 12×3 网格的最高密度填,但单个字段可能挤得紧。
```

---

## JSON 产物格式

`03-field-alignment.json`:

```json
{
  "version": "v9",
  "field_pool_presented": true,
  "fields_display_names": {
    "basic_profile": "基本特征",
    "knowledge_background": "知识背景",
    "responsibilities": "主要工作职责及占比",
    "kpi": "岗位 KPI",
    "collaboration": "上下游协同关系",
    "pain_points": "典型痛点",
    "one_sentence_need": "一句话需求",
    "representative_quotes": "代表性原声"
  },
  "fields_per_persona": {
    "默认": [
      "basic_profile",
      "knowledge_background",
      "responsibilities",
      "kpi",
      "collaboration",
      "pain_points",
      "one_sentence_need",
      "representative_quotes"
    ]
  },
  "custom_fields": [
    {
      "key": "daily_pressure",
      "display_name": "日常工作压力",
      "definition": "受访者描述每天/每周面临的具体压力点",
      "data_shape": "list",
      "applies_to": ["默认"]
    }
  ],
  "add_on_pages": {
    "journey": true,
    "journey_scope": "L1_and_L2",
    "journey_l1_eligible": true,
    "organizational_cohesion": "same_org",
    "journey_l1_reason": "五角色均围绕 DevOps 平台分工,访谈有跨角色交接",
    "journey_reason": "用户希望看跨角色协同链路"
  },
  "visual_assets": {
    "assets_asked": true,
    "assets_asked_at": "field_alignment_step5",
    "avatar_assets_dir": "用户画像报告输出/<项目名>-<日期时间>/画像头像素材/",
    "default_avatar_dir": "assets/default-avatars/",
    "avatar_use_default": true,
    "avatar_expected": ["调度员.png", "运维.png"],
    "avatar_provided": false,
    "avatar_deferred": true,
    "scenario_screenshots_enabled": true,
    "scenario_screenshot_mapping": {
      "工单系统.png": "调度员 / scenario_grid / 工单审批"
    },
    "screenshots_enabled": true,
    "screenshot_dir": "用户画像报告输出/<项目名>-<日期时间>/界面截图/",
    "screenshot_mapping": {
      "发布流水线.png": "运维 / journey / stage_3"
    }
  },
  "layout_estimate": {
    "默认": {
      "total_cells": 32,
      "limit": 36,
      "status": "ok"
    }
  }
}
```

**多画像场景(R1/R3/R4/R5)**:每个画像可以有独立的字段列表,但默认所有画像用同一套。用户如果要不同画像选不同字段,在 `fields_per_persona` 下用画像名作 key。

---

## 边界情况

### 完整呈现和溢出处理

渲染层不能用省略号或 CSS 截断正文。发现内容放不下时,按顺序处理:

1. 切换到更合适的现有 layout 或增加详情页
2. 降低密度但保持可读
3. 回到字段对齐,请用户删字段或合并字段

禁止在 `.section-block-body`、`.persona-name-anchor`、`.persona-subtitle`、`.matrix-quadrant-label`、`.nav-btn` 上使用 `line-clamp` 或 `text-overflow: ellipsis`。

- **画像数 > 5**:字段对齐时,模型主动建议"画像数较多,建议字段精简(8 个以下),否则页面会比较拥挤"
- **某画像样本只有 1 人**:照样按字段对齐,后续抽取时数据就是这一个人的;模型可在话术中提示"该画像样本只有 1 人,内容会比较单薄,可考虑合并到其他画像"
- **用户全选+加自定义,合计严重超限**:严格按 Step 5 报错,不要悄悄截断
