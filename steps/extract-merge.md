# 公共步骤:抽取 + 合并(map-reduce)

把访谈逐字稿变成结构化画像数据的核心步骤。采用 map-reduce 架构。

---

## 为什么用 map-reduce

如果一次性把所有访谈塞给模型让它"自己归纳",单次输入太大,弱模型 hold 不住,且容易丢细节。

map-reduce 架构:
- **map**:每份访谈独立抽取一次(单次输入小,质量高)
- **reduce**:每个字段独立合并一次(每次只看一个字段的多份输出,语义聚类精准)

总 token 消耗高,但单次调用都不大,弱模型也能跑。

---

## 前置条件

- `03-field-alignment.json` 已存在(字段已对齐)
- `03-field-alignment.json` 必须包含以下字段(2026-05-28 加固,缺一则视为未完成,**不能进入抽取**):
  - `field_pool_presented: true`(已向用户展示完整字段池)
  - `fields_display_names`(对象,字段 key → 中文展示名)
  - `fields_per_persona`(对象,每个画像选了哪些字段)
  - `user_confirmed: true`(布尔,表示用户已认可字段池)
  - `confirmation_message_summary`(字符串,≥ 10 字,用户原话摘要锚点)
  - `visual_assets.assets_asked: true`
  - 抽取前执行:`python scripts/validate_field_alignment.py --workdir <过程稿>`
  - `add_on_pages.journey`(布尔,toC 多画像 / toB 多角色场景必填,见 SKILL.md 约束 14 + 旅程确认规则)
  - toB/toD 且画像数 ≥ 2 时另必填:`add_on_pages.journey_scope`、`journey_l1_eligible`、`organizational_cohesion`
  - 若 `alignment_mode` 字段存在且值为 `recommended_by_goal`,但无 `user_confirmed: true` → 视为未确认,回退到字段对齐 Step 1
- `processed/` 目录已有标准化的 txt 文件(每位受访者一个)
- 每个画像知道对应哪些受访者(从 `01-paradigm.json` 或 `02-classification.json` 读)

---

## Step 1:单文档抽取(map 阶段)

由 `scripts/extract_single.py` 执行,**调用模型**。

对每位受访者:
1. 读 `processed/{受访者名}.txt`
2. 读 `03-field-alignment.json` 拿到该画像要的字段列表
3. 拼装 prompt(基础 prompt 来自 `assets/prompts/extract-{tob|toc}.md` + 字段定义)
4. 调用模型抽取
5. 产物写入 `extracted/{受访者名}.json`

### 抽取 prompt 的核心原则

**正向引导,不要负向禁止**(SKILL.md 硬约束 + memory)。例:

✗ 错误写法:"不要把领域知识写进 tools 字段"

✓ 正确写法:"`tools` 字段放通用工具能力(Python、Excel、Photoshop 等),例:'熟练使用 Python 处理数据'。领域知识(熟悉电力调度业务、医疗术语等)放在 `domain_knowledge` 字段。"

### 每个字段抽取产物的标准格式

```json
{
  "field_name": "pain_points",
  "items": [
    {
      "content": "调度过程中要同时盯 5 个监控屏,容易漏看告警",
      "evidence_quote": "我们调度员有时候要看 5 个屏幕,我有一次就漏了一条告警,后面是同事提醒的"
    },
    {
      "content": "夜班疲劳导致判断速度变慢",
      "evidence_quote": "夜班三点多的时候,真的会愣神,有时候反应慢半拍"
    }
  ]
}
```

每条 `content` 都必须附 `evidence_quote`(原话)。这是 SKILL.md 硬约束 5 的硬性要求。

### 单值字段格式

```json
{
  "field_name": "one_sentence_need",
  "value": "希望 AI 帮我提前预警,而不是事后通知",
  "evidence_quote": "现在的系统都是事后通知,我希望 AI 能提前 5 分钟告诉我哪个机组可能出问题"
}
```

---

## Step 2:逐字段合并(reduce 阶段)

由 `scripts/reduce_field.py` 执行,**调用模型**。

对每个画像、每个字段:
1. 收集这个画像下所有受访者在这个字段上的抽取产物
2. 拼装 reduce prompt(来自 `assets/prompts/reduce-{字段名}.md`)
3. 调用模型聚合:语义聚类 + 输出统一格式
4. 写入该画像的 JSON 节点

### Reduce 的核心约束

- **输出格式严格**:每个聚合后的观点必须有 `mentioned_by`(哪些受访者提到了)+ `evidence_quotes`(每位受访者的原话)
- **聚类语义而非字面**:"AI 应该提前预警" 和 "我希望系统能提前告诉我" 是同一个意思,聚成一条
- **保留差异**:5 个人有 4 种说法时,不能强行收敛成 1 条;真实的多样性要留下来
- **toC 处理**:见 SKILL.md "toC 画像的内容处理原则"
  - 多数派一致 → 归纳
  - 分歧 → 基于研究目标选取一个表述
  - 样本小 → 抽象表述,不堆细节

### Reduce 产物标准格式

```json
{
  "field_name": "pain_points",
  "items": [
    {
      "content": "多屏监控容易漏看告警",
      "mentioned_by": ["邓老师", "孔老师", "肖老师"],
      "frequency": "3/5",
      "evidence_quotes": [
        {"source": "邓老师", "quote": "我们调度员有时候要看 5 个屏幕..."},
        {"source": "孔老师", "quote": "屏幕太多了,有几次都没注意到红色告警..."},
        {"source": "肖老师", "quote": "尤其是大风天,告警很多,屏幕看不过来..."}
      ]
    },
    {
      "content": "夜班疲劳导致判断变慢",
      "mentioned_by": ["邓老师", "刘老师"],
      "frequency": "2/5",
      "evidence_quotes": [
        {"source": "邓老师", "quote": "夜班三点多真的会愣神..."},
        {"source": "刘老师", "quote": "凌晨两三点是我们最容易出错的时间..."}
      ]
    }
  ]
}
```

**`mentioned_by` 里每一位都必须有对应的 `evidence_quote`**(SKILL.md 硬约束 5)。

---

## Step 3:合并到 personas.json

由 `scripts/merge.py` 执行,**纯固化逻辑**(不调模型)。

把每个画像的所有字段 reduce 产物组装成最终 JSON:

```json
{
  "version": "v8",
  "research_goal": { ... },
  "paradigm": "R2",
  "personas": [
    {
      "name": "电力调度员",
      "members": ["邓老师", "孔老师", "肖老师", "刘老师", "碳中和老师"],
      "fields": {
        "basic_profile": { ... },
        "responsibilities": { ... },
        "pain_points": { ... },
        ...
      }
    }
  ]
}
```

写入 `04-personas.json`。

---

## Step 4:Schema 校验

由 `scripts/validate.py` 执行,**纯固化逻辑**。

校验:
- 每个字段是否符合 schema 定义
- 每条 item 是否有 `evidence_quotes`
- `mentioned_by` 里的每个人是否都在 `evidence_quotes` 里
- 没有空字段(空字段在 reduce 阶段就该处理掉)

校验不通过的字段,触发"模型修补该字段的 JSON",不全部重做。

---

## 模型调用环境

`extract_single.py` 和 `reduce_field.py` 通过环境变量读取 API 配置:

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`

在 cc switch 切到内部模型(如 MiniMax)时自动用该模型,普通 Claude Code 用 Anthropic 模型。

---

## 边界情况

- **某位受访者抽取失败**:重试 1 次,仍失败则标记「该受访者本字段抽取失败」,合并时跳过,在合并日志中提示
- **整个字段全部受访者都没数据**:合并产物为空,渲染时该字段空白(允许);**不允许模型自己编内容补**
- **受访者数量为 1**:跳过 reduce 阶段,直接把 map 产物按格式包装成 reduce 格式输出
