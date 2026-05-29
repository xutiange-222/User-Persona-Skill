# 范式 R4:2 维矩阵(方式 D)

**用户场景**:toB / toD / toC 均可;想从访谈分出几类用户,有 2 个最关键的区分点。

**输出**:坐标矩阵图 + 4 象限对应 4 类画像。

---

## 前置条件

- `00-research-goal.json` 已确认
- `01-paradigm.json` 已确认范式 = R4
- `research_type` 由 `01-paradigm.json` 记录;决定 2B 或 2C 子页组件族(toB/toC **均支持**方式 D)

---

## 流程概览

```
Step 0: 推荐区分点(2 个)  → 模型读访谈 + 研究目标,推荐
Step 1: 档位划分(每区分点 2 档) → 模型推荐,用户确认
Step 2: 受访者档位映射         → 模型映射,显性化展示让用户确认
Step 3: 聚类生成画像           → 4 象限 = 4 类画像,用户确认
Step 4: 字段对齐               → 引用 steps/field-alignment.md
Step 5: 单文档抽取             → 引用 steps/extract-merge.md
Step 6: 多份合并               → 引用 steps/extract-merge.md(每画像独立 reduce)
Step 7: 渲染(矩阵图 + 多画像)  → 引用 steps/render-persona-page.md
```

R4 比 R3 多的核心:**区分点选择 + 档位划分 + 档位映射 + 坐标图渲染**。内部文件可继续使用"价值变量",但和用户沟通时必须说"区分点"。

---

## Step 0:推荐 2 个区分点

读 `schemas/classify-basis-toc.md` 第二部分(区分点推荐库)。

模型基于:
1. 研究目标(audience / research_question / decision_use)
2. 访谈数据中实际可见的差异维度

**用三个筛选标准选**(覆盖性 / 差异性 / 决策相关性,详见 schemas/classify-basis-toc.md)。

推荐话术(必须显式回扣研究目标):

```
基于你的研究目标(给营销团队看,回答"新用户最先被什么打动"),
我看了 X 份访谈,推荐用这 2 个区分点作为坐标。区分点就是用来把用户分成几类的判断标准:

【横轴】价格敏感度
  - 含义:用户对价格的关注程度
  - 受访者表现:5 位中,2 位高敏感,2 位中等,1 位低敏感
  - 为什么选它:对价格策略和首屏文案设计有核心影响

【纵轴】品牌偏好
  - 含义:用户对品牌的信任和倾向
  - 受访者表现:5 位中,3 位看重品牌,2 位不看
  - 为什么选它:决定产品要不要做品牌叙事

这 2 个变量交叉成 4 个象限,每个象限对应一类画像。

这个选择你认可吗?
- 认可,继续划档位
- 换一个区分点
- 我心里有别的区分点(告诉我,我判断它合不合适)
```

用户确认后写入 `02-classification.json`:

```json
{
  "paradigm": "R4",
  "value_variables": [
    {
      "key": "price_sensitivity",
      "name": "价格敏感度",
      "axis": "x",
      "definition": "用户对价格的关注程度"
    },
    {
      "key": "brand_preference",
      "name": "品牌偏好",
      "axis": "y",
      "definition": "用户对品牌的信任和倾向"
    }
  ]
}
```

---

## Step 1:档位划分

每个区分点分**2 档**(R4 标准),产生 2×2=4 象限。

**档位命名硬规则**:两端不能只叫"高 / 低"。必须写出有含义的两极命名,让用户一眼知道差异是什么。档位名会进入矩阵象限、tooltip、用户类型解释和报告正文,必须让用户逐项确认。

错误:
- 价格敏感度:高 / 低
- 品牌偏好:高 / 低

正确:
- 价格敏感度:反复比价 / 认可即买
- 品牌偏好:品牌背书驱动 / 产品体验驱动

模型推荐档位 + 显性化展示让用户确认:

```
对【价格敏感度】,我建议分 2 档:
  反复比价:看到价格会犹豫,会跨平台比较和等折扣
  认可即买:认可产品价值后直接购买,不太纠结价格

对【品牌偏好】,我建议分 2 档:
  品牌背书驱动:看重品牌历史、口碑和故事
  产品体验驱动:更看产品本身,品牌不是主要原因

这个档位划分你认可吗?可以调整数量或重命名。
```

**档位名确认闸门**:
- 模型必须明确告诉用户:“下面这些词会进入最终报告,请确认你是否接受这些命名。”
- 用户只回复“区分点可以”,仍然不能继续;还要追问档位名是否认可。
- 用户说某个词“不好”“不准”“太抽象”“不喜欢”,必须先给 2 到 4 个替代词,等待用户选择。
- 档位名确认前,不能进入受访者映射、聚类、画像合并或渲染。

写入 `02-classification.json`:

```json
{
  "value_variables": [
    {
      "key": "price_sensitivity",
      "name": "价格敏感度",
      "axis": "x",
      "label_confirmed": true,
      "levels": [
        {"name": "反复比价", "description": "看到价格会犹豫,会跨平台比较和等折扣", "label_confirmed": true},
        {"name": "认可即买", "description": "认可产品价值后直接购买,不太纠结价格", "label_confirmed": true}
      ]
    },
    ...
  ],
  "label_confirmed": true
}
```

---

## Step 2:受访者档位映射(显性化)

模型读 `processed/` 下每位受访者的访谈,在每个区分点上给一个档位判断 + 证据原话。

映射结果**显性化展示**(SKILL.md 职责表 + 离群处理原则):

```
我把 5 位受访者在【价格敏感度】上的映射如下:

档位高:张三、李四
  - 张三原话:"我会去三个平台比价,差几块钱也要选便宜的"
  - 李四原话:"我加购物车里要放一周,等折扣才下手"

档位低:王五、赵六、钱七
  - 王五原话:"我看到就买了,没怎么比"
  - 赵六原话:"贵点没关系,只要东西好"
  - 钱七原话:"价格对我不是首要考虑"

【品牌偏好】上的映射类似。

这个映射你认可吗?
- 认可
- 调整某位受访者的档位
```

写入 `02-classification.json`:

```json
{
  "value_variables": [ ... ],
  "respondent_mapping": {
    "张三": {"price_sensitivity": "高", "brand_preference": "高"},
    "李四": {"price_sensitivity": "高", "brand_preference": "低"},
    "王五": {"price_sensitivity": "低", "brand_preference": "高"},
    "赵六": {"price_sensitivity": "低", "brand_preference": "高"},
    "钱七": {"price_sensitivity": "低", "brand_preference": "低"}
  }
}
```

---

## toC 用户类型命名硬规则

用户类型名称是给产品、设计、用研快速理解用的,必须短、直观、能一眼读懂。

- 最多 5 个汉字,不含“型”“用户”“人群”等尾巴时优先
- 优先使用“内行深听派”“高配氛围派”“入门体验派”这类人群直觉名
- 不要把坐标轴逻辑直接拼成名称,例如不要写“价值待教育型价格权益用户”
- 如果分类逻辑很复杂,把复杂解释放进副标题、矩阵说明或画像描述,不要塞进名称
- tab 和矩阵象限只放短名称,长解释放 hover 或正文
- 命名前先读给产品经理听一遍:5 秒内能理解才通过
- 禁止把两个区分点直接拼接成抽象词,如“价值直觉型深度”“价值待教育型内容尝鲜者”
- 如果必须解释判断逻辑,放到副标题、矩阵说明或 hover,名称只承担识别作用

## Step 3:聚类生成画像(显性化)

R4 的聚类很简单 — 4 象限直接对应 4 类画像。

模型基于映射结果聚出每个象限的画像:

```
基于档位映射,我聚出 4 类画像:

【象限 1:反复比价 × 品牌背书驱动】(1 人:张三)
  - 想法预设:精打细算但有品牌情结,会等大牌打折
  - 推荐画像名:"精明品牌追随者"

【象限 2:反复比价 × 产品体验驱动】(1 人:李四)
  - 想法预设:实用派,只看性价比
  - 推荐画像名:"性价比实用派"

【象限 3:认可即买 × 品牌背书驱动】(2 人:王五、赵六)
  - 推荐画像名:"品牌忠实派"

【象限 4:认可即买 × 产品体验驱动】(1 人:钱七)
  - 推荐画像名:"实用高消费者"

这个分类你认可吗?
- 名称需要调整
- 调整某位受访者的归属
- 某象限样本太少,要不要合并
- 某象限为空 — 是真的没有这种用户,还是样本不够覆盖?
```

写入 `02-classification.json` 的 `groups` 字段:

```json
{
  "groups": [
    {
      "name": "精明品牌追随者",
      "quadrant": "x-高_y-高",
      "members": ["张三"]
    },
    {
      "name": "性价比实用派",
      "quadrant": "x-高_y-低",
      "members": ["李四"]
    },
    {
      "name": "品牌忠实派",
      "quadrant": "x-低_y-高",
      "members": ["王五", "赵六"]
    },
    {
      "name": "实用高消费者",
      "quadrant": "x-低_y-低",
      "members": ["钱七"]
    }
  ]
}
```

---

## Step 4:字段对齐(独立停点,不能折叠)

**硬规则(2026-05-28 加固)**:聚类确认完成后,模型必须**单独**走 `steps/field-alignment.md` 完整 Step 1-5,**不允许**用 `[字段对齐 → 抽取 → 合并 → 渲染]` 折叠记号一笔带过。

进入 Step 5(抽取)前,`03-field-alignment.json` 必须含:
- `fields_per_persona`(每个画像选了哪些字段;不能只写「按推荐来」)
- `user_confirmed: true` + `confirmation_message_summary`(用户原话摘要,≥ 10 字)
- `add_on_pages.journey`(布尔,toC 多画像必填,见 SKILL.md 旅程确认规则)

缺任一字段 → 不能进入抽取阶段,先补问用户。断点续跑时若 `03-field-alignment.json` 已存在但缺这些字段,视为未完成。

## Step 5:标准过渡话术

```
分类已确认。接下来请确认每个画像页要展示哪些信息字段。
[展示 steps/field-alignment.md Step 1 的完整字段池]
```

不允许跳过这一句直接进入抽取。

## Step 6-7:抽取 + 合并

执行 `steps/extract-merge.md`。

每个画像独立 reduce(同 R1)。

注意 toC 画像的内容处理原则(SKILL.md "toC 画像的内容处理原则"):
- 多数派归纳
- 分歧时基于研究目标选取一个表述
- 样本小(1-2 人)时给抽象表述,不堆细节

---

## Step 7:渲染(矩阵图 + 多画像)

## 渲染:按 research_type 选族

方式 D 主路由见 `SKILL.md` §布局自动判断。要点:
- **总览** `layout-matrix-2d`:结构 toB/toC 共用,仅 `metadata.theme` 改配色
- **子页**:toB → `layout-2b-grid` + `tob_journey_l2`; toC → `layout-2c-portrait` + `journey_2c`

**渲染前**:执行 `steps/visual-assets.md` 检查点 B(头像 + 典型场景截图;toC 含 `mockup_list` 专题图)。

调用 `scripts/components/render_report.py`,读取 `过程稿/05-report.json`。

详细布局见 `steps/render-persona-page.md` §5「R4 矩阵 + R5 分布」。

页面顶部 2 维矩阵图,4 象限对应 4 个 tab。点击象限或 tab 切换显示对应画像。

**子页按 `research_type` 分支**(见 `steps/visual-system.md` §2 R4/R5 子页路由表):
- **toC**:象限画像 `layout-2c-portrait`;旅程 `layout-2c-journey` + `journey_2c`
- **toB/toD**:象限画像 `layout-2b-grid`;旅程 `layout-2b-journey` `.is-l2` + `tob_journey_l2`

**交付时**:按 visual-assets 检查点 C 说明各画像头像与场景截图使用情况。

---

## toB/toD 渲染专节(2026-05-29)

当 `research_type=toB/toD` 且用户确认使用 R4 时:

**画像页(`layout-2b-grid`)** — 允许组件:
- `identity_panel`、`resp_rings`、`painpoint_list`、`scenario_grid`、`ai_scenario_grid`
- `collab_flow`、`kpi_panel`、`business_systems`、`generic_kv` / `generic_bullet` / `generic_text` / `titled_list`

**禁止**(toB 象限子页):
- `identity_card`、`section_blocks_grid`(toC 拼贴专用)
- toC 专属 section 标题语义(核心动机、消费观、使用习惯等) — 应映射为 toB 字段池

**旅程页(`layout-2b-journey.is-l2`)** — 组件 `tob_journey_l2`:
- 两行主体:「工作流程」(UML 节点/边) + 「关注点/痛点」(`focuses`)
- **禁止** `journey_2c`、情绪曲线 emoji 行

**参考实现**:
- toB R4 最小样板:`scripts/tools/build_tob_r4_layout_sample.py`
- **勿照抄** HiRes `build_hires_report.py`(仅 toC R4)

**journey_2c 仅 toC 使用**;若误用,cells 必须为「维度×阶段」:

```json
{
  "stages": ["告警发现", "研判决策", "协调执行", "处置复电", "结案复盘"],
  "dimensions": ["思考", "行为", "痛点", "触点"],
  "cells": [
    [ /* 思考 × 5 阶段 */ ],
    [ /* 行为 × 5 阶段 */ ],
    [ /* 痛点 × 5 阶段 */ ],
    [ /* 触点 × 5 阶段 */ ]
  ],
  "emotion": [ /* 5 项,与 stages 对齐 */ ]
}
```

**禁止按「一行一个阶段」组织 cells**。

---

## 用户对话样例

```
模型:
你的研究是 toC,方式 D(2 维矩阵)。
基于研究目标,我推荐这 2 个变量:
- 横轴:价格敏感度
- 纵轴:品牌偏好

[展示理由]

这个选择对吗?

用户:
品牌偏好换成"购物决策周期"(冲动 vs 长期研究)。

模型:
好,我重新推荐档位:
- 价格敏感度:反复比价 / 认可即买
- 购物决策周期:冲动 / 长期研究

档位对吗?

用户:
对。

模型:
[展示档位映射]

档位映射对吗?

用户:
对,继续。

模型:
[展示 4 象限聚类]

分类对吗?

用户:
继续。

模型:
分类已确认。接下来请确认每个画像页要展示哪些信息字段。
[展示 steps/field-alignment.md Step 1 的完整字段池 ★/□ 清单]
你要哪些?

用户:
按推荐来,加上"消费观"。

模型:
[展示推荐 ★ 字段的理由,再问要不要旅程页]
最后确认图片素材(见 steps/visual-assets.md 检查点 A):
1. 每个画像要不要放头像?路径 `画像头像素材/`,建议文件名如 `品质聆听者.png`
2. 典型场景/产品界面要不要配图?路径 `界面截图/`,放好后我帮你确认每张对应哪个场景
3. 这份报告要不要加用户旅程页?
4. 若加旅程,旅程关注点要不要补充界面截图?(同一界面截图目录)

用户:
旅程页要加,场景截图有 2 张稍后放,头像明天补。

模型:
[写 03-field-alignment.json,user_confirmed: true,visual_assets 含 avatar_deferred 等]
[渲染前检查点 B:列出界面截图目录,确认映射]
[抽取 + 合并 + 渲染]
报告已生成。包含 4 个画像、4 张旅程页和 1 张矩阵图。
[检查点 C:头像仍为占位;已用 scene-a.png 等 / 场景图待确认…]
```

---

## 边界情况

- **某象限为空**:模型在 Step 3 显性化提示"该象限无样本",用户决定是否在最终报告中保留空象限(矩阵图上画虚线提示"该类用户未覆盖")
- **某象限只有 1 人**:画像内容来自该位的抽取数据,无 reduce 必要;模型话术提示"该象限只有 1 人,画像内容主要来自一位的数据,可考虑增加访谈样本"
- **用户对档位划分不满意,反复调整**:每次调整都重新跑 Step 2(档位映射),不必重跑 Step 0(区分点选择)
- **用户换区分点**:从 Step 0 重新开始,删 `02-classification.json` 重启 skill
- **toB/toD 用户主动要 R4**:支持;可提示「A/B/C 更常见」,但**不得**暗示 toB 不能用方式 D。确认后总览 `layout-matrix-2d` 仅配色,子页走 2B 族。

---

## 最终产出格式(P8 组件化,2026-05-25 起强制)

不允许直接产 HTML 字符串。必须产符合 `scripts/components/schemas/report.json` 的 components JSON,存到 `过程稿/05-report.json`。

**LLM 决策**:
1. 完成 `04-personas.json` 后,按 `steps/visual-system.md` §2 选定每个 persona 的 `layout`
2. 按 `scripts/components/REGISTRY.md` §9.2 的 24 个组件 type,挑出本画像需要的组件并按重要性排序
3. 每个组件的 `props` 严格匹配 `scripts/components/schemas/<type>.json`
4. 写出 `05-report.json`(顶层结构见 `schemas/report.json`)

**渲染调用**:

```bash
python scripts/components/render_report.py     --input "过程稿/05-report.json"     --output "最终交付件-<目录>/report.html"
```

该脚本自动跑:事前 schema 校验(validate_components_json)+ layout 拼装(8 个 assemble 函数)+ CSS 随包 + 事后 HTML 体检(validate_html)。

**禁止**:
- 直接产 HTML 字符串(不要 cat <<EOF > report.html)
- 用 Edit 工具改最终 report.html(改源 JSON 重跑)
- 自创 component type 或 layout 名(只能从 24 type + 8 layout 里挑)
- 在 props 里塞 schema 之外的字段(`additionalProperties: false` 会拒)
- 写 SVG path / Unicode emoji 字符 / inline 几何 var(由 Python 渲染层算,见 SKILL.md 约束 13)

校验失败 → 看 ERROR 的 path 和 code 改 `05-report.json`,不要改 HTML 打补丁。
