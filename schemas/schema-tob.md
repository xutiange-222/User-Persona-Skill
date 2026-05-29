# toB 画像字段定义

这份文档定义 toB 画像的 JSON schema、可选字段池、默认推荐字段集,以及每个字段的填写规范。

`extract_single.py` 和 `merge.py` 按这个 schema 产出 JSON,`validate.py` 按这个 schema 校验。

## 可选字段池(全集 + 中文说明,展示给用户选)

跟用户对齐字段时,把这份清单**完整列给用户**(用中文,带说明),让用户勾选要哪些。**不要只展示默认推荐**,因为默认推荐可能漏掉用户场景需要的维度。

### A. 用户身份(左栏展示)

- `basic_profile` — 基本特征(岗位、部门、工作年限、职业经历等)
- `knowledge_background` — 知识背景结构:**领域知识**(熟悉什么业务领域)、**工具能力**(掌握什么软件/平台/技术栈)、**经验积累**(行业年限、项目经验)

### B. 工作内容(右栏核心)

- `responsibilities` — 主要工作职责及分配占比(top3 职责,占比合计 100%)
- `main_tasks` — 主要业务任务(具体到日常实操的任务清单,通常 4-8 条,比 responsibilities 更细)
- `high_freq_tasks` — 高频任务处理(每天/每周必做的任务,频次 + 处理流程)
- `kpi` — 岗位考核指标(独立成块,具体指标 + 度量方式)
- `collaboration` — 上下游协同关系(需求来源、交付物、产物流转去向)
- `business_systems` — 使用的业务系统及典型场景(系统名 + 在哪个场景用 + 解决什么问题)
- `ai_assist_systems` — 使用的 AI 辅助系统及典型场景(已有的 AI 工具,以及在哪些场景用)
- `fault_scenarios` — 典型故障场景(异常/紧急情况下的处理过程)
- `scenarios` — 通用业务场景(scenarios 是一个泛化字段,如果用户分了 business_systems / ai_assist_systems / fault_scenarios,通常不再单独用 scenarios)

### C. 用户感受(右栏)

- `pain_points` — 典型痛点(具体可观察的问题,带数字/事实)
- `experience_goals` — 体验目标(理想中产品/工具应该怎么帮助他)

### D. 用户原声

- `one_sentence_need` — 一句话需求(从原话里选最能代表的一句,左栏底部锚点)
- `representative_quotes` — 代表性原声(2-4 条带来源标注,作为 hover tooltip 数据源,不单独成模块)

## 跟用户对齐字段的话术(必须用中文展示完整清单)

```
我把可选的字段维度都列给你,你选要哪些:

【用户身份】(展示在左栏)
□ 基本特征:岗位、部门、工作年限等
□ 知识背景:领域知识 / 工具能力 / 经验积累

【工作内容】(右栏核心,这一组建议至少选 3 个)
□ 主要工作职责及占比(top3 职责)
□ 主要业务任务(更细的任务清单)
□ 高频任务处理(每天/每周必做的)
□ 岗位考核指标 KPI
□ 上下游协同关系(需求来源 / 交付物 / 流转去向)
□ 使用的业务系统及典型场景
□ 使用的 AI 辅助系统及典型场景
□ 典型故障场景

【用户感受】
□ 典型痛点
□ 体验目标

【用户原声】
□ 一句话需求(代表性原话,展示在左栏底部)
□ 代表性原声(用作 hover 时显示证据,不单独成模块)

请告诉我你要哪些字段。
```

## 默认推荐字段集(用户没明确选时用这套)

如果用户没明确选,默认推荐这 9 个:

1. `basic_profile`
2. `knowledge_background`
3. `responsibilities`
4. `collaboration`
5. `scenarios`(通用业务场景)
6. `pain_points`
7. `experience_goals`
8. `one_sentence_need`
9. `representative_quotes`

## 字段优先级与布局

字段顺序就是优先级,布局引擎会按字段顺序在 12×3 网格上分配位置。一些常用组合参考:

- **「调度/运维」类岗位**:basic_profile + knowledge_background + responsibilities + collaboration + business_systems + fault_scenarios + pain_points + experience_goals + one_sentence_need + representative_quotes(右栏 6 字段,需要适当压缩)
- **「策划/决策」类岗位**:basic_profile + knowledge_background + responsibilities + collaboration + main_tasks + ai_assist_systems + pain_points + one_sentence_need
- **「产品/设计」类岗位**:basic_profile + knowledge_background + responsibilities + collaboration + scenarios + pain_points + experience_goals + one_sentence_need

跟用户对齐字段时:**右栏字段 ≤ 6** 是软约束(再多就降级或溢出)。

## 左栏布局约束(硬规则)

`basic_profile` 的子字段会全部渲染到左栏 meta 卡区域。**左栏空间有限,必须控制 basic_profile 子字段数 ≤ 5**(不含 background)。

默认推荐的 4 个 basic_profile 子字段(toB 场景下 gender 通常不关键,默认不展示):

- `department`(部门)
- `role`(岗位)
- `work_years`(工作年限)
- `background`(职业经历,占独立一行)

**如果用户要求加更多子字段(例如 education、age_range、city_tier),Claude 必须主动提醒**:

> "你已经选了 5 个基本特征字段,加 [新字段] 后左栏会比较拥挤,影响视觉效果。建议:
> a. 替换其中一个不重要的字段
> b. 或者把 [新字段] 信息合并进 background 描述里
> 你想怎么处理?"

不要静默接受超过 5 个的请求,布局会破。

## 完整 JSON Schema

```json
{
  "personas": [
    {
      "name": "画像名称(例:数据分析平台运维工程师)",
      "description": "一句话概括(20-40 字)",
      "user_count": 3,
      "persona_type": "toB",
      "source_documents": ["访谈_张三.docx", "访谈_李四.docx"],

      "basic_profile": {
        "department": "所属部门",
        "role": "岗位名称",
        "work_years": "工作年限范围(例:3-5年)",
        "background": "职业经历概述(50-100字)"
      },

      "knowledge_background": {
        "domain": "领域知识(例:熟悉数据治理、了解 ETL 流程)",
        "tools": "工具能力(例:精通 Airflow、掌握 SQL、熟悉 Grafana)",
        "experience": "经验积累(例:5年大数据平台运维经验,2 个千万级数据项目)"
      },

      "responsibilities": [
        {"task": "职责描述", "percentage": 40},
        {"task": "职责描述", "percentage": 35},
        {"task": "职责描述", "percentage": 25}
      ],

      "collaboration": {
        "demand_source": "需求来源(谁给输入,例:业务团队、产品经理)",
        "deliverables": "交付物/开发产物(例:数据看板、ETL 任务)",
        "downstream_flow": "产物下一步流转去向(例:交付给业务方做决策)",
        "kpi": "交付物的 KPI 指标(例:任务成功率 ≥99%、SLA 响应 <30min)"
      },

      "scenarios": [
        {
          "scenario": "典型业务场景描述",
          "tools": ["使用的工具/产品1", "工具2"]
        }
      ],

      "experience_goals": [
        {"title": "效率提升", "detail": "操作流程简化,不需要切换多个系统"},
        {"title": "降噪", "detail": "告警噪音降低,只看真正需要处理的"}
      ],

      "pain_points": [
        {"title": "告警噪音", "detail": "每天 200+ 条告警里只有 5 条真正需要处理"},
        {"title": "工具碎片化", "detail": "排查一个问题要切换 4-5 个系统"}
      ],

      "one_sentence_need": "代表该角色需求的用户原声 [来源:访谈_张三.docx]: \"原话\"",

      "representative_quotes": [
        "[来源:访谈_张三.docx]: \"原话片段...\"",
        "[来源:访谈_李四.docx]: \"原话片段...\""
      ]
    }
  ]
}
```

## 字段填写规范

### name(画像名称)

- 形式:**[岗位/角色] + [核心特征]**
- 例:「数据分析平台运维工程师」「中型企业一线销售」
- 不要用「画像 1」「典型用户 A」这种无信息的命名

### description(一句话概括)

- 20-40 字,概括身份 + 主要痛点 / 主要诉求
- 例:「负责千万级数据平台日常运维,长期被告警噪音和工具碎片化困扰」

### user_count

- 这个画像合并了多少份访谈
- 单文档 extract 时填 1,多文档合并时填合并的数量

### basic_profile.background

- 50-100 字概述,不是简历
- 例:「计算机本科,毕业后在 A 公司做了 3 年后端,2 年前转大数据运维方向,目前在 B 公司负责数据平台稳定性」

### knowledge_background(三栏并列)

- **domain**:业务领域知识,不是技术(例:数据治理、ETL、合规审计)
- **tools**:具体工具栈(例:Airflow、SQL、Grafana)
- **experience**:经验描述(例:5 年某领域经验)

### responsibilities(职责占比)

- top3 最核心职责,**占比合计必须 = 100%**
- 占比是数字(0-100),不是字符串
- 描述要具体到动作 + 对象,例:「编写 ETL 任务并做日常调度监控(40%)」

### collaboration(四个维度齐全)

- **demand_source** + **deliverables** + **downstream_flow** + **kpi**,四个都要填
- 任何一个缺失都填「文档未提及」,不要省略

### scenarios(场景 + 工具)

- 每个场景必须包含两部分:**场景描述** + **该场景使用的工具/产品**
- 2-4 个典型场景
- 工具列表:具体名字,不要写「办公软件」「监控工具」这种笼统词

### pain_points(核心痛点)

- 2-5 条
- 每条是 `{"title": "...", "detail": "..."}` 结构
  - **title**:3-6 字小标题,概括痛点核心(例:「告警噪音」「工具碎片化」)
  - **detail**:具体可观察的描述,带数字/事实(例:「每天 200+ 条告警里只有 5 条真正需要处理」)
- 好例子:`{"title": "告警噪音", "detail": "每天 200+ 条告警里只有 5 条真正需要处理"}`
- 坏例子:`{"title": "工具问题", "detail": "工具不好用"}`(空话,没事实)

### experience_goals(体验目标)

- 2-3 条
- 每条是 `{"title": "...", "detail": "..."}` 结构
  - **title**:2-4 字标题(例:「降噪」「效率提升」「自定义」)
  - **detail**:一句话目标(例:「告警噪音降低,只看真正需要处理的」)

### one_sentence_need

- 从原话里**选一句**,不要拼凑或改写
- 必须带来源标注

### representative_quotes(代表性原声)

- 2-4 条原话,**逐字稿真实出现过**的句子
- 每条带来源标注 `[来源:文件名]: "原话"`
- 选取标准:能代表这个画像最突出的特征(痛点 / 诉求 / 价值观)

## "文档未提及" vs "推断" vs "省略"

三种情况要分清楚:

- **文档未提及**:访谈里完全没提这个字段相关的内容 → 字段值填字符串「文档未提及」
- **推断:[基于...]**:访谈里没明说,但基于其他信息可以合理推断 → 字段值前缀「推断:」例如「推断:基于其提到加班频次,工作年限应在 3-5 年区间」
- **省略**:这个字段被用户在对齐阶段排除掉了 → JSON 里完全没有这个 key

第三种是用户主动排除的结果,前两种都要保留 key,只是值不同。

## 多文档合并时的处理

`merge.py` 把多份单文档抽取结果合并成一个画像时:

- **共性字段**(basic_profile, knowledge_background, collaboration):取多份的交集 + 高频项,标注哪些是共识哪些是个体差异
- **列表字段**(pain_points, scenarios, representative_quotes):合并去重,每个 quote 保留各自来源标注
- **比例字段**(responsibilities):取多份的均值后归一化到 100%
- **数字字段**(user_count):合并的份数
- **source_documents**:列出所有来源文件名

合并冲突时(例:3 个人说工作年限 3-5 年,1 个人说 5-8 年),取多数意见,在 description 里标注差异。

---

## 字段名 → P8 组件 type 映射(2026-05-25 起)

`04-personas.json` 里的字段名(数据层)与 `05-report.json` 里的组件 type(展示层)是两套命名空间。字段对齐阶段需要把每个数据字段映射到对应的组件 type:

| 数据字段(04-personas.json) | 渲染组件 type(05-report.json) | 备注 |
|---|---|---|
| `basic_profile` + `knowledge_background` | `identity_panel`(整合到 5 个子结构) | toB/toD 左栏身份卡 |
| `responsibilities` | `resp_rings` | 占比环图 |
| `collaboration` | `collab_flow` | 字段名严格用 `demand_source` / `deliverables` / `downstream_flow` / `kpi`(对齐 validate_html LEGAL_COLLAB_KEYS) |
| `main_tasks` | `titled_list` | 主要业务任务(高频任务字段 `high_freq_tasks` 亦走此组件) |
| `high_freq_tasks` | `titled_list` | 高频任务处理 |
| `scenarios` / `business_systems` | `scenario_grid` | 业务系统名作为 `tools` 标签;旧的独立"系统网格"组件已合并到此 |
| `ai_assist_systems` | `ai_scenario_grid` | 仅当访谈大量提到 AI 时启用;否则不渲染 |
| `fault_scenarios` | `titled_list` | 旧的独立"故障列表"组件已废弃,改走通用 titled_list 兜底 |
| `pain_points` | `painpoint_list` | 含 mention badge |
| `experience_goals` | `titled_list` 或 `generic_*` | 通用兜底 |
| `one_sentence_need` | `identity_panel.one_sentence_need` | 整合进左栏身份卡 |
| `representative_quotes` | `section_block.evidence_quotes` 或独立 `persona_quote_pull` | toC 用 quote_pull,toB 散布到各 grid_module 的 data-evidence |

**LLM 不允许自创组件 type**:数据字段没匹配的组件 → 走兜底(`titled_list` / `generic_text` / `generic_bullet` / `generic_kv`),通过 `--field-labels` 传中文显示名。

**完整 24 个组件 type 清单**:见 `scripts/components/REGISTRY.md` §9.2（以 `schemas/report.json` enum 为准）。

**用户图片素材(字段对齐必问)**:toB 画像页头像走 `identity_panel.persona_avatar`;典型业务场景走 `scenario_grid.scenes[].screenshot`(文件在 `<项目运行目录>/界面截图/`)。流程见 `steps/visual-assets.md`(与 toC 同一套三处检查点)。
