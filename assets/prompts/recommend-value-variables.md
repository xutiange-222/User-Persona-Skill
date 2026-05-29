# Prompt:推荐区分点(R4/R5 范式)

## 用途

R4/R5 范式下,模型基于访谈数据 + 研究目标,推荐 2 个(R4)或 3-5 个(R5)区分点。内部 JSON 仍沿用 value_variables 命名,但面向用户时统一说"区分点"。

调用方:`paradigms/R4-2d-matrix.md` 或 `paradigms/R5-multi-variable.md` 的 Step 0。

---

## 输入变量

- `{{research_goal}}`:研究目标 JSON
- `{{research_type}}`:通常是 toC
- `{{paradigm}}`:R4 或 R5
- `{{interview_summaries}}`:每位受访者的简短摘要
- `{{value_variables_library}}`:区分点推荐库(schemas/classify-basis-toc.md 第二部分)

---

## Prompt 模板

```
你是一位资深的用户研究方法论专家。基于以下信息,推荐 toC 画像构建的区分点。

## 研究目标
{{research_goal}}

## 研究类型
{{research_type}}

## 选择的范式
{{paradigm}}
- R4 = 推荐 2 个区分点,作为 2 维坐标图的横纵轴
- R5 = 推荐 3-5 个区分点,作为多维分布图的各行

## 受访者摘要
{{interview_summaries}}

## 区分点候选库(按场景分类)
{{value_variables_library}}

## 任务

推荐合适的区分点。**必须**用三个筛选标准:

1. **覆盖性**:所有受访者在这个维度上都有行为表现
2. **差异性**:同一维度上,受访者表现有明显差异
3. **决策相关性**:这个维度对研究目标的决策有核心影响

不满足这三个标准的变量不能推荐。

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

## 用户话术约束

- 跟用户解释时说"区分点",不要说"价值变量"。
- 必须解释一次:"区分点就是用来把用户分成几类的判断标准"。
- R5 要解释为"多维分布图",并补一句白话:"你可以把它理解成一张用户类型对照表:每一行是一个区分点,每一列是一类用户,用来横向看几类用户到底差在哪。"
- R4 坐标轴两端后续划档时不能只叫"高 / 低",要用准确的两极命名,例如"反复比价 / 认可即买"、"自主探索 / 依赖推荐"。

**输出格式**(JSON):

R4 输出:

{
  "recommendations": [
    {
      "key": "price_sensitivity",
      "name": "价格敏感度",
      "definition": "用户对价格的关注程度",
      "axis": "x",
      "coverage_evidence": "5 位受访者都有提到价格相关话题",
      "difference_evidence": "2 位高敏感,2 位中等,1 位低敏感",
      "decision_relevance": "对价格策略和首屏文案设计有核心影响,呼应研究目标'回答新用户最先被什么打动'"
    },
    {
      "key": "brand_preference",
      "name": "品牌偏好",
      "definition": "...",
      "axis": "y",
      "coverage_evidence": "...",
      "difference_evidence": "...",
      "decision_relevance": "..."
    }
  ],
  "alternatives": []
}

R5 输出:

{
  "recommendations": [
    {"key": "...", "name": "...", "definition": "...", "coverage_evidence": "...", "difference_evidence": "...", "decision_relevance": "..."},
    ... (3-5 个)
  ]
}

只输出 JSON,不要其他文字。
```
