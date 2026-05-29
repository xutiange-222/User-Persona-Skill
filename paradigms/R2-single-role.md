# 范式 R2:单角色合并(方式 A)

**用户场景**:这批访谈都是同一种角色(比如都是产品经理 / 都是宝妈),目标是合并出 1 份画像。

**适用**:toB / toD / toC 都可以。

---

## 前置条件

- `00-research-goal.json` 已确认
- `01-paradigm.json` 已确认范式 = R2

---

## 流程概览

R2 是最简单的范式,只有 4 步:

```
Step 1: 字段对齐        → 引用 steps/field-alignment.md
Step 2: 单文档抽取(map) → 引用 steps/extract-merge.md
Step 3: 多份合并(reduce) → 引用 steps/extract-merge.md
Step 4: 渲染            → 引用 steps/render-persona-page.md
```

不涉及聚类、分类依据、价值变量、矩阵图。

---

## Step 1:字段对齐

读 `00-research-goal.json` 拿到 audience / research_question / decision_use。

读 `01-paradigm.json` 确认 `research_type`(toB/toD 或 toC),决定用哪个 schema:
- `research_type == "toB"` 或 `"toD"` → 用 `schemas/schema-tob.md`
- `research_type == "toC"` → 用 `schemas/schema-toc.md`

执行 `steps/field-alignment.md` 完整流程,产物写入 `03-field-alignment.json`。

**R2 专属约束**:R2 只有一个画像,所以 `fields_per_persona` 里只有一个 key(可以叫"默认"或用户给的画像名)。

---

## Step 2:单文档抽取(map 阶段)

调用 `scripts/extract_single.py`,对 `processed/` 下每位受访者执行一次抽取。

产物写入 `extracted/{受访者名}.json`。

模型在该阶段:
- 读 `assets/prompts/extract-tob.md` 或 `extract-toc.md`(基础 prompt)
- 拼上字段定义(从对应 schema)
- 拼上该受访者的访谈文本
- 调用模型抽取

详细规则见 `steps/extract-merge.md`。

---

## Step 3:多份合并(reduce 阶段)

调用 `scripts/reduce_field.py`,对每个字段执行一次 reduce。

R2 只有一个画像,因此每个字段只 reduce 一次(合并所有受访者在该字段上的抽取结果)。

产物按字段拼装,最终写入 `04-personas.json`,结构:

```json
{
  "version": "v8",
  "research_goal": { ... },
  "paradigm": "R2",
  "personas": [
    {
      "name": "电力调度员",   // 用户在 Step 1 给的画像名,或"默认"
      "members": ["邓老师", "孔老师", "肖老师", "刘老师", "碳中和老师"],
      "fields": {
        "basic_profile": { ... },
        "responsibilities": { ... },
        ...
      }
    }
  ]
}
```

---

## Step 3.5:用户素材确认(渲染前必做)

见 `steps/visual-assets.md`。单画像 R2 仍须问**头像**与**典型场景截图**(若有 `business_systems`/`scenarios` 字段)。

---

## Step 4:渲染

调用 `scripts/components/render_report.py`,读取 `过程稿/05-report.json`。

R2 是单画像,因此**没有 tab 切换**,直接渲染整页。

渲染规则见 `steps/render-persona-page.md`。

## 渲染:按 research_type 选族

单 tab,无矩阵总览。按 `research_type` 分支(见 `SKILL.md` §布局自动判断 主路由表 · 方式 A):

| research_type | 画像页 | 旅程(用户确认时) |
|---------------|--------|------------------|
| toB / toD | `layout-2b-grid`(溢出→双页) | `layout-2b-journey` `.is-l2` + `tob_journey_l2` |
| toC | `layout-2c-portrait`(溢出→`layout-2c-detail`) | `layout-2c-journey` + `journey_2c` |

---

## 用户对话样例(R2 全流程)

```
模型(Step 1 入口后):
你的研究是 toB,方式 A(单角色合并)。我先和你对齐画像里要展示的字段。

[展示完整字段池,标记推荐的 ★]

用户:
按推荐来。

模型:
好的。我现在开始抽取每位受访者的画像数据,大概 1-2 分钟。
[运行 extract_single.py]
[运行 reduce_field.py]
[运行 merge.py 和 validate.py]

模型:
抽取合并完成。我现在渲染 HTML 报告。
[运行 render_report.py]

模型:
报告已生成:work/report.html
你可以打开看一下,有需要调整的告诉我。
```

---

## 边界情况

- **画像名字用户没给**:模型基于受访者共性推荐一个名字(如"电力调度员""都市精致妈妈"),用户确认
- **某位受访者抽取失败**:跳过该位,在合并日志中标注"X 位受访者抽取失败,本画像基于 Y 位受访者";Y 仍 ≥ 2 时继续,Y = 1 时提示用户"剩余有效样本只有 1 位,画像可信度较低,是否继续?"
- **画像最终生成后用户想调整字段**:回到 Step 1 重新对齐字段,后续步骤会重跑(因为字段变了,reduce 输出也变)。删 `03-field-alignment.json` 及之后的文件,重启 skill 即可

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
