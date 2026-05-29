# 范式 R5:多维分布(方式 E)

**用户场景**:toB / toD / toC 均可;想从访谈分出几类用户,区分点有 3-5 个,2 维坐标图不足以表达。

**输出**:多维分布图 + K 类画像。

---

## 前置条件

- `00-research-goal.json` 已确认
- `01-paradigm.json` 已确认范式 = R5
- `research_type` 由 `01-paradigm.json` 记录;决定 2B 或 2C 子页组件族(toB/toC **均支持**方式 E)

---

## 流程概览

```
Step 0: 推荐区分点(3-5 个)  → 模型读访谈 + 研究目标,推荐
Step 1: 档位划分(每区分点 2-3 档) → 模型推荐,用户确认
Step 2: 受访者档位映射          → 模型映射,显性化展示让用户确认
Step 3: 聚类生成画像            → 基于档位组合相似度聚类,用户确认
Step 4: 字段对齐                → 引用 steps/field-alignment.md
Step 5: 单文档抽取              → 引用 steps/extract-merge.md
Step 6: 多份合并                → 引用 steps/extract-merge.md
Step 7: 渲染(分布图 + 多画像)   → 引用 steps/render-persona-page.md
```

R5 和 R4 的核心区别:
- 区分点数量(3-5 vs 2)
- 档位数量(2-3 档 vs 2 档)
- 聚类逻辑(基于档位组合相似度 vs 直接象限对应)
- 输出图(多维分布图 vs 2 维坐标图)

---

## Step 0:推荐 3-5 个区分点

读 `schemas/classify-basis-toc.md` 第二部分。

模型推荐 3-5 个区分点(基于研究目标 + 访谈数据)。内部文件可继续使用"价值变量",但和用户沟通时必须说"区分点"。

**注意**:R5 不能只推荐 2 个(那是 R4)。如果模型判断只有 2 个区分点真正区分得好,应该建议用户切换到 R4。如果 6 个以上,应该建议精简到 5 以内,否则图会难读。

话术:

```
基于你的研究目标,我推荐这 4 个区分点来区分用户。区分点就是用来把用户分成几类的判断标准。

这次会产出一张多维分布图。你可以把它理解成一张用户类型对照表:每一行是一个区分点,每一列是一类用户,用来横向看几类用户到底差在哪。

【区分点 1】记录习惯
  - 含义、表现差异、为什么选它

【区分点 2】使用深度
  - 同上

【区分点 3】用户期待
  - 同上

【区分点 4】输出诉求
  - 同上

这 4 个区分点综合判断,可以聚出 3-4 类画像。

这个选择你认可吗?
- 认可
- 换某个区分点
- 增减区分点数量
```

写入 `02-classification.json`:

```json
{
  "paradigm": "R5",
  "value_variables": [
    {"key": "record_habit", "name": "记录习惯", "definition": "..."},
    {"key": "usage_depth", "name": "使用深度", "definition": "..."},
    {"key": "expectations", "name": "用户期待", "definition": "..."},
    {"key": "output_need", "name": "输出诉求", "definition": "..."}
  ]
}
```

---

## Step 1:档位划分

每个区分点 2-3 档。

模型推荐每个区分点的档位 + 显性化展示让用户确认(同 R4 Step 1 模式)。

**档位命名规则**:
- 不能只写"高 / 中 / 低"
- 要写成用户能理解的表现类型,例如"简单记录 / 编辑批注 / 收集创作"、"自主探索 / 依赖推荐"
- 档位名会进入多维分布图、用户类型解释、tooltip 和报告正文,必须逐项让用户确认。

**档位名确认闸门**:
- 模型必须把每个区分点下的全部档位名单独列出,并说明“这些词会进入最终报告”。
- 用户只确认区分点数量或区分点方向,仍然不能继续;还要确认每个档位名。
- 用户说某个词“不好”“不准”“太抽象”“不喜欢”,必须先给 2 到 4 个替代词,等待用户选择。
- 档位名确认前,不能进入受访者映射、聚类、画像合并或渲染。

推荐确认话术:

```text
下面这些档位名会进入最终报告,包括多维分布图和用户类型解释。请你确认这些词是否能接受:

【记录习惯】
- 简单记录: ...
- 编辑批注: ...
- 收集创作: ...

【使用深度】
- 自主探索: ...
- 依赖推荐: ...

如果某个词不满意,直接指出词名,我先改名再继续。
```

写入 `02-classification.json`:

```json
{
  "value_variables": [
    {
      "key": "record_habit",
      "name": "记录习惯",
      "label_confirmed": true,
      "levels": [
        {"name": "简单记录", "description": "...", "label_confirmed": true},
        {"name": "编辑批注", "description": "...", "label_confirmed": true},
        {"name": "收集创作", "description": "...", "label_confirmed": true}
      ]
    },
    ...
  ],
  "label_confirmed": true
}
```

---

## Step 2:受访者档位映射(显性化)

模型对每位受访者在每个区分点上打档,展示给用户确认。

```
我把 5 位受访者在 4 个区分点上的映射如下:

| 受访者 | 记录习惯 | 使用深度 | 用户期待 | 输出诉求 |
|--------|---------|---------|---------|---------|
| 张三   | 简单记录 | 基础    | 简单快捷 | 自留    |
| 李四   | 编辑批注 | 进阶    | 美观好用 | 自留    |
| 王五   | 编辑批注 | 进阶    | 美观好用 | 分享    |
| 赵六   | 收集创作 | 高阶    | 功能强大 | 创作输出 |
| 钱七   | 收集创作 | 高阶    | 功能强大 | 创作输出 |

每个档位都有原话证据,你可以 hover 看。

这个映射你认可吗?
- 认可
- 调整某位受访者的某个档位
```

写入 `02-classification.json`:

```json
{
  "respondent_mapping": {
    "张三": {"record_habit": "简单记录", "usage_depth": "基础", ...},
    ...
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

R5 的聚类逻辑:**基于档位组合的相似度**。

简单的聚类规则:
1. 把每位受访者的档位组合看作"指纹"
2. 指纹完全相同的人聚一类
3. 指纹略有差异(1 个区分点不同)的人也可以聚一类
4. 差异 ≥ 2 个区分点的人通常不聚

模型聚类后**显性化展示让用户确认**:

```
基于档位组合的相似度,我聚出 3 类画像:

【效率者】(2 人:李四、王五)
  - 记录习惯:编辑批注 / 使用深度:进阶 / 用户期待:美观好用 / 输出诉求:自留-分享
  - 共同特征:已经超越简单记录,但创作输出还不稳定

【创意者】(2 人:赵六、钱七)
  - 记录习惯:收集创作 / 使用深度:高阶 / 用户期待:功能强大 / 输出诉求:创作输出
  - 共同特征:把笔记作为创作素材库

【简单者】(1 人:张三)
  - 记录习惯:简单记录 / 使用深度:基础 / 用户期待:简单快捷 / 输出诉求:自留
  - 共同特征:只用最基础的功能

这个分类你认可吗?
- 认可
- 调整某位受访者的归属
- 拆分某类(比如效率者拆成自留派和分享派)
- 合并某类
```

写入 `02-classification.json` 的 `groups` 字段(同 R4 格式,但 quadrant 改为 cluster_id):

```json
{
  "groups": [
    {
      "name": "效率者",
      "cluster_id": "cluster-1",
      "members": ["李四", "王五"],
      "level_signature": {
        "record_habit": "编辑批注",
        "usage_depth": "进阶",
        "expectations": "美观好用",
        "output_need": ["自留", "分享"]
      }
    },
    ...
  ]
}
```

`level_signature` 用来在图上画"这类画像在每个区分点上落哪个档"。多档位的字段(如效率者在 output_need 上有"自留"和"分享"两档)用列表表示。

---

## Step 4:字段对齐(独立停点,不能折叠)

同 R4 Step 4。**硬规则(2026-05-28 加固)**:聚类确认后必须单独走 `steps/field-alignment.md` 完整 Step 1-5,不允许折叠。`03-field-alignment.json` 必须含 `fields_per_persona` + `user_confirmed: true` + `confirmation_message_summary` + `add_on_pages.journey`(布尔)。

## Step 5:标准过渡话术

```
分类已确认。接下来请确认每个画像页要展示哪些信息字段。
[展示完整字段池]
```

## Step 6-7:抽取 + 合并

同 R4。

---

## Step 7:渲染(多维分布图 + 多画像)

**渲染前**:执行 `steps/visual-assets.md` 检查点 B。

调用 `scripts/components/render_report.py`,读取 `过程稿/05-report.json`。

详细布局见 `steps/render-persona-page.md` §5「R4 矩阵 + R5 分布」。

页面顶部多维分布图:
- M 行(每行一个区分点)
- 每行从左到右是该区分点的档位
- K 类画像各用一条曲线穿过 M 行
- 不同画像用不同颜色

页面底部 K 个 tab,对应 K 类画像页。

## 渲染:按 research_type 选族

方式 E 主路由见 `SKILL.md` §布局自动判断。要点:
- **总览** `layout-distribution-multi`:结构 toB/toC 共用,仅 `metadata.theme` 改配色
- **子页**:toB → `layout-2b-grid` × N + `tob_journey_l2`; toC → `layout-2c-portrait` × N + `journey_2c`

详细子页约束见 `steps/render-persona-page.md` §5。

## toB/toD 渲染专节(2026-05-29)

当 `research_type=toB/toD` 且用户确认使用 R5 时:

**画像页(`layout-2b-grid`)** — 允许组件:
- `identity_panel`、`resp_rings`、`painpoint_list`、`scenario_grid`、`ai_scenario_grid`
- `collab_flow`、`kpi_panel`、`business_systems`、`generic_kv` / `generic_bullet` / `generic_text` / `titled_list`

**禁止**(toB 类别子页):
- `identity_card`、`section_blocks_grid`(toC 拼贴专用)
- toC 专属 section 标题语义(核心动机、消费观等)

**旅程页(`layout-2b-journey.is-l2`)** — 组件 `tob_journey_l2`;**禁止** `journey_2c`

**参考实现**:
- toB R4 最小样板:`scripts/tools/build_tob_r4_layout_sample.py`
- toB R5 最小样板:`scripts/tools/build_tob_r5_layout_sample.py`(结构可类比)
- **勿照抄** HiRes toC R5 脚本

---

## 用户对话样例

```
模型:
你的研究是 toC,方式 E(多维分布)。
基于研究目标(给笔记软件产品团队看,回答"不同类用户需要什么功能"),
我推荐这 4 个区分点:

[列出 4 个区分点及理由]

这个选择对吗?

用户:
对,但我想把"输出诉求"换成"协作需求"。

模型:
[换区分点,重新推荐档位]

档位对吗?

用户:
对。

模型:
[展示档位映射,5 人 × 4 个区分点的表格]

映射对吗?

用户:
对。

模型:
[展示聚类结果,3 类画像]

分类对吗?

用户:
"简单者"只有 1 个人,样本太少,合并到"效率者"里吧。

模型:
[更新分类]
现在分类是:
- 【效率者】(3 人:张三、李四、王五)
- 【创意者】(2 人:赵六、钱七)

继续吗?

用户:
继续。

模型:
分类已确认。接下来请确认每个画像页要展示哪些信息字段。
[展示 steps/field-alignment.md Step 1 的完整字段池]
你要哪些?

用户:
按推荐来。

模型:
[推荐 ★ 理由 + 询问是否加旅程页 + 按 visual-assets.md 问头像与典型场景截图]

用户:
不要旅程,这次只要画像。

模型:
[写 03-field-alignment.json: user_confirmed: true, add_on_pages.journey: false]
[抽取 + 合并 + 渲染]
报告已生成。包含 2 个画像和 1 张多维分布图(不含旅程页)。
```

---

## 边界情况

- **某类画像样本只有 1 人**:画像内容来自该位的抽取数据;模型主动建议合并到相近类别
- **聚类后类别过多(> 5 类)**:模型主动建议合并相近的类别,或重新审视区分点是否过多
- **聚类后只剩 1 类(所有人档位组合都接近)**:说明区分点选择不够好,模型主动建议换区分点或减少区分点数量
- **区分点数量超过 5**:模型在 Step 0 就拒绝,提示"超过 5 个区分点会很乱,建议精简或换方式 C"
- **用户想从 R5 切回 R4**:删 `02-classification.json` 和 `01-paradigm.json`,重启 skill 重选范式
- **toB/toD 用户主动要 R5**:支持;可提示「A/B/C 更常见」,但**不得**暗示 toB 不能用方式 E。确认后总览 `layout-distribution-multi` 仅配色,子页走 2B 族。

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
