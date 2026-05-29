# Prompt:推荐分类依据(R3 范式)

## 用途

R3 范式下,模型基于访谈数据 + 研究目标,推荐 1 个主要分类依据 + 1-2 个备选。

调用方:`paradigms/R3-classify-basis.md` 的 Step 0。

---

## 输入变量

- `{{research_goal}}`:研究目标 JSON(audience / research_question / decision_use)
- `{{research_type}}`:toB / toD / toC
- `{{interview_summaries}}`:每位受访者的简短摘要(从 processed/ 自动生成,每人 100 字以内)
- `{{classify_basis_library}}`:对应的分类依据库内容(schemas/classify-basis-tob.md 或 -toc.md)

---

## Prompt 模板

```
你是一位资深的用户研究方法论专家。基于以下信息,推荐画像分类依据。

## 研究目标
{{research_goal}}

## 研究类型
{{research_type}}

## 受访者摘要
{{interview_summaries}}

## 可选分类依据库
{{classify_basis_library}}

## 任务

基于研究目标和实际访谈摘要,从可选分类依据库中(或库外)推荐 1 个主要分类依据 + 1-2 个备选。

**必须做到**:
1. **基于研究目标推荐**,不能凭直觉。在理由中显式回扣研究目标的某个具体方面。
2. **基于访谈数据可分性判断**,如果某个分类依据在数据上分不出明显差异,不推荐。
3. **不要列全部库给用户挑**,只给 1 主 + 1-2 备。

**输出格式**(JSON):

{
  "primary_recommendation": {
    "basis_name": "岗位/角色",
    "reason": "因为研究目标涉及不同岗位对 AI 辅助的差异化需求,按岗位分能突出这种差异",
    "predicted_groups": [
      {"name": "调度员", "members": ["邓老师", "孔老师", "肖老师"], "reason_short": "都负责实时调度"},
      {"name": "运维", "members": ["刘老师"], "reason_short": "负责设备维护"},
      {"name": "碳中和", "members": ["碳中和老师"], "reason_short": "从政策研究角度切入"}
    ]
  },
  "alternatives": [
    {
      "basis_name": "技能水平",
      "reason": "如果研究目标更侧重新功能上手难度,可以考虑这个分类"
    }
  ]
}

只输出 JSON,不要其他文字。
```
