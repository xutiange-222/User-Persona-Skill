# Prompt:受访者档位映射(R4/R5 范式)

## 用途

R4/R5 范式下,模型读每位受访者的访谈,在每个价值变量上判断属于哪个档位 + 给出原话证据。

调用方:`paradigms/R4-2d-matrix.md` 和 `paradigms/R5-multi-variable.md` 的 Step 2。

---

## 输入变量

- `{{respondent_name}}`:受访者名字
- `{{interview_text}}`:该受访者的访谈逐字稿
- `{{value_variables}}`:价值变量定义 + 档位定义(从 02-classification.json 读)
- `{{research_goal}}`:研究目标(用于回扣)

---

## Prompt 模板

```
你是一位资深的用户研究员。基于这位受访者的访谈,在每个价值变量上给出档位判断,并提供原话证据。

## 受访者
{{respondent_name}}

## 访谈文本
{{interview_text}}

## 价值变量定义
{{value_variables}}

## 任务

对每个价值变量,做以下两件事:

1. 判断这位受访者在该变量上落哪个档位
2. 提供 1-3 条原话证据(verbatim,不要改写)

**规则**:

- 如果某个变量在访谈中没有相关数据,标 `"level": null`,`"evidence_quotes": []`,并在 `"note"` 中说明"该受访者访谈中未涉及"
- 档位判断要基于明确的行为表现/态度表达,不要凭印象
- 原话必须是访谈中的真实片段,不能编造

**输出格式**(JSON):

{
  "respondent": "{{respondent_name}}",
  "mapping": {
    "price_sensitivity": {
      "level": "高",
      "evidence_quotes": [
        "我会去三个平台比价,差几块钱也要选便宜的",
        "我加购物车里要放一周,等折扣才下手"
      ],
      "note": ""
    },
    "brand_preference": {
      "level": "低",
      "evidence_quotes": [
        "我看东西本身,不太关心牌子"
      ],
      "note": ""
    }
  }
}

只输出 JSON,不要其他文字。
```
