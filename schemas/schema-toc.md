# toC 画像字段定义

这份文档定义 toC 画像的 JSON schema、可选字段池、默认推荐字段集。

`extract_single.py` 和 `merge.py` 按这个 schema 产出 JSON,`validate.py` 按这个 schema 校验。

---

## 可选字段池(全集 + 中文说明,展示给用户选)

跟用户对齐字段时,把这份清单**完整列给用户**(用中文,带说明),让用户勾选要哪些。**不要只展示默认推荐**,因为默认推荐可能漏掉用户场景需要的维度。

### A. 用户身份(左栏展示)

- `basic_profile` — 基本信息(头像、姓名、性别、年龄、家庭规模、收入、职业、教育背景、国籍、城市)
- `lifestyle` — 生活风格和个性特征(日程安排、社交网络影响力、参考对象、爱好、性格特点、人生履历)
- `consumption_pattern` — 消费观和消费习惯(整体消费观、对本产品及周边商品的消费观念)

### B. 用户感受(右栏核心)

- `experience_goals` — 体验目标(在使用产品的过程中希望获得什么体验价值、需求、个性化签名)
- `motivation` — 动机(使用本类产品深层的动机、追求)
- `pain_points` — 典型痛点(对体验影响较大、发生次数较高的痛点)
- `expectations` — 期待和诉求(对产品发展趋势的洞察、对未来的期待)

### C. 用户行为(右栏)

- `usage_pattern` — 使用习惯(设备和软件、频次、深度、偏好)
- `product_attitude` — 对产品的态度评价(整体评价、典型场景的体验)
- `competitor_view` — 竞争对手对比(产品和竞品相比的优劣势、典型体验)
- `key_scenarios` — 典型场景(KEP — Key Experience Points,关键体验点)

### D. 用户原声

- `one_sentence_need` — 个性化签名 / 一句话需求(用一句话用户原声表达对产品的价值追求、需求、自我定位)
- `representative_quotes` — 代表性原声(2-4 条带来源标注,作为 hover tooltip 数据源,不单独成模块)

### E. 可选字段(只在相关时启用)

- `tech_background` — 技术和资讯(对技术、互联网资讯了解的深度和广度;了解资讯的渠道)
- `lifecycle` — 生命周期(使用产品时间、品牌印象、品牌忠诚度、本产品的角色变化)

---

## 跟用户对齐字段的话术(必须用中文展示完整清单)

```
基于你的研究目标(给 [audience] 看,回答 [research_question]),
我推荐以下字段(★ 是推荐的,你可以增减):

【用户身份】(画像左栏)
★ 基本信息:头像、姓名、性别、年龄、家庭、收入、职业等
★ 生活风格和个性
□ 消费观和消费习惯

【用户感受】(画像右栏核心)
★ 体验目标
★ 动机
★ 典型痛点
□ 期待和诉求

【用户行为】(画像右栏)
□ 使用习惯
□ 产品态度评价
□ 竞争对手对比
□ 典型场景

【用户原声】
★ 一句话需求 / 个性化签名
★ 代表性原声

【可选字段】
□ 技术和资讯(用户是否专家、对技术接受度)
□ 生命周期(用户处于产品生命周期的哪个阶段)

你要哪些?可以直接说:
- "按推荐来"
- "加上 使用习惯、产品态度"
- "去掉 动机,加上 典型场景"
```

---

## 推荐 ★ 的逻辑(基于研究目标)

| 研究目标关键词 | 必推 ★ |
|---------------|--------|
| 新功能定位 / 产品决策 | `experience_goals`, `pain_points`, `motivation`, `one_sentence_need` |
| 营销策略 / 投放 | `basic_profile`, `lifestyle`, `consumption_pattern`, `motivation` |
| 用户分群 / 细分市场 | `lifestyle`, `consumption_pattern`, `usage_pattern`, `motivation` |
| 产品改进 / 体验优化 | `pain_points`, `experience_goals`, `usage_pattern`, `product_attitude` |
| 竞品对标 | `product_attitude`, `competitor_view`, `expectations` |
| 用户教育 / 心智建设 | `tech_background`, `motivation`, `expectations`, `lifecycle` |
| 探索性研究 | 全推 ★ |

模型在话术中**必须显式回扣研究目标**:

```
我推荐这些 ★ 的理由:
你说要"决定新功能要不要做",所以我推荐:
- 体验目标(新功能要满足什么体验)
- 典型痛点(新功能的切入点)
- 动机(新功能要呼应的深层需求)
- 一句话需求(对决策最有说服力的引用)
```

---

## 字段填写规范

### A. basic_profile

```json
{
  "field_name": "basic_profile",
  "value": {
    "name": "李芳",
    "avatar_keyword": "30 岁都市女性,白领",
    "gender": "女",
    "age": "30",
    "family": "已婚有一子,3 岁",
    "income": "家庭月收入 3-5 万",
    "occupation": "互联网公司产品经理",
    "education": "本科,北京某 211",
    "location": "北京市朝阳区"
  },
  "evidence_quotes": [ ... ]
}
```

注意:toC 画像的 basic_profile 通常是**虚构的抽象人**,字段值是研究员/模型基于该类受访者的平均水平给的代表性数值,**不是某个真实受访者的数据**。

### B. lifestyle / consumption_pattern

list 结构,每条带 evidence:

```json
{
  "field_name": "lifestyle",
  "items": [
    {
      "content": "工作日早 7 点起床,晚 11 点睡;周末安排亲子活动",
      "mentioned_by": ["用户 A", "用户 B", "用户 C"],
      "evidence_quotes": [...]
    }
  ]
}
```

### C. pain_points / experience_goals / motivation / expectations

标准 list + evidence 结构,见 `steps/extract-merge.md`。

### D. one_sentence_need

单值字段:

```json
{
  "field_name": "one_sentence_need",
  "value": "我希望产品能像朋友一样懂我,不用我每次解释",
  "evidence_quote": "...",
  "source": "李芳" 或 "综合归纳"
}
```

toC 场景下 `source` 可以是 "综合归纳"(典型代表,不是某个具体人的原话)。

### E. representative_quotes

```json
{
  "field_name": "representative_quotes",
  "items": [
    {"quote": "...", "source": "用户 A"},
    {"quote": "...", "source": "用户 B"}
  ]
}
```

2-4 条,放在 hover tooltip 不占主版面。

---

## 自定义字段约定

用户自定义字段必须有:
- `display_name`(中文显示名)
- `definition`(收集什么内容)
- `data_shape`:`list` / `paragraph` / `single_value`

例:

```json
{
  "key": "social_circle",
  "display_name": "社交圈层",
  "definition": "用户主要在哪些圈层里活动 (闺蜜圈 / 同事圈 / 兴趣圈)",
  "data_shape": "list"
}
```

---

## P8 组件化的 toC 决策点(2026-05-25 起)

### identity_card 的 meta_tags 是开放字段

toC 主页左栏身份卡的 `meta_tags` **完全自由**,LLM 自决:
- 数量:2-5 个(schema 强约束)
- label:自由文本 2-6 字(可以是「职业/年龄」「画像指纹」「设备」「使用风格」任何能识别画像特征的字段名)
- value:自由文本 2-20 字(可单值,也可用 `·` 拼接多值)

例:
```json
{ "label": "职业 / 年龄", "value": "医生 · 50+" },
{ "label": "画像指纹",  "value": "内行 · 内容 · 场景 · 高端" }
```

LLM 根据**研究目标 + 画像特征**决定挑哪些 label,目标是让读者一眼能识别该画像的关键特征。

### section_block 的 title 是开放字段 + body 有最低深度

`section_block.title` 是 LLM 自决文案(3-6 字),要**贴合该画像的语义**(如音乐画像里写「对音质的追求」而不是「行为习惯」)。

但 schema 强约束**内容深度**(防敷衍):
- `title.minLength: 3, maxLength: 6`
- `summary.minLength: 8, maxLength: 25`
- **`body.minLength: 30, maxLength: 100`**(关键:防止「做放松」这种 3 字水帖)
- **`evidence_quotes.minItems: 2`**(每段至少 2 条证据,UXR 可信度)

body 内容必须含**具体动作 / 具体场景 / 具体程度词**,而不是抽象描述。

### section_blocks_grid 数量必须是 2 / 4 / 6

`blocks` 数量被 `oneOf` 限制为 **2、4 或 6**(对应拼贴布局)。3 个或 5 个会被事前校验拦截。

### emoji 必须从 33 个枚举名选(不输出 Unicode 字符)

`journey_2c.emotion[i].emoji` 必须是 33 个语义名之一:
`smile` / `smile_blush` / `grin` / `laughing` / `content` / `relaxed` / `proud` / `star_struck` / `thinking` / `confused` / `raised_eyebrow` / `neutral` / `hmm` / `frowning` / `disappointed` / `frustrated` / `persevere` / `tired` / `sad` / `crying` / `surprised` / `shocked` / `exclamation` / `excited` / `celebrate` / `fire` / `heart_eyes` / `headphone` / `light_bulb` / `target` / `thumbs_up` / `thumbs_down` / `question`

详细分类 + 选择指南见 `scripts/components/REGISTRY.md` §6.3。**禁止直接写 `🙂` `😕` 等 Unicode 字符**(SKILL.md 约束 13)。

### 字段名 → P8 组件 type 映射

| 数据字段(04-personas.json) | 渲染组件 type(05-report.json) |
|---|---|
| 画像名 + 副标 + meta tags | `identity_card` |
| 代表原话 | `persona_quote_pull`(右上跨 2 列大引号) |
| 各类「核心需求 / 动机 / 行为」分段 | `section_blocks_grid.blocks[]`(2/4/6 个 `section_block`) |
| 用户旅程(阶段 × 维度 + 情绪曲线) | `journey_2c`(整张图作为一个容器组件) |
| 矩阵象限子画像 | `identity_card` + `section_blocks_grid`(放进 `layout-2c-portrait`,id 用 `persona-qN`) |
| 单画像专题详情 | `detail_headline` + `mockup_list` + `detail_analysis`(可选 `detail_illust_corner` 角落小图) |

**完整 24 个组件 type 清单**:见 `scripts/components/REGISTRY.md` §9.2（以 `schemas/report.json` enum 为准）。

**用户图片素材(字段对齐必问)**:toC 头像走 `identity_card.illust_path` / 旅程头图;专题详情产品图走 `mockup_list.mockups[].screenshot`。目录与询问流程见 `steps/visual-assets.md`(与 toB 同一套三处检查点)。
