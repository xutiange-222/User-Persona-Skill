# 范式 R3:确认分类依据(方式 C)

**用户场景**:用户知道这批人是不同角色,但文件没分好。需要 skill 和用户对齐"按什么分"。

**适用**:toB / toD / toC 都可以。

---

## 前置条件

- `00-research-goal.json` 已确认
- `01-paradigm.json` 已确认范式 = R3,`research_type` 已确定

---

## 流程概览

```
Step 0: 推荐分类依据   → 模型读访谈 + 研究目标,推荐分类依据
Step 1: 确认具体分类   → 模型基于分类依据初分,用户确认
Step 2: 字段对齐       → 引用 steps/field-alignment.md
Step 3: 单文档抽取(map) → 引用 steps/extract-merge.md
Step 4: 多份合并(reduce) → 引用 steps/extract-merge.md(每个画像独立 reduce)
Step 5: 渲染           → 引用 steps/render-persona-page.md
```

---

## Step 0:推荐分类依据

模型读所有 `processed/` 下的文件(扫描而非深度抽取),识别角色多样性。

参考库:
- `research_type == "toB" or "toD"` → 读 `schemas/classify-basis-tob.md`
- `research_type == "toC"` → 读 `schemas/classify-basis-toc.md` 第一部分

**模型必须基于研究目标推荐 1 个主要分类依据 + 1-2 个备选**,不要列全部库给用户挑。

调用 `assets/prompts/recommend-classify-basis.md` 的 prompt 让模型推荐。

话术模板:

```
我看了 X 份访谈,这批受访者角色比较多样。
基于你的研究目标(给 [audience] 看,回答 [research_question]),
我建议按 [推荐的分类依据] 来分。

理由:
- 你要回答的问题涉及 [回扣研究目标]
- 这种分类下,每个画像的差异点最能服务这个目标

如果你倾向其他方式,也可以选:
- [备选 1]
- [备选 2]

或者你心里有别的分类逻辑,告诉我。
```

---

## Step 1:确认具体分类(显性化展示)

用户确认分类依据后,模型给出**具体的分类初分**:

```
按"岗位/角色"分,我从访谈内容初步识别出 3 类:

【调度员】(3 位):邓老师、孔老师、肖老师
  - 共同特征:负责电网实时调度操作
【运维工程师】(1 位):刘老师
  - 共同特征:负责设备维护和应急处理
【碳中和研究】(1 位):碳中和老师
  - 共同特征:从研究角度切入,负责政策对接

这个分类你认可吗?
- 认可,继续
- 调整某位受访者的归属
- 拆/合并某些类别
- 换一种分类依据
- 类别名不满意,先改名字
```

**显性化是 R3 的核心**:模型不能黑箱归类,必须把每位受访者的归属理由说清楚,用户拍板。

**类别命名必须显性确认**:
- “按什么分”和“每一类叫什么”必须一起确认。
- 模型必须把最终会出现在报告 tab、画像标题、目录和说明里的类别名列出来。
- 用户确认前,这些类别名只能是候选名,不能写死到下游合并和渲染。
- 用户只确认分类依据,但没有确认类别名时,必须追问:“分类依据我先按 [X] 记录。下面这些类别名会进入最终报告,你认可吗?如果不喜欢,我先改名字再继续。”
- 用户说“这个词不好”时,先给 2 到 4 个替代名,让用户选定后再继续。

确认后写入 `01-paradigm.json` 的 groups 字段(格式同 R1):

```json
{
  "paradigm": "R3",
  "research_type": "toB",
  "classify_basis": "岗位/角色",
  "classify_basis_reason": "因为研究目标涉及不同岗位对 AI 辅助的差异化需求",
  "label_confirmed": true,
  "groups": [
    {"name": "调度员", "label_reason": "用户确认该名称能准确表达这一类人的角色", "members": ["邓老师", "孔老师", "肖老师"]},
    {"name": "运维工程师", "label_reason": "用户确认该名称能准确表达这一类人的角色", "members": ["刘老师"]},
    {"name": "碳中和研究", "label_reason": "用户确认该名称能准确表达这一类人的角色", "members": ["碳中和老师"]}
  ]
}
```

---

## Step 2-5:同 R1

从 Step 2 开始,流程和 R1 完全一致:
- Step 2 字段对齐(含 `steps/visual-assets.md` 检查点 A:头像 + 典型场景截图)
- Step 3 单文档抽取
- Step 4 多份合并(每个画像独立 reduce)
- Step 5 渲染前执行 visual-assets 检查点 B;交付时检查点 C(多画像 tab)

唯一区别是 R3 的画像来自分类依据归纳,R1 的画像来自文件分组。下游流程不区分。

## 渲染:按 research_type 选族

同 R1(方式 B/C 多 tab)。见 `SKILL.md` §布局自动判断 主路由表 · 方式 C:`layout-2b-grid` / `layout-2c-portrait` 及对应旅程族。

---

## 用户对话样例

```
模型:
你的研究是 toB,方式 C(需要确认分类)。
我看了 5 份访谈,这批受访者角色比较多样。

基于你的研究目标(给产品团队看,回答 AI 辅助决策需求),
我建议按"岗位/角色"分。

理由:你的研究目标关注不同岗位对 AI 的差异化需求,按岗位分能突出这种差异。

具体分类:
- 【调度员】(3 位):邓老师、孔老师、肖老师
- 【运维工程师】(1 位):刘老师
- 【碳中和研究】(1 位):碳中和老师

这个对吗?

用户:
碳中和老师也是研究和决策类的,可以和调度员合并到一类。

模型:
[更新分类]
好的,现在分类是:
- 【调度决策类】(4 位):邓老师、孔老师、肖老师、碳中和老师
- 【运维工程师】(1 位):刘老师

继续吗?

用户:
继续。

[后续流程同 R1]
```

---

## 边界情况

- **用户给的分类依据是 schema 里没有的**:模型接受,不强行套库;在 `classify_basis` 字段直接用用户的描述
- **分类后某类只有 1 位**:照样保留,但提示样本量小;用户可以选择和相近类别合并
- **用户改 3 次以上还不满意分类**:模型主动建议"要不要换一种分类依据,我可以给出其他选项"
- **用户用复合分类依据(如"岗位 × 经验水平"产生 4-6 类)**:照样支持,写入 `classify_basis = "岗位 × 经验水平"`,groups 数量相应增加

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
